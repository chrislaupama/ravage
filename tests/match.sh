#!/bin/sh
# Two-client match test: compile the game data, start a headless dedicated
# server on duel_graybox, connect two real headless clients ("runner" holds
# forward, "target" stands still), and let the game code's match test check
# ready-up, spawns, collision, pickups, combat, respawn, overtime and the
# match statistics (game/ssqc/matchtest.qc). The target's client prints
# the stats its HUD shows. A third client, "watcher", joins the full
# server as a spectator. Last, the server's recording of the match must
# play back to its end.
#
#   tests/match.sh <bin-dir>
#
# Needs ericw-tools like map_pipeline.sh; exits 77 (skipped) without them,
# except on CI. Linux only for now: the Windows client has no headless
# console output.
set -eu

bin=${1:?usage: match.sh <bin-dir>}
root=$(cd "$(dirname "$0")/.." && pwd)
tools=${ERICW_TOOLS:-$root/deps/ericw-tools/bin}
if [ ! -x "$tools/qbsp" ]; then
	echo "SKIP: ericw-tools not found in $tools (run tools/fetch-ericw-tools.sh)"
	[ -z "${CI:-}" ] || exit 1
	exit 77
fi

base=$(mktemp -d)
pids=
cleanup() {
	# The clients run until this script ends. They ignore SIGTERM, so stop
	# them with SIGKILL.
	for pid in $pids; do kill -KILL "$pid" 2>/dev/null || true; done
	rm -rf "$base"
}
trap cleanup EXIT

FTEQCC="$bin/fteqcc" ERICW_TOOLS="$tools" "$root/tools/build-game-data.sh" "$base/base" > /dev/null

# A port per run, so parallel test runs don't collide.
port=$((27700 + $$ % 200))

timeout 90 "$bin/ravage-sv" -basedir "$base" -nohome +set sys_colorconsole 0 \
	+set sv_port "$port" +set rv_matchtest 1 +set timelimit 0 +set fraglimit 0 \
	+map duel_graybox > "$base/server.log" 2>&1 &
server=$!

client() { # name extra-commands...
	name=$1
	shift
	"$bin/ravage" -basedir "$base" -nohome +set vid_renderer headless \
		+set s_device none +set sys_colorconsole 0 +set name "$name" \
		+connect "127.0.0.1:$port" "$@" > "$base/$name.log" 2>&1 </dev/null &
	pids="$pids $!"
}
# "+forward" on the command line is not a command, so exec it from a cfg.
echo "+forward" > "$base/base/runner.cfg"
sleep 1
client target
client runner +exec runner.cfg
# Both player slots are taken, so this one spectates.
sleep 2
client watcher

status=0
wait "$server" || status=$?

fail=0
results=$(grep "RAVAGE matchtest:" "$base/server.log" || true)
printf '%s\n' "$results"
if [ "$status" -ne 0 ]; then
	echo "FAIL server exited with status $status"
	fail=1
fi
if ! printf '%s\n' "$results" | grep -q "RAVAGE matchtest: PASS"; then
	echo "FAIL match test did not pass"
	fail=1
fi
# The client HUD reads stats the server sends; after respawning, the target
# has full health, no armor and the machine gun with 100 bullets.
hud=$(grep -a "RAVAGE hudtest:" "$base/target.log" || true)
printf '%s\n' "${hud:-RAVAGE hudtest: no output}"
if [ "$hud" != "RAVAGE hudtest: health=100 armor=0 weapon=2 ammo=100" ]; then
	echo "FAIL client HUD stats are wrong"
	fail=1
fi
if ! grep -q "watcher is spectating" "$base/server.log"; then
	echo "FAIL the third client did not join as a spectator"
	fail=1
fi

# The server recorded the match and saved its statistics under the same
# name. The runner's one railgun shot hit.
demo=$(cd "$base/base" && ls demos/*.mvd 2>/dev/null | head -1)
stats=$(ls "$base"/base/data/matches/*.json 2>/dev/null | head -1)
if [ -z "$demo" ] || [ ! -s "$base/base/$demo" ]; then
	echo "FAIL the match was not recorded"
	fail=1
elif [ "$(basename "$demo" .mvd)" != "$(basename "${stats:-none}" .json)" ]; then
	echo "FAIL no statistics file for $demo"
	fail=1
elif ! grep -q '"Railgun": { "shots": 1, "hits": 1 }' "$stats"; then
	echo "FAIL the statistics file is wrong:"
	cat "$stats"
	fail=1
else
	echo "recorded $demo with statistics"
	# Play it back: the client must reach the end of the match, with the
	# statistics, and timedemo prints the frame rate when it finishes.
	timeout 60 "$bin/ravage" -basedir "$base" -nohome +set vid_renderer headless \
		+set s_device none +set sys_colorconsole 0 +timedemo "$demo" > "$base/playback.log" 2>&1 </dev/null &
	player=$!
	pids="$pids $player"
	for i in $(seq 60); do
		grep -aq "frames .* seconds" "$base/playback.log" && break
		sleep 1
	done
	grep -a "frames .* seconds" "$base/playback.log" || true
	if ! grep -aq "Match statistics received for 2 players" "$base/playback.log"; then
		echo "FAIL the demo did not play back to the end of the match"
		tail -20 "$base/playback.log"
		fail=1
	fi
fi
if [ "$fail" -ne 0 ]; then
	echo "--- server log"
	cat "$base/server.log"
	for name in target runner watcher; do
		echo "--- $name log"
		tail -20 "$base/$name.log"
	done
fi
exit $fail
