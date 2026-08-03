#!/usr/bin/env python3
"""
Local Lambda + API Gateway emulator for dashboard_api
=====================================================

Serves `dashboard_api/app.py`'s `lambda_handler` over real HTTP on localhost so
the Vite dev server can point at it and the browser exercises the same code path
that runs in production.

WHY NOT `sam local start-api`
-----------------------------
`sam local` requires Docker to run the Lambda container, and Docker is not
installed on this machine (no colima/podman/lima either). It is also not needed
here: `lambda_handler(event, context)` is a plain function that reads
`event['path']`, `event['httpMethod']`, and `event['queryStringParameters']`, and
returns `{statusCode, headers, body}`. This script builds that event dict, calls
the handler in-process, and translates the return value back to an HTTP response.

What this DOES faithfully reproduce:
  - the handler's own routing, DynamoDB access, JSON shaping, and error handling
  - API Gateway's proxy event and response contract
  - CORS headers, since the handler sets them itself

What it does NOT reproduce (use a real deploy to check these):
  - IAM authorization, throttling, request/response mapping templates
  - cold starts, the 15-minute timeout, memory limits
  - API Gateway stage paths and custom domains

USAGE
-----
    # 1. DynamoDB Local (no Docker; needs a JDK)
    java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -inMemory -port 8000

    # 2. Publish pipeline output into it
    cd pipeline && python3 stage13_publish_dynamodb.py --endpoint-url http://localhost:8000

    # 3. Serve the Lambda
    python3 backend-api/fantasy-backend/local_api.py --port 3001

    # 4. Point the frontend at it
    cd dashboard/frontend && VITE_USE_LAMBDA_API=true \
        VITE_API_BASE_URL=http://localhost:3001 npm run dev

Unset AWS_PROFILE / AWS_REGION when running locally -- DynamoDB Local partitions
data by credential and region, so a stray profile makes the table look empty.
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))


def load_handler(endpoint_url: str, table_name: str):
    """Import dashboard_api.app with boto3 redirected at DynamoDB Local.

    app.py builds its `table` at import time from a default-configured
    boto3.resource, so the redirect has to be installed BEFORE the import. This
    patches boto3.resource rather than editing app.py: the deployed handler must
    stay byte-identical to what is tested here, otherwise the emulator is
    validating code that never ships.
    """
    import boto3

    real_resource = boto3.resource

    def patched_resource(service_name, *args, **kwargs):
        if service_name == "dynamodb":
            kwargs.setdefault("endpoint_url", endpoint_url)
            kwargs.setdefault("region_name", "us-east-1")
            kwargs.setdefault("aws_access_key_id", "local")
            kwargs.setdefault("aws_secret_access_key", "local")
        return real_resource(service_name, *args, **kwargs)

    boto3.resource = patched_resource
    os.environ["TABLE_NAME"] = table_name

    sys.path.insert(0, os.path.join(HERE, "dashboard_api"))
    import app  # noqa: E402  -- import must follow the patch above

    return app.lambda_handler


class LambdaProxyHandler(BaseHTTPRequestHandler):
    """Translates HTTP <-> the API Gateway proxy event/response contract."""

    lambda_handler = None  # injected in main()

    def do_GET(self):
        self._invoke("GET")

    def do_OPTIONS(self):
        # CORS preflight. The handler sets the headers, so route it through too.
        self._invoke("OPTIONS")

    def _invoke(self, method: str):
        parsed = urlparse(self.path)
        # API Gateway gives single values, not lists, in queryStringParameters.
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()} or None

        event = {
            "path": parsed.path,
            "httpMethod": method,
            "queryStringParameters": qs,
            "headers": dict(self.headers),
            "body": None,
            "isBase64Encoded": False,
        }

        try:
            result = self.lambda_handler(event, LambdaContext())
        except Exception as exc:  # emulate API Gateway's 502 on handler crash
            body = json.dumps({"error": "Handler raised", "message": str(exc)})
            self._respond(502, {"Content-Type": "application/json"}, body)
            print(f"  {method} {self.path} -> 502 (handler raised: {exc})")
            return

        status = result.get("statusCode", 200)
        headers = result.get("headers") or {}
        body = result.get("body") or ""
        self._respond(status, headers, body)

        season = (qs or {}).get("season", "(default: all)")
        print(f"  {method} {parsed.path} season={season} -> {status} ({len(body)} bytes)")

    def _respond(self, status: int, headers: dict, body: str):
        encoded = body.encode("utf-8")
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, str(value))
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, fmt, *args):
        pass  # suppress the default per-request stderr noise; _invoke logs instead


class LambdaContext:
    """Minimal stand-in for the Lambda context object."""
    function_name = "dashboard-api-local"
    memory_limit_in_mb = 512
    aws_request_id = "local-invoke"
    log_group_name = "/aws/lambda/dashboard-api-local"

    def get_remaining_time_in_millis(self):
        return 30000


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=3001)
    ap.add_argument("--endpoint-url", default="http://localhost:8000",
                    help="DynamoDB Local endpoint")
    ap.add_argument("--table-name", default="fantasy-dashboard-data")
    ap.add_argument("--invoke", metavar="PATH",
                    help="invoke one path and print the response instead of serving "
                         "(e.g. --invoke '/api/trades?season=season_2')")
    args = ap.parse_args()

    handler = load_handler(args.endpoint_url, args.table_name)

    if args.invoke:
        parsed = urlparse(args.invoke)
        qs = {k: v[0] for k, v in parse_qs(parsed.query).items()} or None
        result = handler({
            "path": parsed.path,
            "httpMethod": "GET",
            "queryStringParameters": qs,
        }, LambdaContext())
        print(f"statusCode: {result.get('statusCode')}")
        body = result.get("body") or ""
        print(f"body bytes: {len(body)}")
        try:
            print(json.dumps(json.loads(body), indent=2)[:1200])
        except json.JSONDecodeError:
            print(body[:1200])
        return 0 if result.get("statusCode") == 200 else 1

    LambdaProxyHandler.lambda_handler = staticmethod(handler)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), LambdaProxyHandler)

    print("=" * 78)
    print("Local Lambda + API Gateway emulator: dashboard_api")
    print("=" * 78)
    print(f"  listening : http://localhost:{args.port}")
    print(f"  dynamodb  : {args.endpoint_url} (table {args.table_name})")
    print(f"  frontend  : VITE_USE_LAMBDA_API=true "
          f"VITE_API_BASE_URL=http://localhost:{args.port} npm run dev")
    print("  Ctrl-C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
