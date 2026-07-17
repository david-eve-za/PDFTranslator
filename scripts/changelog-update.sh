#!/usr/bin/env bash
# scripts/changelog-update.sh
# Automated CHANGELOG.md update following Keep a Changelog format
# Usage: ./scripts/changelog-update.sh v0.2.0

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 v0.2.0"
    exit 1
fi

CHANGELOG="CHANGELOG.md"
TEMP_CHANGELOG="${CHANGELOG}.tmp"
DATE=$(date +%Y-%m-%d)

echo "Updating CHANGELOG for $VERSION..."

# Read current changelog
if [[ ! -f "$CHANGELOG" ]]; then
    echo "ERROR: $CHANGELOG not found"
    exit 1
fi

# Extract [Unreleased] section
UNRELEASED=$(sed -n '/^## \[Unreleased\]/,/^## \[/p' "$CHANGELOG" | head -n -1)

if [[ -z "$UNRELEASED" || "$UNRELEASED" == "## [Unreleased]" ]]; then
    echo "WARNING: No content in [Unreleased] section"
    # Still create version section
    UNRELEASED_CONTENT=""
else
    UNRELEASED_CONTENT="$UNRELEASED"
fi

# Create new version entry
NEW_VERSION="## [$VERSION] - $DATE

$UNRELEASED_CONTENT

---

"

# Replace [Unreleased] section and add new version
awk -v new_version="$NEW_VERSION" '
    /^## \[Unreleased\]/ {
        print $0
        print ""
        print "### Added"
        print "- "
        print ""
        print "### Changed"
        print "- "
        print ""
        print "### Deprecated"
        print "- "
        print ""
        print "### Removed"
        print "- "
        print ""
        print "### Fixed"
        print "- "
        print ""
        print "### Security"
        print "- "
        print ""
        print "---"
        print new_version
        next
    }
    { print }
' "$CHANGELOG" > "$TEMP_CHANGELOG"

mv "$TEMP_CHANGELOG" "$CHANGELOG"

echo "✅ CHANGELOG.md updated for $VERSION"
echo ""
echo "Please edit CHANGELOG.md to fill in the release details, then commit:"
echo "  git add CHANGELOG.md"
echo "  git commit -m \"chore(changelog): update for $VERSION\""