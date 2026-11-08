#!/bin/sh
# 冒烟自检：环境 + 一次最小成片 + 断言。
# 需要: ffmpeg/ffprobe、om 桥（OPENMONTAGE_HOME 指向 OpenMontage）。
set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)
OM=$HOME/.dsh/profiles/media/bin/om
if [ -n "$OM_BIN" ]; then OM=$OM_BIN; fi
WORK=$HOME/.cache/media-workstation-smoke/$(date +%Y%m%dT%H%M%S)
if [ -n "$SMOKE_WORK" ]; then WORK=$SMOKE_WORK; fi
P=$WORK/smoke

echo "== env =="
"$OM" doctor

mkdir -p "$P/assets" "$P/artifacts" "$P/renders" "$P/previews"

ffmpeg -hide_banner -loglevel error -y -f lavfi -i testsrc2=size=1280x720:rate=30:duration=3 \
  -f lavfi -i "sine=frequency=440:sample_rate=48000:duration=3" \
  -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac -shortest "$P/assets/a.mp4"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i smptebars=size=1280x720:rate=30:duration=3 \
  -f lavfi -i "sine=frequency=660:sample_rate=48000:duration=3" \
  -c:v libx264 -preset veryfast -pix_fmt yuv420p -c:a aac -shortest "$P/assets/b.mp4"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "sine=frequency=220:sample_rate=48000:duration=6" \
  -c:a pcm_s16le "$P/assets/music.wav"

cat > "$P/artifacts/decisions.json" <<JSON
{
  "version": "1.0",
  "render_runtime": "ffmpeg",
  "composition_mode": "cuts",
  "renderer_family": "ffmpeg",
  "cuts": [
    {"id": "c1", "source": "$P/assets/a.mp4", "in_seconds": 0.0, "out_seconds": 3.0},
    {"id": "c2", "source": "$P/assets/b.mp4", "in_seconds": 0.0, "out_seconds": 3.0}
  ],
  "metadata": {"compose_target": {"width": 1280, "height": 720, "fit": "pad"}}
}
JSON

echo
echo "== validate + compose =="
"$OM" validate "$P/artifacts/decisions.json" --runtime ffmpeg
"$OM" compose "$P/artifacts/decisions.json" --out "$P/renders/base.mp4"

echo
echo "== mix / norm / attach =="
"$OM" mix --voice "$P/renders/base.mp4" --music "$P/assets/music.wav" --out "$P/artifacts/mix.m4a"
"$OM" norm "$P/artifacts/mix.m4a" --out "$P/artifacts/norm.m4a" --lufs -14
"$OM" attach --video "$P/renders/base.mp4" --audio "$P/artifacts/norm.m4a" --out "$P/renders/final.mp4"

echo
echo "== assert =="
"$OM" probe "$P/renders/final.mp4" --loudness --expect width=1280 --expect height=720 --expect fps=30 --expect audio=yes --expect lufs=-14

echo
echo "output: $P/renders/final.mp4"