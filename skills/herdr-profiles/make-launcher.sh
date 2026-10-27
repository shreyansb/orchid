#!/bin/sh
# Make a small launcher for one login profile, so the person can type one command.
#   make-launcher.sh <command-name> claude|codex <config-dir>            dry run
#   make-launcher.sh <command-name> claude|codex <config-dir> --apply    write ~/.local/bin/<command-name>
# Claude Code reads its login from CLAUDE_CONFIG_DIR. Codex reads it from CODEX_HOME,
# which must be an existing folder. No shell startup files are edited.
set -eu

NAME="${1:-}"; KIND="${2:-}"; DIR="${3:-}"; APPLY=""
[ "${4:-}" = "--apply" ] && APPLY=1
[ -n "$NAME" ] && [ -n "$DIR" ] || { echo "usage: make-launcher.sh <command-name> claude|codex <config-dir> [--apply]" >&2; exit 2; }
case "$KIND" in
  claude) VAR=CLAUDE_CONFIG_DIR; BIN=claude ;;
  codex)  VAR=CODEX_HOME; BIN=codex ;;
  *) echo "kind must be claude or codex" >&2; exit 2 ;;
esac
case "$NAME" in *[!a-zA-Z0-9_-]*|"") echo "command name: letters, digits, - and _ only" >&2; exit 2 ;; esac
command -v "$NAME" >/dev/null 2>&1 && { echo "refusing: a command named $NAME already exists on PATH" >&2; exit 1; }

TARGET="$HOME/.local/bin/$NAME"
[ -e "$TARGET" ] && { echo "refusing: $TARGET already exists" >&2; exit 1; }
CONTENT="#!/bin/sh
# Orchid profile launcher: $KIND with its own login.
$VAR=\"$DIR\" exec $BIN \"\$@\""

echo "launcher: $TARGET"
echo "$CONTENT"
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) echo "note: $HOME/.local/bin is not on your PATH. Add it yourself, or run the launcher by full path." ;; esac

if [ -n "$APPLY" ]; then
  mkdir -p "$(dirname "$TARGET")" "$DIR"
  printf '%s\n' "$CONTENT" > "$TARGET"
  chmod +x "$TARGET"
  echo "written. Undo: rm $TARGET"
else
  echo "Dry run. Add --apply to write it."
fi
