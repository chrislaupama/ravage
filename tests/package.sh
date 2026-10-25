#!/bin/sh
# Release package test: a package from tools/package-release.sh carries its
# license and credit files and no Quake assets, and its programs find the
# package's game data when started from some other working directory.
#
#   tests/package.sh <package-dir>
#   tests/package.sh --linux <bin-dir>
#
# With --linux (as under ctest) it first compiles the game data and packages
# it with the programs in bin-dir. That needs ericw-tools like match.sh, and
# exits 77 (skipped) without them, except on CI.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

if [ "${1:-}" = --linux ]; then
	bin=${2:?usage: package.sh --linux <bin-dir>}
	tools=${ERICW_TOOLS:-$root/deps/ericw-tools/bin}
	if [ ! -x "$tools/qbsp" ]; then
		echo "SKIP: ericw-tools not found in $tools (run tools/fetch-ericw-tools.sh)"
		[ -z "${CI:-}" ] || exit 1
		exit 77
	fi
	FTEQCC="$bin/fteqcc" ERICW_TOOLS="$tools" "$root/tools/build-game-data.sh" "$scratch/game/base" > /dev/null
	"$root/tools/package-release.sh" linux-x86_64 test "$bin" "$scratch/game" "$scratch/out" > /dev/null
	pkg=$scratch/out/ravage-test-linux-x86_64
else
	pkg=${1:?usage: package.sh <package-dir>}
fi
pkg=$(cd "$pkg" && pwd -P)

# macOS has no timeout(1).
if ! command -v timeout > /dev/null; then
	timeout() { perl -e 'alarm shift; exec @ARGV or die "$ARGV[0]: $!"' "$@"; }
fi

windows=false
case $(uname -s) in
MINGW*|MSYS*|CYGWIN*) windows=true ;;
esac

fail=0
bad() {
	echo "FAIL $*"
	fail=1
}

# Contents.
if [ -d "$pkg/RAVAGE.app" ]; then
	data=$pkg/RAVAGE.app/Contents/Resources
	server=$pkg/ravage-sv
	client=$pkg/RAVAGE.app/Contents/MacOS/ravage
else
	data=$pkg
	server=$pkg/ravage-sv
	client=$pkg/ravage
	if $windows; then
		server=$server.exe
		client=$client.exe
	fi
fi
for f in README.txt LICENSE.txt licenses/LibreQuake-LICENSE.txt licenses/LibreQuake-CREDITS.txt; do
	[ -s "$pkg/$f" ] || bad "missing $f"
done
for f in qwprogs.dat csprogs.dat gfx/palette.lmp maps/duel_graybox.bsp models/player.iqm; do
	[ -s "$data/base/$f" ] || bad "missing base/$f"
done
for f in "$server" "$client"; do
	[ -x "$f" ] || bad "missing program $f"
done
quake=$(find "$pkg" -iname 'pak*.pak' -o -iname 'id1' -o -iname 'progs.dat' -o -iname '*.pem')
[ -z "$quake" ] || bad "package holds files it must not ship: $quake"
echo "ok   contents"

# Started from an empty working directory, the server must find the
# package's game data and load the arena (the game code's self-test prints
# the line checked here).
cd "$scratch"
status=0
out=$(timeout 60 "$server" -nohome +set sys_colorconsole 0 +map duel_graybox +wait +quit 2>&1 </dev/null) || status=$?
if [ "$status" -ne 0 ] || ! printf '%s\n' "$out" | grep -q 'RAVAGE selftest: map=duel_graybox .* errors=0'; then
	bad "ravage-sv did not load duel_graybox from the package (status $status)"
	printf '%s\n' "$out"
else
	echo "ok   ravage-sv loads the arena from another working directory"
fi

# The Windows client is a GUI program with no console output to check.
if ! $windows; then
	status=0
	out=$(timeout 60 "$client" -nohome +set fs_hidesyspaths 0 +set vid_renderer headless \
		+set s_device none +path +quit 2>&1 </dev/null) || status=$?
	if [ "$status" -ne 0 ] || ! printf '%s\n' "$out" | grep -qF "$data/base"; then
		bad "ravage did not use the package's game data (status $status)"
		printf '%s\n' "$out"
	else
		echo "ok   ravage uses the package's game data"
	fi
fi

exit $fail
