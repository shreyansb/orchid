#!/bin/sh
# Link one orchid skill into an agent's skills folder. Never replaces an existing skill.
#   link-skill.sh <skill> --to claude|codex            dry run
#   link-skill.sh <skill> --to claude|codex --apply    create the symlink
#   link-skill.sh <skill> --to claude|codex --uninstall [--apply]
# The target folder is ~/.claude/skills or ~/.codex/skills (override with SKILLS_DIR).
set -eu

SKILL=""; TO=""; APPLY=""; UNINSTALL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --to) TO="${2:-}"; shift ;;
    --apply) APPLY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -*) echo "unknown option $1" >&2; exit 2 ;;
    *) SKILL="$1" ;;
  esac
  shift
done
[ -n "$SKILL" ] && [ -n "$TO" ] || { echo "usage: link-skill.sh <skill> --to claude|codex [--apply] [--uninstall]" >&2; exit 2; }

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/skills/$SKILL"
[ -f "$SRC/SKILL.md" ] || { echo "no such skill: $SKILL" >&2; exit 1; }
case "$TO" in
  claude) DIR="${SKILLS_DIR:-$HOME/.claude/skills}" ;;
  codex)  DIR="${SKILLS_DIR:-$HOME/.codex/skills}" ;;
  *) echo "--to must be claude or codex" >&2; exit 2 ;;
esac
DEST="$DIR/$SKILL"
act() { if [ -n "$APPLY" ]; then "$@"; else echo "would: $*"; fi; }

if [ -n "$UNINSTALL" ]; then
  if [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "$SRC" ]; then
    act rm "$DEST"
  else
    echo "$DEST is not an orchid link. Leaving it alone."
  fi
  [ -n "$APPLY" ] || echo "Dry run. Add --apply to do it."
  exit 0
fi

if [ -L "$DEST" ] && [ "$(readlink "$DEST")" = "$SRC" ]; then
  echo "already linked: $DEST -> $SRC"
  exit 0
fi
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  echo "refusing: $DEST already exists. Move it away yourself if you want orchid's version." >&2
  exit 1
fi
act mkdir -p "$DIR"
act ln -s "$SRC" "$DEST"
[ -n "$APPLY" ] || echo "Dry run. Add --apply to create the link."
