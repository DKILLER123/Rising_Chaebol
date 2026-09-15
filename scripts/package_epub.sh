#!/bin/bash
# Package the Peninsula EPUB — mimetype must be FIRST entry, stored uncompressed.
# Working dir: /home/z/my-project/epub  →  Output: public/Peninsula_Rising_Chaebol.epub
set -e
cd /home/z/my-project/epub

OUT="/home/z/my-project/public/Peninsula_Rising_Chaebol.epub"
rm -f "$OUT"

CREATED=0
if [ ! -f mimetype ]; then
  echo -n "application/epub+zip" > mimetype
  CREATED=1
fi
zip -q -X -0 "$OUT" mimetype
zip -q -X -r "$OUT" META-INF OEBPS -x "*.DS_Store"
[ "$CREATED" = "1" ] && rm -f mimetype

echo "=== packaged: $OUT ==="
ls -la "$OUT"
echo "=== entry count ==="
unzip -l "$OUT" | tail -1
echo "=== mimetype check (must be first, stored) ==="
unzip -lv "$OUT" | sed -n '4,6p'
