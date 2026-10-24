#!/bin/sh
# Download the pinned ericw-tools release (qbsp, vis, light) for this OS and
# check its sha256.
#
#   tools/fetch-ericw-tools.sh [dest]     (default: deps/ericw-tools)
#
# The programs end up in <dest>/bin. ericw-tools is GPLv3; it runs as a
# separate program and is never linked into RAVAGE.
set -eu

version=v0.18.1
case $(uname -s) in
Linux)
	pkg=Linux
	sha=986531ff66d692fa732b7f75a6c871dcbd152b98721d1c2475b76d3367f040e2 ;;
MINGW*|MSYS*|CYGWIN*)
	pkg=win64
	sha=a0f39c6faeb29cd08b267880cdcebb310f9938fef4cbbff07d1f6843c36e9cd3 ;;
*)
	echo "No prebuilt ericw-tools $version for $(uname -s); build it from https://github.com/ericwa/ericw-tools" >&2
	exit 1 ;;
esac

root=$(cd "$(dirname "$0")/.." && pwd)
dest=${1:-$root/deps/ericw-tools}
name=ericw-tools-$version-$pkg
zip=$dest/$name.zip

mkdir -p "$dest"
if [ -x "$dest/bin/qbsp" ] || [ -x "$dest/bin/qbsp.exe" ]; then
	if [ "$(cat "$dest/version" 2>/dev/null)" = "$name" ]; then
		echo "ericw-tools $version already in $dest/bin"
		exit 0
	fi
fi

curl -fsSL -o "$zip.part" "https://github.com/ericwa/ericw-tools/releases/download/$version/$name.zip"
mv "$zip.part" "$zip"
echo "$sha  $zip" | sha256sum -c --quiet

rm -rf "$dest/bin" "$dest/doc" "$dest/$name"
if command -v unzip > /dev/null; then
	unzip -q -o "$zip" -d "$dest"
else
	# Git Bash on Windows may not have unzip; Python can extract zips too.
	py=$(command -v python3 || command -v python)
	"$py" -m zipfile -e "$zip" "$dest"
	chmod +x "$dest/$name/bin/"*
fi
mv "$dest/$name/bin" "$dest/$name/doc" "$dest/"
rmdir "$dest/$name"
rm -f "$zip"
echo "$name" > "$dest/version"
echo "ericw-tools $version installed in $dest/bin"
