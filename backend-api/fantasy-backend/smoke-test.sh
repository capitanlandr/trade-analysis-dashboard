#!/bin/bash
BASE_URL="${1:-https://aucuc2yvd4.execute-api.us-east-1.amazonaws.com/Prod}"
ENDPOINTS=("trades" "teams" "stats" "standings" "playoffs" "draft-order" "waivers")
PASS=0
FAIL=0

echo "Smoke testing API endpoints at: $BASE_URL"
echo "=========================================="

for endpoint in "${ENDPOINTS[@]}"; do
  echo -n "Testing /api/$endpoint... "
  RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/$endpoint")
  STATUS=$(echo "$RESPONSE" | tail -1)
  BODY=$(echo "$RESPONSE" | sed '$d')

  if [ "$STATUS" = "200" ]; then
    # Validate it's valid JSON
    echo "$BODY" | python3 -m json.tool > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo "OK (${STATUS}, valid JSON)"
      PASS=$((PASS + 1))
    else
      echo "FAIL (${STATUS}, invalid JSON)"
      FAIL=$((FAIL + 1))
    fi
  else
    echo "FAIL (${STATUS})"
    FAIL=$((FAIL + 1))
  fi
done

echo ""
echo "=========================================="
echo "Results: $PASS passed, $FAIL failed out of ${#ENDPOINTS[@]} endpoints"

if [ $FAIL -gt 0 ]; then
  exit 1
fi
