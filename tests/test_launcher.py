import runpy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class LauncherTests(unittest.TestCase):
    def test_reentrant_game_start_keeps_outer_timer_alive(self):
        registered = []
        fake_bpy = SimpleNamespace(
            app=SimpleNamespace(
                timers=SimpleNamespace(
                    register=lambda callback, **_kwargs: registered.append(callback)
                )
            )
        )
        launcher = Path(__file__).parents[1] / "tools" / "launch_openxr_game.py"

        with patch.dict(sys.modules, {"bpy": fake_bpy}):
            globals_ = runpy.run_path(str(launcher))

        self.assertEqual(len(registered), 1)
        registered[0].__globals__["_game_start_requested"] = True
        self.assertGreater(registered[0](), 0.0)


if __name__ == "__main__":
    unittest.main()
