#!/bin/bash
set -euo pipefail
assets="$(cd "$(dirname "$0")/../assets" && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir "$work/AppIcon.iconset"
for size in 16 32 128 256 512; do
  for scale in 1 2; do
    suffix=""; if [ "$scale" = 2 ]; then suffix="@2x"; fi
    pixels=$((size * scale))
    rsvg-convert -w "$pixels" -h "$pixels" -o "$work/AppIcon.iconset/icon_${size}x${size}${suffix}.png" "$assets/icon.svg"
  done
done
rsvg-convert -o "$assets/icon.png" "$assets/icon.svg"
iconutil -c icns "$work/AppIcon.iconset" -o "$assets/AppIcon.icns"
for size in 16 32 48 128; do
  rsvg-convert -w "$size" -h "$size" -o "$assets/../../extension/icons/icon-$size.png" "$assets/icon.svg"
done
