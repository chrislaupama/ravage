#!/bin/sh
# Build RAVAGE's game data folder: compile the server game code with fteqcc
# and every map in content/maps with ericw-tools (qbsp -bsp2, vis, light).
#
#   tools/build-game-data.sh [out-dir]     (default: build/game/base)
#
# Environment:
#   FTEQCC       fteqcc program (default: build/bin/fteqcc)
#   ERICW_TOOLS  folder holding qbsp, vis and light
#                (default: deps/ericw-tools/bin, see tools/fetch-ericw-tools.sh)
#
# Run the game with -basedir pointing at the folder above out-dir, for
# example: build/bin/ravage -basedir build/game +map duel_graybox
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
out=$(mkdir -p "${1:-$root/build/game/base}" && cd "${1:-$root/build/game/base}" && pwd)
fteqcc=${FTEQCC:-$root/build/bin/fteqcc}
tools=${ERICW_TOOLS:-$root/deps/ericw-tools/bin}

for tool in qbsp vis light; do
	if [ ! -x "$tools/$tool" ] && [ ! -x "$tools/$tool.exe" ]; then
		echo "$tool not found in $tools; run tools/fetch-ericw-tools.sh or set ERICW_TOOLS" >&2
		exit 1
	fi
done

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "== game code"
"$fteqcc" -src "$root/game/ssqc" -o "$out/qwprogs.dat" > "$work/qcc.log" 2>&1 || {
	cat "$work/qcc.log"
	exit 1
}
grep -i -E "warning|error" "$work/qcc.log" || true

# The engine draws the maps' 8-bit textures with this palette.
mkdir -p "$out/gfx" "$out/maps"
cp "$root/content/gfx/palette.lmp" "$out/gfx/"

for map in "$root"/content/maps/*.map; do
	name=$(basename "$map" .map)
	echo "== $name"
	cp "$map" "$work/$name.map"
	# Compile in the scratch folder so .prt, .log and other side files
	# never land in the source tree. Maps name their WAD relative to
	# content/maps, the way TrenchBroom resolves it, hence -wadpath.
	(
		cd "$work"
		"$tools/qbsp" -nopercent -bsp2 -leaktest -wadpath "$root/content/maps" "$name.map"
		"$tools/vis" "$name.bsp"
		"$tools/light" -bounce -extra4 "$name.bsp"
	) > "$work/$name.log" 2>&1 || {
		cat "$work/$name.log"
		echo "failed to compile $map" >&2
		exit 1
	}
	grep -i -E "warning|error|leak" "$work/$name.log" || true
	cp "$work/$name.bsp" "$out/maps/"
	[ ! -f "$work/$name.lit" ] || cp "$work/$name.lit" "$out/maps/"
done
echo "game data written to $out"
