#!/bin/bash
################################################################################
# BULLETPROOF FILE RENAME SCRIPT TEMPLATE
# 
# This script demonstrates the complete process for safely finding and replacing
# file references across an entire repository.
#
# Usage: Copy this template, modify the REPLACEMENTS array, and run it.
################################################################################

set -e  # Exit immediately if a command fails
set -u  # Exit if undefined variable is used
set -o pipefail  # Propagate pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# CONFIGURATION SECTION - EDIT THIS FOR YOUR RENAME
################################################################################

# Define your replacements as "OLD_PATTERN:NEW_NAME" pairs
# CRITICAL: Order from MOST SPECIFIC to LEAST SPECIFIC!
# Example: Replace "api-old-file.json" before "old-file.json"
declare -a REPLACEMENTS=(
    # Format: "pattern-to-find:replacement-text"
    "api-old-file\.json:api-new-file.json"
    "old-file\.json:new-file.json"
    "another-old\.txt:another-new.txt"
)

# File extensions to search in
FILE_EXTENSIONS=(
    "*.py"      # Python
    "*.ts"      # TypeScript
    "*.tsx"     # TypeScript React
    "*.js"      # JavaScript
    "*.jsx"     # JavaScript React
    "*.md"      # Markdown
    "*.yaml"    # YAML
    "*.yml"     # YAML
    "*.json"    # JSON (be careful!)
    "*.sh"      # Shell scripts
    "*.txt"     # Text files
)

# Directories to EXCLUDE from search
EXCLUDE_DIRS=(
    "node_modules"
    ".git"
    "dist"
    "build"
    ".pytest_cache"
    "__pycache__"
    "logs"
    "backups"
    ".venv"
    "venv"
    "env"
)

# Actual file rename operations (optional)
# Format: "OLD_PATH:NEW_PATH"
declare -a FILE_RENAMES=(
    "path/to/old-file.json:path/to/new-file.json"
    "api-old.json:api-new.json"
)

# Files to delete (optional)
declare -a FILES_TO_DELETE=(
    "path/to/redundant-file.json"
)

################################################################################
# HELPER FUNCTIONS
################################################################################

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Build find command with all exclusions
build_find_exclude_args() {
    local args=""
    for dir in "${EXCLUDE_DIRS[@]}"; do
        args="$args -not -path '*/$dir/*'"
    done
    echo "$args"
}

# Build grep exclude arguments
build_grep_exclude_args() {
    local args=""
    for dir in "${EXCLUDE_DIRS[@]}"; do
        args="$args --exclude-dir=$dir"
    done
    echo "$args"
}

################################################################################
# STEP 1: COMPREHENSIVE SCAN
################################################################################
scan_for_references() {
    log_step "STEP 1: Scanning Repository for References"
    
    local scan_output_file="/tmp/rename_scan_$(date +%s).txt"
    
    echo "Scanning for references to:"
    for replacement in "${REPLACEMENTS[@]}"; do
        local pattern="${replacement%%:*}"
        local clean_pattern="${pattern//\\/}"  # Remove escape characters for display
        echo "  - $clean_pattern"
    done
    echo ""
    
    # Scan for each pattern
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local clean_pattern="${old_pattern//\\/}"
        
        echo "Searching for: $clean_pattern"
        
        local grep_excludes=$(build_grep_exclude_args)
        local include_args=""
        for ext in "${FILE_EXTENSIONS[@]}"; do
            include_args="$include_args --include=$ext"
        done
        
        # Use eval to properly expand arguments
        eval "grep -rn $include_args $grep_excludes '$old_pattern' . 2>/dev/null" | tee -a "$scan_output_file" || true
        
        echo ""
    done
    
    # Summary
    if [ -f "$scan_output_file" ]; then
        local total_matches=$(wc -l < "$scan_output_file")
        local total_files=$(cut -d: -f1 "$scan_output_file" | sort -u | wc -l)
        
        log_info "Scan complete!"
        log_info "  Total matches: $total_matches"
        log_info "  Total files: $total_files"
        log_info "  Results saved to: $scan_output_file"
        
        # Show files grouped by extension
        echo ""
        echo "Files by type:"
        cut -d: -f1 "$scan_output_file" | sort -u | sed 's/.*\.//' | sort | uniq -c | sort -rn
    else
        log_warn "No matches found"
    fi
    
    echo ""
    echo -e "${YELLOW}Press Enter to continue with replacements, or Ctrl+C to cancel...${NC}"
    read
}

################################################################################
# STEP 2: PERFORM REPLACEMENTS
################################################################################
perform_replacements() {
    log_step "STEP 2: Performing Find-and-Replace"
    
    echo "Replacing patterns in order (most specific first):"
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local new_name="${replacement##*:}"
        echo "  $old_pattern → $new_name"
    done
    echo ""
    
    # Apply replacements by file type
    local file_count=0
    
    # Python files
    log_info "Updating Python files..."
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local new_name="${replacement##*:}"
        
        find . -type f -name "*.py" \
            -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" \
            -not -path "*/.pytest_cache/*" -not -path "*/__pycache__/*" \
            -not -path "*/backups/*" -not -path "*/logs/*" \
            -exec sed -i '' "s/$old_pattern/$new_name/g" {} + 2>/dev/null || true
    done
    
    # TypeScript/JavaScript files
    log_info "Updating TypeScript/JavaScript files..."
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local new_name="${replacement##*:}"
        
        find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
            -not -path "*/node_modules/*" -not -path "*/.git/*" -not -path "*/dist/*" \
            -exec sed -i '' "s/$old_pattern/$new_name/g" {} + 2>/dev/null || true
    done
    
    # Configuration files (YAML/JSON)
    log_info "Updating configuration files..."
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local new_name="${replacement##*:}"
        
        find . -type f \( -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) \
            -not -path "*/node_modules/*" -not -path "*/.git/*" \
            -not -path "*/dist/*" -not -path "*/logs/*" -not -path "*/backups/*" \
            -exec sed -i '' "s/$old_pattern/$new_name/g" {} + 2>/dev/null || true
    done
    
    # Markdown documentation
    log_info "Updating Markdown documentation..."
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local new_name="${replacement##*:}"
        
        find . -type f -name "*.md" \
            -not -path "*/node_modules/*" -not -path "*/.git/*" \
            -exec sed -i '' "s/$old_pattern/$new_name/g" {} + 2>/dev/null || true
    done
    
    # Shell scripts
    log_info "Updating shell scripts..."
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local new_name="${replacement##*:}"
        
        find . -type f -name "*.sh" \
            -not -path "*/node_modules/*" -not -path "*/.git/*" \
            -exec sed -i '' "s/$old_pattern/$new_name/g" {} + 2>/dev/null || true
    done
    
    log_info "Find-and-replace complete!"
}

################################################################################
# STEP 3: VERIFY NO OLD REFERENCES REMAIN
################################################################################
verify_replacements() {
    log_step "STEP 3: Verifying Replacements"
    
    local all_clean=true
    
    for replacement in "${REPLACEMENTS[@]}"; do
        local old_pattern="${replacement%%:*}"
        local clean_pattern="${old_pattern//\\/}"
        
        echo "Checking for remaining references to: $clean_pattern"
        
        local grep_excludes=$(build_grep_exclude_args)
        local include_args=""
        for ext in "${FILE_EXTENSIONS[@]}"; do
            include_args="$include_args --include=$ext"
        done
        
        local matches=$(eval "grep -r $include_args $grep_excludes '$old_pattern' . 2>/dev/null" | wc -l)
        
        if [ "$matches" -gt 0 ]; then
            log_error "Found $matches remaining references to $clean_pattern!"
            eval "grep -rn $include_args $grep_excludes '$old_pattern' . 2>/dev/null" | head -10
            all_clean=false
        else
            log_info "✓ No references to $clean_pattern found"
        fi
        echo ""
    done
    
    if [ "$all_clean" = true ]; then
        log_info "✅ All old references successfully replaced!"
    else
        log_warn "⚠️  Some old references still exist. Review above."
        echo ""
        echo "Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_error "Aborted by user"
            exit 1
        fi
    fi
}

################################################################################
# STEP 4: RENAME ACTUAL FILES
################################################################################
rename_files() {
    log_step "STEP 4: Renaming Actual Files"
    
    # Delete files first (if any)
    if [ ${#FILES_TO_DELETE[@]} -gt 0 ]; then
        log_info "Deleting files..."
        for file_path in "${FILES_TO_DELETE[@]}"; do
            if [ -f "$file_path" ]; then
                rm "$file_path"
                log_info "  ✓ Deleted: $file_path"
            else
                log_warn "  ⚠ Not found: $file_path"
            fi
        done
    fi
    
    # Rename files
    if [ ${#FILE_RENAMES[@]} -gt 0 ]; then
        log_info "Renaming files..."
        for rename_pair in "${FILE_RENAMES[@]}"; do
            local old_path="${rename_pair%%:*}"
            local new_path="${rename_pair##*:}"
            
            if [ -f "$old_path" ]; then
                mv "$old_path" "$new_path"
                log_info "  ✓ Renamed: $old_path → $new_path"
            else
                log_warn "  ⚠ Not found: $old_path"
            fi
        done
    fi
    
    log_info "File operations complete!"
}

################################################################################
# STEP 5: VERIFY RESULTS
################################################################################
verify_results() {
    log_step "STEP 5: Verifying Results"
    
    # Check renamed files exist
    log_info "Checking renamed files exist..."
    for rename_pair in "${FILE_RENAMES[@]}"; do
        local new_path="${rename_pair##*:}"
        if [ -f "$new_path" ]; then
            local size=$(ls -lh "$new_path" | awk '{print $5}')
            log_info "  ✓ $new_path ($size)"
        else
            log_error "  ✗ $new_path NOT FOUND!"
        fi
    done
    
    # Check deleted files are gone
    if [ ${#FILES_TO_DELETE[@]} -gt 0 ]; then
        log_info "Checking deleted files are gone..."
        for file_path in "${FILES_TO_DELETE[@]}"; do
            if [ ! -f "$file_path" ]; then
                log_info "  ✓ $file_path deleted"
            else
                log_error "  ✗ $file_path still exists!"
            fi
        done
    fi
    
    # Show git status
    log_info "Git status:"
    git status --short | head -30
    
    # Show statistics
    echo ""
    log_info "Git diff statistics:"
    git diff --stat | tail -5
}

################################################################################
# STEP 6: TEST
################################################################################
run_tests() {
    log_step "STEP 6: Running Tests"
    
    # Add your test commands here
    log_info "Add your test commands in the run_tests() function"
    
    # Example tests:
    # - Verify JSON files are valid
    # - Run --dry-run mode of your pipeline
    # - Check critical imports work
    # - Run unit tests
    
    echo ""
    echo "Example test commands:"
    echo "  python3 -c 'import json; json.load(open(\"new-file.json\"))'"
    echo "  python3 your_script.py --dry-run"
    echo "  npm run type-check"
    echo "  pytest"
}

################################################################################
# MAIN EXECUTION
################################################################################
main() {
    log_step "BULLETPROOF FILE RENAME SCRIPT"
    
    echo "This script will:"
    echo "  1. Scan repository for ALL references to old filenames"
    echo "  2. Replace references (most specific patterns first)"
    echo "  3. Verify no old references remain"
    echo "  4. Rename actual files"
    echo "  5. Verify results with git status"
    echo "  6. Run tests"
    echo ""
    echo "Total replacements: ${#REPLACEMENTS[@]}"
    echo "Total file renames: ${#FILE_RENAMES[@]}"
    echo "Total deletions: ${#FILES_TO_DELETE[@]}"
    echo ""
    
    # Safety check: Are we in a git repo?
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_error "Not in a git repository! Aborting."
        exit 1
    fi
    
    # Safety check: Are there uncommitted changes?
    if [ -n "$(git status --porcelain)" ]; then
        log_warn "You have uncommitted changes!"
        echo "Create a backup branch first? (Y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Nn]$ ]]; then
            local branch_name="refactor/file-rename-$(date +%Y%m%d-%H%M%S)"
            git checkout -b "$branch_name"
            log_info "Created backup branch: $branch_name"
        fi
    fi
    
    echo ""
    echo -e "${YELLOW}Press Enter to start, or Ctrl+C to cancel...${NC}"
    read
    
    # Execute steps
    scan_for_references
    perform_replacements
    verify_replacements
    rename_files
    verify_results
    run_tests
    
    # Final summary
    log_step "✅ RENAME COMPLETE"
    
    echo ""
    echo "Next steps:"
    echo "  1. Review changes:  git diff"
    echo "  2. Review specific: git diff path/to/file"
    echo "  3. Test manually:   [run your app/tests]"
    echo "  4. Commit changes:  git add . && git commit -m 'refactor: rename files'"
    echo "  5. If broken:       git checkout main (or your previous branch)"
    echo ""
}

################################################################################
# EXECUTION
################################################################################

# Check if running with --help
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Bulletproof File Rename Script"
    echo ""
    echo "Usage: $0"
    echo ""
    echo "Before running:"
    echo "  1. Edit the REPLACEMENTS array with your patterns"
    echo "  2. Edit FILE_RENAMES array with actual file moves"
    echo "  3. Edit FILES_TO_DELETE array with files to remove"
    echo "  4. Edit run_tests() function with your test commands"
    echo ""
    echo "Features:"
    echo "  - Scans entire repository"
    echo "  - Excludes binary/generated directories"
    echo "  - Replaces in correct order (specific before generic)"
    echo "  - Verifies no old references remain"
    echo "  - Shows git diff statistics"
    echo "  - Creates backup branch"
    echo ""
    exit 0
fi

# Run main
main

################################################################################
# ADDITIONAL TIPS
################################################################################
# 
# 1. TEST FIRST WITH A SMALL SUBSET:
#    - Comment out most REPLACEMENTS, test with just one
#    - Verify it works correctly before enabling all replacements
#
# 2. USE WORD BOUNDARIES IF NEEDED:
#    - sed 's/\bword\b/new/g' only matches whole word
#    - sed 's/word/new/g' matches substring too
#
# 3. ESCAPE SPECIAL REGEX CHARACTERS:
#    - Dots: file\.json not file.json
#    - Dashes: my-file not my-file (dashes are safe in character class)
#    - Slashes: path\/to\/file or use different delimiter: s|path/to|new/path|g
#
# 4. VERIFY JSON FILES REMAIN VALID:
#    python3 -c "import json; json.load(open('file.json'))"
#
# 5. DRY RUN OPTION:
#    Set DRY_RUN=1 at top to only show what would happen
#
################################################################################
