from .launch_guard import run_guarded
from .pet_window_v11 import run_pet_v11

raise SystemExit(run_guarded(run_pet_v11))
