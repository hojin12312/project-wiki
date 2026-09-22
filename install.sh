#!/bin/sh
# Link the wiki-init / wiki-update skills into each agent harness.
#
#   sh install.sh            install (default)
#   sh install.sh status     show link state
#   sh install.sh uninstall  remove only links that point into this package
#
# Targets (a target is used only when its harness is present on this machine):
#   ~/.claude/skills/           Claude Code
#   ~/.agents/skills/           Pi, Devin CLI, Codex
#   ~/.config/opencode/skills/  OpenCode
# Existing files or foreign links are never overwritten.
set -eu

PKG_DIR=$(cd "$(dirname "$0")" && pwd -P)
SKILLS="wiki-init wiki-update"
MODE=${1:-install}

targets() {
    if [ -d "$HOME/.claude" ]; then
        echo "$HOME/.claude/skills"
    fi
    if [ -d "$HOME/.pi/agent" ] || [ -d "$HOME/.config/devin" ] || [ -d "$HOME/.codex" ]; then
        echo "$HOME/.agents/skills"
    fi
    if [ -d "$HOME/.config/opencode" ]; then
        echo "$HOME/.config/opencode/skills"
    fi
}

status=0
for dir in $(targets); do
    for skill in $SKILLS; do
        link="$dir/$skill"
        want="$PKG_DIR/$skill"
        case "$MODE" in
        install)
            if [ -L "$link" ]; then
                have=$(readlink "$link")
                if [ "$have" = "$want" ]; then
                    echo "ok       $link"
                else
                    echo "CONFLICT $link -> $have (not replaced)" >&2
                    status=1
                    continue
                fi
            elif [ -e "$link" ]; then
                echo "CONFLICT $link exists and is not a symlink (not replaced)" >&2
                status=1
                continue
            else
                mkdir -p "$dir"
                ln -s "$want" "$link"
                echo "linked   $link -> $want"
            fi
            if [ ! -f "$link/SKILL.md" ] || [ ! -f "$link/core/protocol.md" ]; then
                echo "BROKEN   $link: SKILL.md or core/protocol.md not reachable" >&2
                status=1
            fi
            ;;
        status)
            if [ -L "$link" ]; then
                echo "$link -> $(readlink "$link")"
            elif [ -e "$link" ]; then
                echo "$link (not a symlink)"
            else
                echo "$link (missing)"
            fi
            ;;
        uninstall)
            if [ -L "$link" ] && [ "$(readlink "$link")" = "$want" ]; then
                rm "$link"
                echo "removed  $link"
            fi
            ;;
        *)
            echo "usage: sh install.sh [install|status|uninstall]" >&2
            exit 2
            ;;
        esac
    done
done

if [ "$MODE" = install ] && [ "$status" -eq 0 ]; then
    python3 "$PKG_DIR/core/scripts/wiki_state.py" self-update >/dev/null 2>&1 || true
    python3 -c 'import sys; assert sys.version_info >= (3, 8)' 2>/dev/null \
        || { echo "python3 >= 3.8 is required" >&2; status=1; }
fi
exit "$status"
