#!/bin/sh
# Copy a file to a destination without clobbering. Shows a diff and backs up first.
#   safe-write.sh <source> <destination>            dry run: show what would happen
#   safe-write.sh <source> <destination> --apply    write (backup made if dest exists)
# Use it for every file orchid puts in the person's home folder or config.
set -eu

SRC="${1:-}"; DEST="${2:-}"; APPLY=""
[ "${3:-}" = "--apply" ] && APPLY=1
[ -f "$SRC" ] && [ -n "$DEST" ] || { echo "usage: safe-write.sh <source> <destination> [--apply]" >&2; exit 2; }

if [ ! -e "$DEST" ]; then
  echo "new file: $DEST"
  if [ -n "$APPLY" ]; then mkdir -p "$(dirname "$DEST")"; cp "$SRC" "$DEST"; else echo "would: copy $SRC -> $DEST"; fi
  exit 0
fi
if cmp -s "$SRC" "$DEST"; then
  echo "unchanged: $DEST"
  exit 0
fi
echo "exists and differs: $DEST"
diff -u "$DEST" "$SRC" || true
BAK="$DEST.orchid-bak-$(date +%Y%m%d-%H%M%S)"
if [ -n "$APPLY" ]; then cp "$DEST" "$BAK"; cp "$SRC" "$DEST"; echo "backup: $BAK"; else echo "would: back up to $BAK, then overwrite"; fi
