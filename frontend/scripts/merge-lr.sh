#!/usr/bin/env bash
# Merge two videos side-by-side (left | right) into one 1920x1080 MP4.
#
#   scripts/merge-lr.sh LEFT.webm RIGHT.webm [OUT.mp4]
#
# This is exactly what the dual recording does automatically; kept as a
# standalone tool so you can re-merge any two clips (e.g. the raw per-pane
# webm files under test-results/dual/) without re-running the whole demo.
#
# The two inputs don't need identical length: the shorter one is padded by
# freezing its last frame (tpad) so nothing gets cut off.
set -euo pipefail

LEFT="${1:?usage: merge-lr.sh LEFT RIGHT [OUT]}"
RIGHT="${2:?usage: merge-lr.sh LEFT RIGHT [OUT]}"
OUT="${3:-dual-demo-1080.mp4}"

dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }
LD="$(dur "$LEFT")"; RD="$(dur "$RIGHT")"
MAX="$(printf '%s\n%s\n' "$LD" "$RD" | sort -rn | head -1)"

ffmpeg -y -i "$LEFT" -i "$RIGHT" -filter_complex "\
  [0:v]tpad=stop_mode=clone:stop_duration=${MAX}[l];\
  [1:v]tpad=stop_mode=clone:stop_duration=${MAX}[r];\
  [l][r]hstack=inputs=2,scale=1920:1080:flags=lanczos,format=yuv420p,trim=duration=${MAX}[v]" \
  -map "[v]" -r 30 "$OUT"

echo "✅ merged → $OUT  (left=${LD}s right=${RD}s)"
