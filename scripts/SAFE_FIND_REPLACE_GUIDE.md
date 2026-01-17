# Safe Find-and-Replace Guide for File Renames

## The Problem We Solved
When renaming files across a codebase, you need to find and replace ALL references while avoiding:
- Missing files in excluded directories
- Substring matching errors (e.g., `api-old.json` matching `old.json` pattern)
- Binary file corruption
- Incomplete replacements

## The Bulletproof Process

### Step 1: Comprehensive Scan
Find EVERY file that contains your target string:

```bash
#!/bin/bash
TARGET_STRING="old-filename.json"

# Method 1: Using grep (faster, shows line numbers)
grep -r \
    --include="*.py" \
    --include="*.ts" \
    --include="*.tsx" \
    --include="*.js" \
    --include="*.jsx" \
    --include="*.md" \
    --include="*.yaml" \
    --include="*.yml" \
    --include="*.json" \
    --include="*.sh" \
    --exclude-dir=node_modules \
    --exclude-dir=.git \
    --exclude-dir=dist \
    --exclude-dir=build \
    --exclude-dir=.pytest_cache \
    --exclude-dir=__pycache__ \
    --exclude-dir=logs \
    --exclude-dir=backups \
    -n "$TARGET_STRING" . > scan_results.txt

# Method 2: Using ripgrep (fastest, if available)
rg "$TARGET_STRING" \
    --type py \
    --type ts \
    --type md \
    --type yaml \
    --type json \
    --glob '!node_modules' \
    --glob '!.git' \
    --glob '!dist' \
    --glob '!logs' \
    --glob '!backups' \
    -n > scan_results_rg.txt

# Review the results
cat scan_results.txt | wc -l
echo "Total files with references:"
cat scan_results.txt | cut -d: -f1 | sort -u | wc -l
```

### Step 2: Understand Context
Review each reference to understand:
- Is this a file path reference?
- Is this in documentation?
- Is this in a configuration file?
- Could this string appear as a substring in other contexts?

```bash
# Group by file type
echo "=== Python Files ==="
grep "\.py:" scan_results.txt

echo "=== TypeScript Files ==="
grep "\.tsx\?:" scan_results.txt

echo "=== Documentation ==="
grep "\.md:" scan_results.txt
```

### Step 3: Order Your Replacements
**CRITICAL RULE:** Replace more specific patterns BEFORE less specific ones.

❌ **WRONG ORDER** (causes bugs):
```bash
# This will incorrectly match "api-old.json" when replacing "old.json"
sed -i 's/old\.json/new.json/g' file.py
sed -i 's/api-old\.json/api-new.json/g' file.py
```

✅ **CORRECT ORDER**:
```bash
# Replace more specific pattern first
sed -i 's/api-old\.json/api-new.json/g' file.py
# Then replace less specific pattern
sed -i 's/old\.json/new.json/g' file.py
```

### Step 4: Safe Replacement Script

```bash
#!/bin/bash
set -e  # Exit on error

echo "Step 1: Create backup branch"
git checkout -b refactor/rename-files
git add -A
git commit -m "backup: before file rename" || true

echo "Step 2: Perform replacements (most specific first)"

# Define your replacements in order from MOST to LEAST specific
declare -a REPLACEMENTS=(
    "api-old-file\.json:api-new-file.json"
    "old-file\.json:new-file.json"
)

# Apply each replacement to appropriate file types
for replacement in "${REPLACEMENTS[@]}"; do
    OLD_PATTERN="${replacement%%:*}"
    NEW_NAME="${replacement##*:}"
    
    echo "Replacing: $OLD_PATTERN -> $NEW_NAME"
    
    # Python files
    find . -type f -name "*.py" \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -not -path "*/dist/*" \
        -not -path "*/.pytest_cache/*" \
        -not -path "*/backups/*" \
        -not -path "*/logs/*" \
        -exec sed -i '' "s/$OLD_PATTERN/$NEW_NAME/g" {} +
    
    # TypeScript files
    find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -not -path "*/dist/*" \
        -exec sed -i '' "s/$OLD_PATTERN/$NEW_NAME/g" {} +
    
    # Config files
    find . -type f \( -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -not -path "*/dist/*" \
        -not -path "*/logs/*" \
        -exec sed -i '' "s/$OLD_PATTERN/$NEW_NAME/g" {} +
    
    # Documentation
    find . -type f -name "*.md" \
        -not -path "*/node_modules/*" \
        -not -path "*/.git/*" \
        -exec sed -i '' "s/$OLD_PATTERN/$NEW_NAME/g" {} +
done

echo "Step 3: Verify no old references remain"
for replacement in "${REPLACEMENTS[@]}"; do
    OLD_PATTERN="${replacement%%:*}"
    COUNT=$(grep -r "$OLD_PATTERN" \
        --include="*.py" --include="*.ts" --include="*.tsx" \
        --include="*.js" --include="*.jsx" --include="*.md" \
        --include="*.yaml" --include="*.yml" \
        --exclude-dir=node_modules --exclude-dir=.git \
        --exclude-dir=dist --exclude-dir=logs \
        . 2>/dev/null | wc -l)
    
    if [ "$COUNT" -gt 0 ]; then
        echo "⚠️  WARNING: $COUNT references to $OLD_PATTERN still exist!"
        grep -r "$OLD_PATTERN" \
            --include="*.py" --include="*.ts" --include="*.md" \
            --exclude-dir=node_modules --exclude-dir=.git \
            . 2>/dev/null | head -10
    else
        echo "✓ No references to $OLD_PATTERN found"
    fi
done

echo "Step 4: Rename actual files"
# Add your file renaming commands here

echo "Step 5: Test"
# Run your test commands here
```

### Step 5: Verify Everything

```bash
# Check git diff
git diff --stat
git diff --name-only

# Verify critical files
cat << 'EOF' | bash
# Add verification commands for your specific files
test -f "new-file.json" && echo "✓ new-file.json exists"
grep -q "new-file.json" critical_script.py && echo "✓ Script references new name"
EOF

# Test without side effects
python3 your_script.py --dry-run
# or
python3 your_script.py --skip-git
```

### Step 6: Commit Safely

```bash
# Review all changes
git diff > review_changes.patch
less review_changes.patch

# Stage changes incrementally
git add pipeline/
git add dashboard/
git add docs/

# Commit with descriptive message
git commit -m "refactor: rename files for clarity

- old-file.json → new-file.json
- Rationale: [explain why]
- Updated 30 references across code and docs
- Tested with --dry-run flag"

# If anything breaks, easy rollback
git checkout main  # Go back to safety
```

## Key Takeaways

1. **Order matters** - Replace specific patterns before generic ones
2. **Escape dots** - Use `\.json` not `.json` in regex
3. **Test first** - Always use `--dry-run` or `--skip-git` flags
4. **Use branches** - Create feature branch before bulk changes
5. **Verify after** - grep for old pattern to catch missed replacements
6. **Include all file types** - Don't forget `.yaml`, `.sh`, `.md`, etc.

## Common Pitfalls

❌ **Substring matching**: `s/file.json/new.json/g` matches `myfile.json`
✅ **Solution**: Use word boundaries or be more specific

❌ **Forgotten file types**: Only updating `.py` files, missing `.ts` and `.md`
✅ **Solution**: Explicitly list all relevant extensions

❌ **Binary files**: Corrupting `.git/` or `node_modules/`
✅ **Solution**: Always exclude binary/generated directories

❌ **No verification**: Assuming replacements worked
✅ **Solution**: grep afterwards to confirm 0 old references remain
