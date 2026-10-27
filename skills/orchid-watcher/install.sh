#!/bin/sh
# Install or remove the orchid watcher as a launchd job (macOS).
#   install.sh               dry run: show everything, change nothing
#   install.sh --apply       install (backs up an existing plist first)
#   install.sh --uninstall   dry run of the removal
#   install.sh --uninstall --apply
# The watcher reads home, orchestrator name and machine label from the orchid config.
set -eu

APPLY=""; UNINSTALL=""
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    *) echo "usage: install.sh [--apply] [--uninstall]" >&2; exit 2 ;;
  esac
done

LABEL="dev.orchid.watcher"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$REPO/skills/orchid-watcher/orchid_watcher.py"
TEMPLATE="$REPO/launchd/$LABEL.plist.template"
CONFIG="${ORCHID_CONFIG:-$HOME/.config/orchid/config}"
STATE="$(dirname "$CONFIG")"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"
STAMP="$(date +%Y%m%d-%H%M%S)"

say() { echo "$*"; }
act() { if [ -n "$APPLY" ]; then "$@"; else say "would: $*"; fi; }

if [ "$(uname -s)" != "Darwin" ]; then
  say "The watcher uses launchd and runs on macOS only. On Linux everything else works;" >&2
  say "a systemd unit is future work. Nothing was changed." >&2
  exit 3
fi

if [ -n "$UNINSTALL" ]; then
  if [ -f "$PLIST" ] && grep -q "<string>$LABEL</string>" "$PLIST"; then
    act launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    act mv "$PLIST" "$PLIST.orchid-removed-$STAMP"
    say "The plist is moved aside, not deleted. Delete $PLIST.orchid-removed-$STAMP when you are sure."
  else
    say "No orchid watcher plist found at $PLIST. Nothing to remove."
  fi
  [ -n "$APPLY" ] || say "Dry run. Add --apply to do it."
  exit 0
fi

HERDR="$(command -v herdr || true)"
[ -n "$HERDR" ] || { say "herdr is not on PATH. Install herdr first." >&2; exit 1; }
if [ -x /usr/bin/python3 ]; then PY=/usr/bin/python3; else PY="$(command -v python3 || true)"; fi
[ -n "$PY" ] || { say "python3 not found." >&2; exit 1; }
[ -f "$CONFIG" ] || { say "No orchid config at $CONFIG. Create it first (see skills/orchid-tasks)." >&2; exit 1; }
[ -f "$TEMPLATE" ] || { say "Missing template $TEMPLATE" >&2; exit 1; }

# PATH for the job: the folder of the herdr we found, common tool folders, then the system.
PATHVAL="$(dirname "$HERDR"):/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
PATHVAL="$(echo "$PATHVAL" | tr ':' '\n' | awk '!seen[$0]++' | paste -sd: -)"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
"$PY" - "$TEMPLATE" "$TMP/new.plist" "$PY" "$SCRIPT" "$PATHVAL" "$CONFIG" "$STATE/watcher.log" <<'EOF'
import sys
from xml.sax.saxutils import escape
src, dst, py, script, path, config, log = sys.argv[1:8]
text = open(src).read()
for key, value in (("__PYTHON__", py), ("__SCRIPT__", script), ("__PATH__", path),
                   ("__CONFIG__", config), ("__LOG__", log)):
    text = text.replace(key, escape(value))
open(dst, "w").write(text)
EOF
plutil -lint "$TMP/new.plist" >/dev/null && say "plist renders and passes plutil -lint"

say "label:   $LABEL"
say "script:  $SCRIPT"
say "python:  $PY"
say "herdr:   $HERDR"
say "config:  $CONFIG"
say "log:     $STATE/watcher.log"

if [ -f "$PLIST" ]; then
  if cmp -s "$PLIST" "$TMP/new.plist"; then
    say "plist is already up to date"
  else
    say "plist exists and differs. Diff (current -> new):"
    diff -u "$PLIST" "$TMP/new.plist" || true
    act cp "$PLIST" "$PLIST.orchid-bak-$STAMP"
    act cp "$TMP/new.plist" "$PLIST"
  fi
else
  act mkdir -p "$(dirname "$PLIST")" "$STATE"
  act cp "$TMP/new.plist" "$PLIST"
fi
act launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
act launchctl bootstrap "$DOMAIN" "$PLIST"
[ -n "$APPLY" ] || say "Dry run. Add --apply to install."
