#!/bin/sh
# Create the orchid home folder and fill it from the templates. Dry run by default.
#   init-home.sh <home-folder>            dry run: print every folder and file it would create
#   init-home.sh <home-folder> --apply    create them (existing files are diffed and backed up first)
# Every file goes through safe-write.sh, so nothing is overwritten without a diff and a backup.
set -eu

HOME_DIR="${1:-}"; APPLY=""
[ "${2:-}" = "--apply" ] && APPLY=1
[ -n "$HOME_DIR" ] || { echo "usage: init-home.sh <home-folder> [--apply]" >&2; exit 2; }
case "$HOME_DIR" in
  "~") HOME_DIR="$HOME" ;;
  "~/"*) HOME_DIR="$HOME/${HOME_DIR#"~/"}" ;;
  '$HOME/'*) HOME_DIR="$HOME/${HOME_DIR#'$HOME/'}" ;;
esac
case "$HOME_DIR" in /*) ;; *) echo "home folder must be a full path or start with ~/" >&2; exit 2 ;; esac

REPO="$(cd "$(dirname "$0")/.." && pwd)"
case "$HOME_DIR/" in "$REPO"/*) echo "refusing: the home folder must not be inside the orchid repo ($REPO)" >&2; exit 1 ;; esac

echo "home folder: $HOME_DIR"
for d in "$HOME_DIR" "$HOME_DIR/tasks" "$HOME_DIR/done"; do
  if [ -d "$d" ]; then echo "exists: $d"
  elif [ -n "$APPLY" ]; then mkdir -p "$d"; echo "created: $d"
  else echo "would: mkdir -p $d"; fi
done

copy() {  # copy <template> <destination-name>
  if [ -n "$APPLY" ]; then sh "$REPO/scripts/safe-write.sh" "$REPO/templates/$1" "$HOME_DIR/$2" --apply
  else sh "$REPO/scripts/safe-write.sh" "$REPO/templates/$1" "$HOME_DIR/$2"; fi
}
copy AGENTS.md AGENTS.md
copy CLAUDE.md CLAUDE.md
copy board.md board.md
copy journal.md journal.md
copy spaces.md spaces.md
copy task.md task-template.md

[ -n "$APPLY" ] || echo "Dry run. Add --apply to create."
