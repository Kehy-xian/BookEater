from .launch_guard import run_guarded
from .pet_window_v12 import run_pet_v12

raise SystemExit(run_guarded(run_pet_v12))
