#!/bin/sh
# Rendering benchmark: load a map in the client, then render a full 360
# degree turn from the first spawn point with "timerefresh" and report the
# frame rate. Run it on a machine with a GPU; numbers from software
# rendering (for example Xvfb with llvmpipe) only show that it works.
#
#   tools/bench-map.sh [map] [frames] [width] [height]
#
# Defaults: duel_graybox, 1000 frames, 1920x1080. Expects the client in
# build/bin and game data from tools/build-game-data.sh in build/game.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
map=${1:-duel_graybox}
frames=${2:-1000}
width=${3:-1920}
height=${4:-1080}
game=${RAVAGE_GAME_DIR:-$root/build/game}
client=${RAVAGE_CLIENT:-$root/build/bin/ravage}

cfg=$game/base/bench.cfg
trap 'rm -f "$cfg"' EXIT
{
	# Give the renderer and the local server time to start before loading.
	i=0; while [ $i -lt 30 ]; do echo wait; i=$((i + 1)); done
	echo "map $map"
	i=0; while [ $i -lt 120 ]; do echo wait; i=$((i + 1)); done
	echo "timerefresh 1 $frames"
	echo "timerefresh 1 $frames"
	echo "timerefresh 1 $frames"
	echo quit
} > "$cfg"

"$client" -basedir "$game" -nohome +set vid_fullscreen 0 +set vid_width "$width" \
	+set vid_height "$height" +set vid_vsync 0 +set s_device none \
	+set sys_colorconsole 0 +set crosshair 0 +exec bench.cfg 2>&1 </dev/null |
	grep -E "GL_RENDERER|seconds \(" | sed "s/^/$map ${width}x$height: /"
