#!/bin/sh
# 把本仓的 media profile 安装到 ~/.dsh/profiles/media（默认备份后覆盖）。
# 用法: ./scripts/install.sh [--link]
set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)
DEST=$HOME/.dsh/profiles/media
MODE=copy
if [ $# -gt 0 ]; then MODE=$1; fi
TS=$(date +%Y%m%dT%H%M%S)

if [ -e "$DEST" ]; then
  BAK=$HOME/.dsh/backups/media-profile-$TS
  mkdir -p "$HOME/.dsh/backups"
  mv "$DEST" "$BAK"
  echo "backed up: $BAK"
fi

mkdir -p "$HOME/.dsh/profiles"
if [ "$MODE" = "--link" ]; then
  ln -sfn "$REPO/profile" "$DEST"
  echo "linked: $DEST -> $REPO/profile"
else
  cp -R "$REPO/profile" "$DEST"
  echo "copied: $DEST"
fi

echo
echo "next:"
echo "  1. edit $DEST/cordis.patch.yml if the MCP binaries live elsewhere"
echo "  2. run $REPO/scripts/verify.sh"