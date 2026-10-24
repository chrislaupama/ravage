#!/bin/sh
# Smoke test: the client and dedicated server start, report the RAVAGE build
# config, and shut down cleanly without any game data.
#
#   tests/smoke.sh <bin-dir>
set -eu

bin=${1:?usage: smoke.sh <bin-dir>}
base=$(mktemp -d)
trap 'rm -rf "$base"' EXIT
mkdir -p "$base/base"

windows=false
case $(uname -s) in
MINGW*|MSYS*|CYGWIN*) windows=true ;;
esac
basedir=$base
if $windows; then
	# Windows programs need a Windows path, not an MSYS one.
	basedir=$(cygpath -m "$base")
fi

fail=0
check() {
	name=$1
	shift
	status=0
	out=$("$@" 2>&1 </dev/null) || status=$?
	if [ "$status" -ne 0 ]; then
		echo "FAIL $name: exited with status $status"
		echo "$out"
		fail=1
		return
	fi
	for want in "RAVAGE ENGINE" "config_ravage.h"; do
		if ! printf '%s\n' "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -qF "$want"; then
			echo "FAIL $name: output is missing \"$want\""
			echo "$out"
			fail=1
			return
		fi
	done
	echo "ok   $name"
}

# sys_colorconsole 0 keeps the Windows server writing plain text to stdout.
check "ravage-sv" timeout 30 "$bin/ravage-sv" -basedir "$basedir" -nohome +set sys_colorconsole 0 +version +quit
# The Windows client is a GUI program with no console output to check.
if $windows; then
	echo "skip ravage (headless): no console output on Windows"
	exit $fail
fi
check "ravage (headless)" timeout 30 "$bin/ravage" -basedir "$basedir" -nohome \
	+set vid_renderer headless +set s_device none +version +quit

exit $fail
