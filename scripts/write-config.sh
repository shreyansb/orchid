#!/bin/sh
# Write the orchid config from three answers. Validates them first, so a placeholder such as
# <machine-label> can never be saved. Dry run by default; shows a diff; backs up an old config.
#   write-config.sh --home ~/orchid-home --orchestrator orchid --label laptop            dry run
#   write-config.sh --home ~/orchid-home --orchestrator orchid --label laptop --apply    write
# Default destination: $ORCHID_CONFIG, or ~/.config/orchid/config.
set -eu

HOME_DIR=""; ORCH=""; LABEL=""; APPLY=""; DEST="${ORCHID_CONFIG:-$HOME/.config/orchid/config}"
while [ $# -gt 0 ]; do
  case "$1" in
    --home) HOME_DIR="${2:-}"; shift ;;
    --orchestrator) ORCH="${2:-}"; shift ;;
    --label) LABEL="${2:-}"; shift ;;
    --config) DEST="${2:-}"; shift ;;
    --apply) APPLY=1 ;;
    *) echo "unknown option $1" >&2; exit 2 ;;
  esac
  shift
done
REPO="$(cd "$(dirname "$0")/.." && pwd)"

fail() { echo "error: $*" >&2; exit 2; }
[ -n "$HOME_DIR" ] || fail "--home is required"
[ -n "$ORCH" ] || fail "--orchestrator is required"
[ -n "$LABEL" ] || fail "--label is required (a short name for this machine, for example laptop)"
case "$LABEL" in *'<'*|*'>'*|*/*) fail "label must not contain <, > or / (got: $LABEL)" ;; esac
echo "$ORCH" | grep -Eq '^[a-z][a-z0-9_-]{0,31}$' || fail "orchestrator must be a herdr agent name: lowercase letters, digits, - and _, starting with a letter, 32 characters at most (got: $ORCH)"

TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
awk -v h="$HOME_DIR" -v o="$ORCH" -v l="$LABEL" '
  /^home=/ { print "home=" h; next }
  /^orchestrator=/ { print "orchestrator=" o; next }
  /^machine_label=/ { print "machine_label=" l; next }
  { print }' "$REPO/templates/config" > "$TMP"

if [ -n "$APPLY" ]; then sh "$REPO/scripts/safe-write.sh" "$TMP" "$DEST" --apply; else sh "$REPO/scripts/safe-write.sh" "$TMP" "$DEST"; echo "Dry run. Add --apply to write."; fi
