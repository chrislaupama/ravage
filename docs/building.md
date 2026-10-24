# Building RAVAGE

RAVAGE builds with CMake. The build produces three programs in `build/bin/`:

| Program | What it is |
|---|---|
| `ravage` | Game client (OpenGL and Vulkan) |
| `ravage-sv` | Headless dedicated server |
| `fteqcc` | QuakeC compiler for the game code |

## Linux

Tested on Ubuntu 24.04.

```
sudo apt-get install cmake ninja-build gcc g++ libsdl2-dev libgl-dev libvulkan-dev \
  libxrandr-dev libxcursor-dev libjpeg-dev libvorbis-dev libgnutls28-dev libopus-dev \
  libwayland-dev libxkbcommon-dev libbz2-dev libpng-dev libfreetype-dev zlib1g-dev

cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build build --target ravage-all
ctest --test-dir build --output-on-failure
```

## Windows

Windows x64 builds are cross-compiled from Linux with MinGW-w64. The programs only need DLLs that ship with Windows.

```
sudo apt-get install cmake ninja-build gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64

tools/build-win64-deps.sh          # zlib, libpng, FreeType and Vulkan headers, into deps/win64
export RAVAGE_WIN64_DEPS=$PWD/deps/win64
cmake -S . -B build-win64 -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_TOOLCHAIN_FILE=cmake/mingw-w64-x86_64.cmake
cmake --build build-win64 --target ravage-all
```

Not yet included on Windows: Ogg Vorbis audio, JPEG and bzip2-compressed packages. Building natively with Visual Studio hasn't been tried.

## Running

There is no game content yet. The client starts to an empty console, and the server stops with "Couldn't load a map" until the first arena arrives in step 4. The programs look for game data in a `base/` folder inside the directory they're started from (the current working directory), not next to the executable. To use data somewhere else, point `-basedir` at the folder that contains `base/`:

```
build/bin/ravage-sv -basedir /path/to/data
build/bin/ravage -basedir /path/to/data
```

To use a Quake install you legally own as a local reference, see [licensing.md](licensing.md#using-your-own-quake-install-for-development).

## Continuous integration

`.github/workflows/build.yml` builds Linux and Windows on every pull request and push to `main`, runs the tests, and uploads the programs as build artifacts. The Windows server is also started on a Windows runner.
