#!/bin/sh
# Build the libraries the macOS build uses, as universal (arm64 and x86_64)
# binaries for macOS 11 and later: SDL2 as a shared library that ships inside
# RAVAGE.app, and libpng and FreeType as static libraries. zlib and bzip2 come
# with macOS.
#
#   tools/build-macos-deps.sh [prefix]     (default: deps/macos)
#
# Then configure with CMAKE_PREFIX_PATH=<prefix>, see the release workflow.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
prefix=$(mkdir -p "${1:-$root/deps/macos}" && cd "${1:-$root/deps/macos}" && pwd)
work="$prefix/src"
mkdir -p "$work"

fetch() { # url sha256 file
	if [ ! -f "$work/$3" ]; then
		curl -fsSL -o "$work/$3.part" "$1"
		mv "$work/$3.part" "$work/$3"
	fi
	echo "$2  $work/$3" | shasum -a 256 -c --quiet
}

build() { # source-dir extra-cmake-args...
	src=$1
	shift
	cmake -S "$src" -B "$src/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_OSX_ARCHITECTURES="arm64;x86_64" -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
		-DCMAKE_INSTALL_PREFIX="$prefix" -DCMAKE_PREFIX_PATH="$prefix" \
		-DCMAKE_IGNORE_PREFIX_PATH="/opt/homebrew;/usr/local" "$@" > "$src/configure.log" 2>&1 ||
		{ cat "$src/configure.log"; exit 1; }
	cmake --build "$src/build" --target install > "$src/build.log" 2>&1 ||
		{ tail -50 "$src/build.log"; exit 1; }
}

fetch https://github.com/libsdl-org/SDL/releases/download/release-2.30.11/SDL2-2.30.11.tar.gz \
	8b8d4aef2038533da814965220f88f77d60dfa0f32685f80ead65e501337da7f SDL2-2.30.11.tar.gz
fetch https://download.sourceforge.net/libpng/libpng-1.6.45.tar.xz \
	926485350139ffb51ef69760db35f78846c805fef3d59bfdcb2fba704663f370 libpng-1.6.45.tar.xz
fetch https://download.sourceforge.net/freetype/freetype-2.13.3.tar.xz \
	0550350666d427c74daeb85d5ac7bb353acba5f76956395995311a9c6f063289 freetype-2.13.3.tar.xz

cd "$work"
tar -xzf SDL2-2.30.11.tar.gz
tar -xJf libpng-1.6.45.tar.xz
tar -xJf freetype-2.13.3.tar.xz

echo "Building SDL2"
build SDL2-2.30.11 -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TEST=OFF

echo "Building libpng"
build libpng-1.6.45 -DPNG_SHARED=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF -DPNG_FRAMEWORK=OFF \
	-DPNG_HARDWARE_OPTIMIZATIONS=OFF

echo "Building FreeType"
build freetype-2.13.3 -DBUILD_SHARED_LIBS=OFF -DFT_DISABLE_BZIP2=ON -DFT_DISABLE_HARFBUZZ=ON \
	-DFT_DISABLE_BROTLI=ON -DFT_DISABLE_PNG=ON -DFT_DISABLE_ZLIB=ON

echo "Dependencies installed in $prefix"
