#!/bin/sh
# Cross-compile the static libraries the Windows build links against
# (zlib, libpng, FreeType) and fetch the Vulkan headers, using MinGW-w64.
#
#   tools/build-win64-deps.sh [prefix]     (default: deps/win64)
#
# Then configure with RAVAGE_WIN64_DEPS=<prefix> in the environment.
set -eu

root=$(cd "$(dirname "$0")/.." && pwd)
prefix=$(mkdir -p "${1:-$root/deps/win64}" && cd "${1:-$root/deps/win64}" && pwd)
work="$prefix/src"
toolchain="$root/cmake/mingw-w64-x86_64.cmake"
mkdir -p "$work"

fetch() { # url sha256 file
	if [ ! -f "$work/$3" ]; then
		curl -fsSL -o "$work/$3.part" "$1"
		mv "$work/$3.part" "$work/$3"
	fi
	echo "$2  $work/$3" | sha256sum -c --quiet
}

build() { # source-dir extra-cmake-args...
	src=$1
	shift
	cmake -S "$src" -B "$src/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
		-DCMAKE_TOOLCHAIN_FILE="$toolchain" -DCMAKE_INSTALL_PREFIX="$prefix" \
		-DCMAKE_FIND_ROOT_PATH="$prefix" -DBUILD_SHARED_LIBS=OFF "$@" > "$src/configure.log"
	cmake --build "$src/build" --target install > "$src/build.log"
}

fetch https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz \
	9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23 zlib-1.3.1.tar.gz
fetch https://download.sourceforge.net/libpng/libpng-1.6.45.tar.xz \
	926485350139ffb51ef69760db35f78846c805fef3d59bfdcb2fba704663f370 libpng-1.6.45.tar.xz
fetch https://download.sourceforge.net/freetype/freetype-2.13.3.tar.xz \
	0550350666d427c74daeb85d5ac7bb353acba5f76956395995311a9c6f063289 freetype-2.13.3.tar.xz

cd "$work"
tar -xzf zlib-1.3.1.tar.gz
tar -xJf libpng-1.6.45.tar.xz
tar -xJf freetype-2.13.3.tar.xz

echo "Building zlib"
build zlib-1.3.1 -DZLIB_BUILD_EXAMPLES=OFF
# Only the static library is wanted, so the import library can't be picked by mistake.
rm -f "$prefix/lib/libzlib.dll.a" "$prefix/bin/libzlib.dll"
cp "$prefix/lib/libzlibstatic.a" "$prefix/lib/libz.a"

echo "Building libpng"
build libpng-1.6.45 -DPNG_SHARED=OFF -DPNG_TESTS=OFF -DPNG_TOOLS=OFF \
	-DZLIB_ROOT="$prefix" -DZLIB_LIBRARY="$prefix/lib/libz.a" -DZLIB_INCLUDE_DIR="$prefix/include"

echo "Building FreeType"
build freetype-2.13.3 -DFT_DISABLE_BZIP2=ON -DFT_DISABLE_HARFBUZZ=ON \
	-DFT_DISABLE_BROTLI=ON -DFT_DISABLE_PNG=ON -DFT_DISABLE_ZLIB=ON

echo "Fetching Vulkan headers"
if [ ! -d Vulkan-Headers ]; then
	git -c advice.detachedHead=false clone -q --depth 1 --branch v1.3.275 https://github.com/KhronosGroup/Vulkan-Headers.git
fi
mkdir -p "$prefix/include"
cp -r Vulkan-Headers/include/vulkan Vulkan-Headers/include/vk_video "$prefix/include/"

echo "Dependencies installed in $prefix"
