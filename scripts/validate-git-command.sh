#!/bin/bash
# Git command safety validator for the git-ops agent.
# Runs as a PreToolUse hook — blocks dangerous git operations.
# Exit 0 = allow, Exit 2 = block (feeds error message back to agent).

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$COMMAND" ]; then
  exit 0
fi

# Block force push (any form)
if echo "$COMMAND" | grep -iE 'git\s+push\s+.*--force|git\s+push\s+.*-f\b|git\s+push\s+--force' > /dev/null; then
  echo "BLOCKED: Force push is never allowed. Use regular push only." >&2
  exit 2
fi

# Block reset --hard
if echo "$COMMAND" | grep -iE 'git\s+reset\s+--hard' > /dev/null; then
  echo "BLOCKED: git reset --hard destroys uncommitted work. Use git stash instead." >&2
  exit 2
fi

# Block checkout . (discard all changes)
if echo "$COMMAND" | grep -iE 'git\s+checkout\s+\.' > /dev/null; then
  echo "BLOCKED: git checkout . discards all changes. Use git stash instead." >&2
  exit 2
fi

# Block restore . (discard all changes)
if echo "$COMMAND" | grep -iE 'git\s+restore\s+\.' > /dev/null; then
  echo "BLOCKED: git restore . discards all changes. Use git stash instead." >&2
  exit 2
fi

# Block clean -f (delete untracked files)
if echo "$COMMAND" | grep -iE 'git\s+clean\s+.*-f' > /dev/null; then
  echo "BLOCKED: git clean -f permanently deletes untracked files. Not allowed." >&2
  exit 2
fi

# Block branch -D (force delete branch)
if echo "$COMMAND" | grep -iE 'git\s+branch\s+.*-D' > /dev/null; then
  echo "BLOCKED: git branch -D force-deletes branches. Use -d (safe delete) instead." >&2
  exit 2
fi

# Block rebase (can rewrite history)
if echo "$COMMAND" | grep -iE 'git\s+rebase' > /dev/null; then
  echo "BLOCKED: git rebase rewrites history. Not allowed in safe git-ops." >&2
  exit 2
fi

# Block --no-verify (skips hooks)
if echo "$COMMAND" | grep -iE 'git\s+.*--no-verify' > /dev/null; then
  echo "BLOCKED: --no-verify skips safety hooks. Not allowed." >&2
  exit 2
fi

# Block amend (rewrites last commit)
if echo "$COMMAND" | grep -iE 'git\s+commit\s+.*--amend' > /dev/null; then
  echo "BLOCKED: --amend rewrites the last commit. Create a new commit instead." >&2
  exit 2
fi

# Block push to main/master without explicit branch
if echo "$COMMAND" | grep -iE 'git\s+push\s+(origin\s+)?(main|master)\b' > /dev/null; then
  # Allow it but warn — the agent prompt already requires backup-first
  :
fi

exit 0
