#!/bin/sh
# Placeholder asset test: the committed models, skins and sounds match what
# tools/assets/ generates (so nobody edits a generated file by hand or
# forgets to regenerate), and every model or sound the game code names
# exists in content/.
#
#   tests/assets.sh
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
python=$(command -v python3 || command -v python)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
fail=0

"$python" "$root/tools/assets/make_models.py" "$work" > /dev/null
"$python" "$root/tools/assets/make_sounds.py" "$work" > /dev/null
for dir in models sound; do
	if ! diff -r "$root/content/$dir" "$work/$dir" > /dev/null; then
		echo "FAIL content/$dir differs from what tools/assets/ generates; rerun the generators"
		diff -rq "$root/content/$dir" "$work/$dir" || true
		fail=1
	fi
done

# Model paths are relative to the game folder, sound paths to its sound/.
for path in $(grep -ohE '"models/[a-z0-9_]+\.iqm"' "$root"/game/*/*.qc | tr -d '"' | sort -u); do
	[ -f "$root/content/$path" ] || { echo "FAIL missing $path"; fail=1; }
done
for path in $(grep -ohE '"[a-z]+/[a-z0-9_]+\.wav"' "$root"/game/*/*.qc | tr -d '"' | sort -u); do
	[ -f "$root/content/sound/$path" ] || { echo "FAIL missing sound/$path"; fail=1; }
done

[ "$fail" -eq 0 ] && echo "assets: PASS"
exit $fail
