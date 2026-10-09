#!/usr/bin/env bash
# 把本仓库的技能安全地链接到 Codex 技能目录。
# 只创建软链；目标已存在时跳过，绝不覆盖、绝不删除任何文件。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$REPO_DIR/skills"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DEST_DIR="$CODEX_HOME/skills"

if [ ! -d "$SRC_DIR" ]; then
  echo "错误：找不到 $SRC_DIR" >&2
  exit 1
fi

mkdir -p "$DEST_DIR"

linked=0
skipped=0
failed=0

link_one() {
  local src="$1" dest="$2" label="$3"
  if [ -L "$dest" ]; then
    if [ "$(readlink "$dest")" = "$src" ]; then
      echo "  已链接  $label"
      skipped=$((skipped + 1))
      return
    fi
    echo "  跳过    $label（已存在软链 -> $(readlink "$dest")）"
    skipped=$((skipped + 1))
    return
  fi
  if [ -e "$dest" ]; then
    echo "  跳过    $label（本地已有同名目录，未覆盖）"
    skipped=$((skipped + 1))
    return
  fi
  if ln -s "$src" "$dest" 2>/dev/null; then
    echo "  已链接  $label"
    linked=$((linked + 1))
  else
    echo "  失败    $label（无法创建软链，请检查权限）" >&2
    failed=$((failed + 1))
  fi
}

echo "技能来源：$SRC_DIR"
echo "目标目录：$DEST_DIR"
echo

echo "[用户技能]"
for skill_dir in "$SRC_DIR"/*/; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  link_one "${skill_dir%/}" "$DEST_DIR/$name" "$name"
done

echo
echo "[Codex 内置技能 .system]"
echo "  说明：Codex 会随版本自动管理这些技能，本机已自带则跳过，避免覆盖新版本。"
SYSTEM_MARKER="$DEST_DIR/.system/.codex-system-skills.marker"
for skill_dir in "$SRC_DIR/.system"/*/; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"
  dest="$DEST_DIR/.system/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    echo "  跳过    $name（本机 Codex 已自带）"
    skipped=$((skipped + 1))
    continue
  fi
  mkdir -p "$DEST_DIR/.system"
  link_one "${skill_dir%/}" "$dest" "$name"
done
if [ ! -e "$SYSTEM_MARKER" ]; then
  echo "  提示：本机尚未生成 $SYSTEM_MARKER，Codex 首次启动时会自行创建，无需手动处理。"
fi

echo
echo "完成：新建 $linked 个，跳过 $skipped 个，失败 $failed 个。"
if [ "$skipped" -gt 0 ]; then
  echo "被跳过的目标保持原样，如需改用本仓库版本，请先自行备份并移除原目录。"
fi
exit 0
