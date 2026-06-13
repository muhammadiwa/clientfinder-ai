#!/bin/bash
# =============================================================
# ClientFinder — Auto-create PR + Merge to develop
# =============================================================
# Usage:
#   ./scripts/auto-pr-merge.sh <branch-name> [commit-message]
#
# Examples:
#   ./scripts/auto-pr-merge.sh feature/t3-frontend-core
#   ./scripts/auto-pr-merge.sh feature/t3-frontend-core "feat(T3): vite init"
#
# Effect:
#   1. Creates a PR from <branch-name> → develop (if not exists)
#   2. Auto-merges it with squash to keep history linear
#   3. Deletes the local feature branch (since develop has it now)
#
# Requires: GITHUB_TOKEN env var with `repo` scope
# =============================================================

set -euo pipefail

BRANCH="${1:-}"
COMMIT_MSG="${2:-Auto-merge from $BRANCH}"

if [ -z "$BRANCH" ]; then
    echo "Usage: $0 <branch-name> [commit-message]"
    echo "Example: $0 feature/t3-frontend-core"
    exit 1
fi

# Load env (for GITHUB_TOKEN)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

if [ -f .env ]; then
    # shellcheck disable=SC1091
    set -a; source .env; set +a
fi

TOKEN="${GITHUB_TOKEN:-${GHP_TOKEN:-}}"
REPO="muhammadiwa/clientfinder-ai"
API="https://api.github.com"

if [ -z "$TOKEN" ]; then
    echo "✗ GITHUB_TOKEN not set. Add to .env or export before running."
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "✗ You are on '$CURRENT_BRANCH', expected '$BRANCH'"
    echo "  Run: git checkout $BRANCH"
    exit 1
fi

# Check that branch has been pushed
if ! git ls-remote --heads origin "$BRANCH" | grep -q "$BRANCH"; then
    echo "✗ Branch '$BRANCH' not pushed to remote yet."
    echo "  Run: git push -u origin $BRANCH"
    exit 1
fi

# Check if PR already exists
EXISTING_PR=$(curl -s -H "Authorization: token $TOKEN" -H "Accept: application/vnd.github+json" \
    "$API/repos/$REPO/pulls?state=open&head=$REPO:$BRANCH" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print(d[0]['number'] if d else '')" 2>/dev/null)

if [ -n "$EXISTING_PR" ]; then
    PR_NUMBER="$EXISTING_PR"
    PR_URL="https://github.com/$REPO/pull/$PR_NUMBER"
    echo "→ PR #$PR_NUMBER already exists for $BRANCH"
else
    echo "→ Creating PR from $BRANCH → develop..."

    # Get the latest commit message to use as PR title
    LATEST_COMMIT=$(git log -1 --format="%s" origin/"$BRANCH" 2>/dev/null || echo "Work in progress")
    PR_BODY="Auto-merged via scripts/auto-pr-merge.sh

**Branch:** \`$BRANCH\`
**Target:** \`develop\`
**Latest commit:** $LATEST_COMMIT

🤖 Generated with auto-merge"

    CREATE_RESP=$(curl -s -X POST \
        -H "Authorization: token $TOKEN" \
        -H "Accept: application/vnd.github+json" \
        "$API/repos/$REPO/pulls" \
        -d "$(python3 -c "
import json, sys
print(json.dumps({
    'title': '$LATEST_COMMIT',
    'head': '$BRANCH',
    'base': 'develop',
    'body': '''$PR_BODY''',
    'maintainer_can_modify': True
}))
")")

    PR_NUMBER=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('number',''))" 2>/dev/null)
    PR_URL=$(echo "$CREATE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('html_url',''))" 2>/dev/null)

    if [ -z "$PR_NUMBER" ]; then
        echo "✗ Failed to create PR. Response:"
        echo "$CREATE_RESP" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESP"
        exit 1
    fi
    echo "✓ PR #$PR_NUMBER created: $PR_URL"
fi

# Merge the PR
echo "→ Merging PR #$PR_NUMBER (squash)..."
MERGE_RESP=$(curl -s -X PUT \
    -H "Authorization: token $TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "$API/repos/$REPO/pulls/$PR_NUMBER/merge" \
    -d "$(python3 -c "
import json
print(json.dumps({
    'commit_title': '$COMMIT_MSG',
    'commit_message': 'Auto-merged via scripts/auto-pr-merge.sh',
    'sha': '$(curl -s -H "Authorization: token $TOKEN" "$API/repos/$REPO/pulls/$PR_NUMBER" | python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])" 2>/dev/null)',
    'merge_method': 'squash'
}))
")")

MERGED=$(echo "$MERGE_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('merged', False))" 2>/dev/null)

if [ "$MERGED" = "True" ]; then
    echo "✓ PR #$PR_NUMBER merged to develop"
    echo "  URL: $PR_URL"
else
    echo "✗ Merge failed. Response:"
    echo "$MERGE_RESP" | python3 -m json.tool 2>/dev/null || echo "$MERGE_RESP"
    exit 1
fi

# Switch local to develop and pull latest
echo "→ Switching to develop and pulling latest..."
git checkout develop
git pull origin develop

# Optionally delete the local feature branch
git branch -d "$BRANCH" 2>/dev/null && echo "  Deleted local branch: $BRANCH" || true

echo ""
echo "✓ Done. $BRANCH → develop (via PR #$PR_NUMBER)"
