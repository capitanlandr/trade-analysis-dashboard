#!/bin/bash
# Setup git hooks for the project
# Run this after cloning the repository: ./setup-hooks.sh

echo "🔧 Setting up git hooks..."

# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/sh
# Pre-commit hook: Run TypeScript type checking on staged files
# Regenerate using: ./setup-hooks.sh

echo "🔍 Running pre-commit checks..."

# Get root directory
ROOT_DIR=$(git rev-parse --show-toplevel)
FRONTEND_DIR="$ROOT_DIR/dashboard/frontend"

# Check if any TypeScript files are staged
STAGED_TS_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx)$' | grep "^dashboard/frontend/")

if [ -n "$STAGED_TS_FILES" ]; then
  echo "📝 TypeScript files changed, running type check..."
  
  cd "$FRONTEND_DIR"
  
  # Run TypeScript compiler in check mode
  npx tsc --noEmit
  
  if [ $? -ne 0 ]; then
    echo "❌ TypeScript errors found. Commit aborted."
    echo "Fix the errors above or use 'git commit --no-verify' to skip checks."
    exit 1
  fi
  
  echo "✅ TypeScript check passed"
fi

# Check Python files (if any staged)
STAGED_PY_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' | grep "^pipeline/")

if [ -n "$STAGED_PY_FILES" ]; then
  echo "🐍 Python files changed, running validation..."
  
  cd "$ROOT_DIR"
  
  # Check Python syntax
  for file in $STAGED_PY_FILES; do
    python3 -m py_compile "$file" 2>/dev/null
    if [ $? -ne 0 ]; then
      echo "❌ Python syntax error in: $file"
      exit 1
    fi
  done
  
  echo "✅ Python validation passed"
fi

echo "✨ All checks passed!"
exit 0
EOF

# Make hook executable
chmod +x .git/hooks/pre-commit

echo "✅ Git hooks installed successfully!"
echo ""
echo "Pre-commit hook will now:"
echo "  • Run TypeScript type checking on .ts/.tsx files"
echo "  • Validate Python syntax on .py files"
echo "  • Skip checks with: git commit --no-verify"