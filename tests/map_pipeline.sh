#!/bin/sh
# Map pipeline test: compile the game code and every map in content/maps as
# BSP2, then load each map on the dedicated server and run its self-test
# (spawn points have room and a floor, pickups rest on a floor).
#
#   tests/map_pipeline.sh <bin-dir>
#
# Needs ericw-tools (tools/fetch-ericw-tools.sh, or ERICW_TOOLS). Exits 77,
# which CTest reports as skipped, when they are missing, except on CI where
# missing tools are a failure.
set -eu

bin=${1:?usage: map_pipeline.sh <bin-dir>}
root=$(cd "$(dirname "$0")/.." && pwd)

# Every entity TrenchBroom can place must have a spawn function in the game
# code. func_detail and func_group are merged into the world by qbsp.
fail=0
classes=$(sed -n 's/^@\(Point\|Solid\)Class.*= *\([a-z_0-9]*\) *:.*/\2/p' \
	"$root/tools/trenchbroom/RAVAGE/ravage.fgd")
for class in $classes; do
	case $class in func_detail|func_group) continue ;; esac
	if ! grep -q "^void() $class =" "$root"/game/ssqc/*.qc; then
		echo "FAIL ravage.fgd: $class has no spawn function in game/ssqc"
		fail=1
	fi
done
[ "$fail" -eq 0 ] || exit 1
echo "ok   ravage.fgd: $(echo "$classes" | wc -l) entity classes match the game code"

tools=${ERICW_TOOLS:-$root/deps/ericw-tools/bin}
if [ ! -x "$tools/qbsp" ] && [ ! -x "$tools/qbsp.exe" ]; then
	echo "SKIP: ericw-tools not found in $tools (run tools/fetch-ericw-tools.sh)"
	[ -z "${CI:-}" ] || exit 1
	exit 77
fi

base=$(mktemp -d)
trap 'rm -rf "$base"' EXIT
basedir=$base
case $(uname -s) in
MINGW*|MSYS*|CYGWIN*) basedir=$(cygpath -m "$base") ;;
esac

FTEQCC="$bin/fteqcc" ERICW_TOOLS="$tools" "$root/tools/build-game-data.sh" "$base/base"

for bsp in "$base"/base/maps/*.bsp; do
	name=$(basename "$bsp" .bsp)

	magic=$(head -c 4 "$bsp")
	if [ "$magic" != "BSP2" ]; then
		echo "FAIL $name: expected a BSP2 file, header is '$magic'"
		fail=1
		continue
	fi

	status=0
	out=$(timeout 60 "$bin/ravage-sv" -basedir "$basedir" -nohome \
		+set sys_colorconsole 0 +set rv_selftest 1 +map "$name" 2>&1 </dev/null) || status=$?
	summary=$(printf '%s\n' "$out" | grep "RAVAGE selftest: map=" || true)
	if [ "$status" -ne 0 ]; then
		echo "FAIL $name: server exited with status $status"
		fail=1
	elif ! printf '%s\n' "$out" | grep -q "RAVAGE selftest: PASS"; then
		echo "FAIL $name: self-test did not pass"
		fail=1
	elif printf '%s\n' "$out" | grep -q "Couldn't find spawn function"; then
		echo "FAIL $name: map uses entities the game code doesn't know"
		fail=1
	else
		echo "ok   $name: ${summary#RAVAGE selftest: }"
		continue
	fi
	printf '%s\n' "$out"
done
exit $fail
