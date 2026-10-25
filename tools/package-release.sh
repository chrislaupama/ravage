#!/bin/sh
# Assemble a standalone RAVAGE release package: the client, the dedicated
# server, the game data, and every license and credit file the contents need.
#
#   tools/package-release.sh <platform> <version> <bin-dir> <game-dir> <out-dir> [deps-dir]
#
#   platform   linux-x86_64, windows-x86_64 or macos-universal
#   version    goes into the package name, for example v0.1.0
#   bin-dir    folder holding ravage and ravage-sv (.exe on Windows)
#   game-dir   folder holding base/ (from the game-data build target)
#   out-dir    where the package folder and archive are written
#   deps-dir   prefix from tools/build-win64-deps.sh or build-macos-deps.sh,
#              whose src/ folder has the bundled libraries' license files
#
# macOS signing, from the environment (all optional):
#   MACOS_SIGN_IDENTITY   a Developer ID Application identity in the keychain;
#                         without it the app gets an ad-hoc signature
#   MACOS_NOTARY_KEY, MACOS_NOTARY_KEY_ID, MACOS_NOTARY_ISSUER
#                         an App Store Connect API key (.p8 file), its key ID
#                         and issuer ID; with them the signed app is notarized
#                         and the ticket stapled to it
#
# Writes <out-dir>/ravage-<version>-<platform>/ and next to it a .tar.gz
# (Linux) or .zip (Windows, macOS). macOS packages must be built on macOS.
set -eu

[ $# -ge 5 ] || { sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
platform=$1
version=$2
bin=$(cd "$3" && pwd)
game=$(cd "$4" && pwd)
out=$(mkdir -p "$5" && cd "$5" && pwd)
deps=${6:+$(cd "$6" && pwd)}
root=$(cd "$(dirname "$0")/.." && pwd)

name=ravage-$version-$platform
pkg=$out/$name
rm -rf "$pkg" "$pkg.tar.gz" "$pkg.zip"
mkdir -p "$pkg/licenses"

[ -f "$game/base/qwprogs.dat" ] || { echo "no game data in $game/base; build the game-data target" >&2; exit 1; }

# Programs and game data. The engine looks for base/ in the working
# directory first and then next to its executable (or, in a macOS app, in
# Contents/Resources), so the package runs from anywhere.
case $platform in
linux-*)
	cp "$bin/ravage" "$bin/ravage-sv" "$pkg/"
	strip "$pkg/ravage" "$pkg/ravage-sv"
	data=$pkg
	;;
windows-*)
	cp "$bin/ravage.exe" "$bin/ravage-sv.exe" "$pkg/"
	x86_64-w64-mingw32-strip "$pkg/ravage.exe" "$pkg/ravage-sv.exe"
	data=$pkg
	;;
macos-*)
	app=$pkg/RAVAGE.app/Contents
	mkdir -p "$app/MacOS" "$app/Frameworks" "$app/Resources"
	cp "$bin/ravage" "$bin/ravage-sv" "$app/MacOS/"
	strip -x "$app/MacOS/ravage" "$app/MacOS/ravage-sv"
	# SDL2 and epoll-shim ship inside the app; point the programs at them
	# instead of the build tree.
	cp "$deps/lib/libSDL2-2.0.0.dylib" "$bin/../_deps/epoll-shim-build/src/libepoll-shim.0.dylib" "$app/Frameworks/"
	for exe in "$app/MacOS/ravage" "$app/MacOS/ravage-sv"; do
		# otool lists a universal binary's rpaths once per architecture.
		otool -l "$exe" | awk '$1 == "path" { print $2 }' | sort -u | while read -r rpath; do
			install_name_tool -delete_rpath "$rpath" "$exe"
		done
		install_name_tool -add_rpath @executable_path/../Frameworks "$exe"
	done
	sed -e "s/@VERSION@/${version#v}/g" "$root/tools/release/Info.plist" > "$app/Info.plist"
	ln -s RAVAGE.app/Contents/MacOS/ravage-sv "$pkg/ravage-sv"
	data=$app/Resources
	;;
*)
	echo "unknown platform $platform" >&2
	exit 2
	;;
esac
cp -R "$game/base" "$data/"
# Server keys and match records the engine may have written during tests.
rm -f "$data/base/"*.pem
rm -rf "$data/base/data"

notarized=false
if [ "${platform%%-*}" = macos ]; then
	# Sign once the bundle is complete, libraries and helper first. Without a
	# Developer ID it's an ad-hoc signature, which Apple silicon needs to run
	# the code at all, but Gatekeeper then asks on first launch.
	if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
		sign() { codesign --force --timestamp --options runtime --sign "$MACOS_SIGN_IDENTITY" "$@"; }
	else
		sign() { codesign --force --sign - "$@"; }
	fi
	sign "$app/Frameworks/"*.dylib "$app/MacOS/ravage-sv"
	sign "$pkg/RAVAGE.app"
	if [ -n "${MACOS_SIGN_IDENTITY:-}" ] && [ -n "${MACOS_NOTARY_KEY:-}" ]; then
		ditto -c -k --keepParent "$pkg/RAVAGE.app" "$out/notarize.zip"
		xcrun notarytool submit "$out/notarize.zip" --wait --timeout 30m \
			--key "$MACOS_NOTARY_KEY" --key-id "$MACOS_NOTARY_KEY_ID" --issuer "$MACOS_NOTARY_ISSUER" \
			--output-format json > "$out/notarize.json" || true
		rm -f "$out/notarize.zip"
		if ! grep -q '"status" *: *"Accepted"' "$out/notarize.json"; then
			cat "$out/notarize.json" >&2
			id=$(sed -n 's/.*"id" *: *"\([^"]*\)".*/\1/p' "$out/notarize.json")
			[ -z "$id" ] || xcrun notarytool log "$id" --key "$MACOS_NOTARY_KEY" \
				--key-id "$MACOS_NOTARY_KEY_ID" --issuer "$MACOS_NOTARY_ISSUER" >&2 || true
			echo "notarization failed" >&2
			exit 1
		fi
		rm -f "$out/notarize.json"
		xcrun stapler staple "$pkg/RAVAGE.app"
		notarized=true
	fi
fi

# Licenses. The engine is GPL; the source for this exact build is the
# release's tag on GitHub.
cp "$root/LICENSE" "$pkg/LICENSE.txt"
cp "$root/content/models/LICENSE.librequake" "$pkg/licenses/LibreQuake-LICENSE.txt"
cp "$root/content/models/CREDITS.librequake" "$pkg/licenses/LibreQuake-CREDITS.txt"
third_party=""
add_license() { # label source-file dest-name
	if [ -f "$2" ]; then
		cp "$2" "$pkg/licenses/$3"
		third_party="$third_party
- $1: licenses/$3"
	else
		echo "missing license file for $1: $2" >&2
		exit 1
	fi
}
case $platform in
windows-*)
	add_license "zlib" "$deps/src/zlib-1.3.1/LICENSE" zlib-LICENSE.txt
	add_license "libpng" "$deps/src/libpng-1.6.45/LICENSE" libpng-LICENSE.txt
	add_license "FreeType (used under the FreeType License)" "$deps/src/freetype-2.13.3/docs/FTL.TXT" FreeType-FTL.txt
	;;
macos-*)
	add_license "SDL2" "$deps/src/SDL2-2.30.11/LICENSE.txt" SDL2-LICENSE.txt
	add_license "libpng" "$deps/src/libpng-1.6.45/LICENSE" libpng-LICENSE.txt
	add_license "FreeType (used under the FreeType License)" "$deps/src/freetype-2.13.3/docs/FTL.TXT" FreeType-FTL.txt
	add_license "epoll-shim" "$bin/../_deps/epoll-shim-src/LICENSE" epoll-shim-LICENSE.txt
	;;
esac
[ -n "$third_party" ] || third_party="
- None. The Linux programs use the system's own libraries."

case $platform in
linux-*) run="Run ./ravage to play, or ./ravage-sv +map duel_graybox to host a dedicated server.
The programs need glibc 2.35 or later (Ubuntu 22.04, Debian 12, Fedora 36,
SteamOS 3 or newer), SDL2 and OpenGL." ;;
windows-*) run="Run ravage.exe to play, or ravage-sv.exe +map duel_graybox to host a dedicated
server. Windows 10 or later, 64-bit. Windows may warn that the programs are
from an unknown publisher; choose More info, then Run anyway." ;;
macos-*) run="Open RAVAGE.app to play, or run ./ravage-sv +map duel_graybox in Terminal to host
a dedicated server. macOS 11 or later, Apple silicon or Intel."
	$notarized || run="$run

This build is not notarized by Apple, so macOS blocks it the first time.
Open it once, then go to System Settings > Privacy & Security and choose
Open Anyway. Or, in Terminal: xattr -dr com.apple.quarantine RAVAGE.app" ;;
esac

cat > "$pkg/README.txt" <<EOF
RAVAGE $version ($platform)
Fast. Brutal. Relentless.

RAVAGE is a standalone, multiplayer arena FPS. This build is pre-production:
one graybox Duel arena, duel_graybox.

$run

Everything needed to play is in this package. It contains no Quake game
assets and does not need Quake installed.

Licenses and credits
--------------------
RAVAGE ENGINE is built from FTEQW and is licensed under the GNU General
Public License, version 2 or later (LICENSE.txt). Its source code, for this
exact build, is at https://github.com/chrislaupama/ravage/tree/$version

The player, weapon, pickup and projectile models, their skins, and most
sounds come from LibreQuake (https://github.com/lavenderdotpet/librequake),
Copyright (c) 2019-2023 Contributors to the LibreQuake project, under the
BSD 3-clause license: licenses/LibreQuake-LICENSE.txt, with its contributors
in licenses/LibreQuake-CREDITS.txt. Some were converted or recoloured for
RAVAGE.

The announcer was generated for RAVAGE with ElevenLabs text to speech. The
maps, textures, palette and remaining sounds are original to RAVAGE.

Libraries included in this package:$third_party
EOF
if [ "${platform%%-*}" = windows ]; then
	# Notepad before Windows 10 1809 wants CRLF.
	sed -i 's/$/\r/' "$pkg/README.txt"
fi

cd "$out"
case $platform in
linux-*) tar -czf "$name.tar.gz" "$name" ;;
windows-*) zip -qr9 "$name.zip" "$name" ;;
macos-*) ditto -c -k --keepParent "$name" "$name.zip" ;;
esac
echo "packaged $(ls "$out/$name".*)"
