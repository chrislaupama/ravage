# RAVAGE top-level build.
#
# Builds the RAVAGE client, dedicated server and QuakeC compiler from the
# FTEQW engine in engine/fteqw, using RAVAGE's own build config.
#
#   cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --target ravage-all
#   cmake --build build --target game-data    (game code and maps)

cmake_minimum_required(VERSION 3.16)
project(RAVAGE C CXX)

# Feature set and branding for the engine.
set(FTE_BUILD_CONFIG "${CMAKE_CURRENT_SOURCE_DIR}/engine/config_ravage.h"
	CACHE FILEPATH "Engine build config")

# Stamp builds with this repository's revision rather than FTEQW's.
execute_process(
	COMMAND git rev-parse --short HEAD
	WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
	OUTPUT_VARIABLE RAVAGE_GIT_REVISION
	OUTPUT_STRIP_TRAILING_WHITESPACE
	ERROR_QUIET)
if(NOT RAVAGE_GIT_REVISION)
	set(RAVAGE_GIT_REVISION "unknown")
endif()
set(FTE_REVISON "SVNREVISION=git-${RAVAGE_GIT_REVISION}" CACHE STRING "Engine revision string")

# Only the engine, the server and the QuakeC compiler are needed. Plugins and
# other upstream tools stay off unless RAVAGE starts using them.
foreach(opt
		FTE_PLUG_QUAKE3 FTE_PLUG_COD FTE_PLUG_BULLET FTE_PLUG_ODE FTE_PLUG_QI
		FTE_PLUG_EZHUD FTE_PLUG_IRC FTE_PLUG_HL2 FTE_PLUG_MODELS FTE_PLUG_FFMPEG
		FTE_PLUG_OPENXR FTE_PLUG_CEF FTE_PLUG_XMPP
		FTE_TOOL_IQM FTE_TOOL_IMAGE FTE_TOOL_QTV FTE_TOOL_MASTER FTE_TOOL_HTTPSV
		FTE_TOOL_QCCGUI FTE_MENU_SYS FTE_CSADDON)
	set(${opt} false CACHE BOOL "Disabled by RAVAGE")
endforeach()

# Builds must run on any x86-64 machine, not just the one that compiled them.
set(FTE_MARCH_NATIVE false CACHE BOOL "Optimise for the build machine's CPU")

add_subdirectory(engine/fteqw)

set_target_properties(fteqw PROPERTIES
	OUTPUT_NAME ravage
	RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set_target_properties(fteqw-sv PROPERTIES
	OUTPUT_NAME ravage-sv
	RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set_target_properties(fteqcc PROPERTIES
	RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

add_custom_target(ravage-all DEPENDS fteqw fteqw-sv fteqcc)

# Game data (server game code and compiled maps) in build/game/base. Needs
# ericw-tools, see tools/fetch-ericw-tools.sh.
add_custom_target(game-data
	COMMAND ${CMAKE_COMMAND} -E env "FTEQCC=$<TARGET_FILE:fteqcc>"
		"${CMAKE_CURRENT_SOURCE_DIR}/tools/build-game-data.sh" "${CMAKE_BINARY_DIR}/game/base"
	DEPENDS fteqcc
	USES_TERMINAL)

enable_testing()
add_test(NAME smoke
	COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/tests/smoke.sh" "${CMAKE_BINARY_DIR}/bin")
add_test(NAME map_pipeline
	COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/tests/map_pipeline.sh" "${CMAKE_BINARY_DIR}/bin")
set_tests_properties(map_pipeline PROPERTIES SKIP_RETURN_CODE 77)
