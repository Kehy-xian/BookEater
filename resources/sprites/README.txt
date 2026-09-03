BookEater production sprite directory

Transparent PNG frames go here using the stable naming contract:
<asset_slug>_<state>_<frame>.png

Every frame must be exactly 190x190, 8-bit RGBA PNG. Keep unused canvas pixels transparent and
keep every frame on the same canvas/baseline so the character does not jump between poses.

Examples:
paperling_idle_00.png
pagedge_walk_02.png
inknest_eat_05.png
lantern_sleep_01.png

A form/state is loaded only when every required frame exists. Missing or corrupt sets fall back
to the vector renderer so updates cannot make the desktop pet disappear.

- IDLE: 4 frames, 420 ms each
- EAT: 6 frames, 115 ms each
- WALK: 4 frames, 130 ms each
- READ: 3 frames, 220 ms each
- SLEEP: 3 frames, 420 ms each
- TALK: 2 frames, 180 ms each
- SPIT_MEMORY: 4 frames, 145 ms each
- SNACK: 6 frames, 120 ms each
- DELICIOUS: 3 frames, 260 ms each
- PLAY: 4 frames, 150 ms each
- WASH: 4 frames, 190 ms each
- BUMP: 3 frames, 130 ms each
- DROP: 2 frames, 120 ms each

IDLE is a slow four-frame breathing cycle. Keep the feet and optional shadow fixed near the shared
baseline; move or gently squash only the torso in a 0, -1, -3, -1 px rhythm.

The seven original states are generated for release builds. The six added action states are
optional: a complete local override replaces the fallback motion, while an incomplete set is
ignored safely.
