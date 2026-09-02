BookEater production sprite directory

Transparent PNG frames go here using the stable naming contract:
<asset_slug>_<state>_<frame>.png

Examples:
paperling_idle_00.png
pagedge_walk_02.png
inknest_eat_05.png
lantern_sleep_01.png

A form/state is loaded only when every required frame exists. Missing or corrupt sets fall back
to the vector renderer so updates cannot make the desktop pet disappear.
