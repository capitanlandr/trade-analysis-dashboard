#!/bin/bash
# Script to rename waiver wire files and update all references
# Part of refactor/rename-waiver-files branch

set -e  # Exit on error

echo "=========================================="
echo "Waiver Wire File Renaming Script"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Show what will be changed
echo -e "${YELLOW}Step 1: Scanning for references...${NC}"
echo ""

echo "Files referencing 'waiver-wire.json':"
grep -r "waiver-wire\.json" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" --include="*.yaml" --include="*.yml" \
    --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=.pytest_cache --exclude-dir=backups --exclude-dir=logs \
    . 2>/dev/null | cut -d: -f1 | sort -u | head -20 || echo "  (none found)"

echo ""
echo "Files referencing 'api-waiver-wire.json':"
grep -r "api-waiver-wire\.json" --include="*.py" --include="*.ts" --include="*.tsx" --include="*.md" --include="*.yaml" --include="*.yml" \
    --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=dist --exclude-dir=.pytest_cache --exclude-dir=backups --exclude-dir=logs \
    . 2>/dev/null | cut -d: -f1 | sort -u | head -20 || echo "  (none found)"

echo ""
echo -e "${YELLOW}Press Enter to continue with replacements, or Ctrl+C to cancel...${NC}"
read

# Step 2: Perform replacements in Python files
echo ""
echo -e "${GREEN}Step 2: Performing find-and-replace...${NC}"
echo ""

# Replacement 1: waiver-wire.json -> cumulative_processed_waiver_transactions.json
echo "Updating Python files..."
find . -type f -name "*.py" \
    -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" \
    -not -path "*/.pytest_cache/*" -not -path "*/backups/*" -not -path "*/logs/*" \
    -exec sed -i '' 's/waiver-wire\.json/cumulative_processed_waiver_transactions.json/g' {} +

echo "Updating TypeScript files..."
find . -type f \( -name "*.ts" -o -name "*.tsx" \) \
    -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" \
    -exec sed -i '' 's/api-waiver-wire\.json/waiver-wire-page.json/g' {} +

echo "Updating YAML files..."
find . -type f \( -name "*.yaml" -o -name "*.yml" \) \
    -not -path "*/node_modules/*" -not -path "*/.git/*" \
    -exec sed -i '' 's/waiver-wire\.json/cumulative_processed_waiver_transactions.json/g' {} +

echo "Updating Markdown documentation..."
find . -type f -name "*.md" \
    -not -path "*/node_modules/*" -not -path "*/.git/*" \
    -exec sed -i '' 's/api-waiver-wire\.json/waiver-wire-page.json/g' {} + \
    -exec sed -i '' 's/waiver-wire\.json/cumulative_processed_waiver_transactions.json/g' {} +

echo ""
echo -e "${GREEN}✓ Find-and-replace complete${NC}"

# Step 3: Rename actual files
echo ""
echo -e "${GREEN}Step 3: Renaming actual files...${NC}"
echo ""

# Rename pipeline file if it exists
if [ -f "pipeline/waiver-wire.json" ]; then
    echo "Renaming pipeline/waiver-wire.json..."
    mv pipeline/waiver-wire.json pipeline/cumulative_processed_waiver_transactions.json
    echo -e "${GREEN}✓ Renamed to cumulative_processed_waiver_transactions.json${NC}"
else
    echo -e "${YELLOW}⚠ pipeline/waiver-wire.json not found (may already be renamed)${NC}"
fi

# Delete unused frontend copy
if [ -f "dashboard/frontend/public/waiver-wire.json" ]; then
    echo "Deleting dashboard/frontend/public/waiver-wire.json (unused duplicate)..."
    rm dashboard/frontend/public/waiver-wire.json
    echo -e "${GREEN}✓ Deleted unused file${NC}"
else
    echo -e "${YELLOW}⚠ dashboard/frontend/public/waiver-wire.json not found (may already be deleted)${NC}"
fi

# Rename dashboard API file if it exists
if [ -f "dashboard/frontend/public/api-waiver-wire.json" ]; then
    echo "Renaming dashboard/frontend/public/api-waiver-wire.json..."
    mv dashboard/frontend/public/api-waiver-wire.json dashboard/frontend/public/waiver-wire-page.json
    echo -e "${GREEN}✓ Renamed to waiver-wire-page.json${NC}"
else
    echo -e "${YELLOW}⚠ dashboard/frontend/public/api-waiver-wire.json not found (may already be renamed)${NC}"
fi

# Step 4: Show git status
echo ""
echo -e "${GREEN}Step 4: Git status${NC}"
echo ""
git status --short

# Step 5: Summary
echo ""
echo "=========================================="
echo -e "${GREEN}✅ RENAMING COMPLETE${NC}"
echo "=========================================="
echo ""
echo "Summary of changes:"
echo "  1. waiver-wire.json → cumulative_processed_waiver_transactions.json"
echo "  2. api-waiver-wire.json → waiver-wire-page.json"
echo "  3. Deleted: dashboard/frontend/public/waiver-wire.json (unused)"
echo ""
echo "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Test locally: ./dev.sh"
echo "  3. Commit: git add . && git commit -m 'refactor: rename waiver wire files for clarity'"
echo ""
