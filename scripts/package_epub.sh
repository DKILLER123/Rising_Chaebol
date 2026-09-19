#!/usr/bin/env bash
# Package the Peninsula EPUB. The root mimetype entry is stored and comes first.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
TREE="$ROOT/epub"
OUT="$ROOT/public/Peninsula_Rising_Chaebol.epub"

cd "$TREE"
if [[ ! -f mimetype ]]; then
  printf 'application/epub+zip' > mimetype
  CREATED=1
else
  CREATED=0
fi
rm -f "$OUT"
zip -q -X -0 "$OUT" mimetype
zip -q -X -r "$OUT" META-INF OEBPS -x '*.DS_Store'
[[ "$CREATED" == 1 ]] && rm -f mimetype

printf '=== packaged: %s ===\n' "$OUT"
stat -c '%n %s bytes' "$OUT"
printf '%s\n' '=== entry count ==='
unzip -l "$OUT" | tail -1
printf '%s\n' '=== mimetype check (must be first, stored) ==='
unzip -lv "$OUT" | sed -n '4,6p'
