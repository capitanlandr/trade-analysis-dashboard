#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/dashboard/frontend"
DIST_DIR="$FRONTEND_DIR/dist"

AWS_PROFILE_NAME="${AWS_PROFILE:-}"
AWS_REGION_NAME="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"

if [[ -z "${AWS_S3_BUCKET:-}" ]]; then
  echo "ERROR: AWS_S3_BUCKET is not set"
  exit 1
fi

if [[ -z "${AWS_CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
  echo "ERROR: AWS_CLOUDFRONT_DISTRIBUTION_ID is not set"
  exit 1
fi

PROFILE_ARGS=()
if [[ -n "$AWS_PROFILE_NAME" ]]; then
  PROFILE_ARGS=(--profile "$AWS_PROFILE_NAME")
fi

pushd "$FRONTEND_DIR" > /dev/null

if [[ ! -d node_modules ]]; then
  npm install
fi

npm run build

if [[ ! -d "$DIST_DIR" ]]; then
  echo "ERROR: build output not found at $DIST_DIR"
  exit 1
fi

echo "Syncing assets to s3://$AWS_S3_BUCKET (long cache)"
aws "${PROFILE_ARGS[@]}" --region "$AWS_REGION_NAME" s3 sync dist/ "s3://$AWS_S3_BUCKET/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "*.html" \
  --exclude "*.json"

echo "Syncing HTML/JSON to s3://$AWS_S3_BUCKET (short cache)"
aws "${PROFILE_ARGS[@]}" --region "$AWS_REGION_NAME" s3 sync dist/ "s3://$AWS_S3_BUCKET/" \
  --exclude "*" \
  --include "*.html" \
  --include "*.json" \
  --cache-control "public, max-age=3600, must-revalidate"

echo "Invalidating CloudFront distribution $AWS_CLOUDFRONT_DISTRIBUTION_ID"
aws "${PROFILE_ARGS[@]}" cloudfront create-invalidation \
  --distribution-id "$AWS_CLOUDFRONT_DISTRIBUTION_ID" \
  --paths "/*"

if aws "${PROFILE_ARGS[@]}" cloudfront get-distribution \
  --id "$AWS_CLOUDFRONT_DISTRIBUTION_ID" \
  --query 'Distribution.DomainName' \
  --output text > /tmp/cloudfront_domain.txt 2>/dev/null; then
  echo "Deployed to https://$(cat /tmp/cloudfront_domain.txt)"
fi

popd > /dev/null
