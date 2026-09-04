import runpy
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


class LauncherTests(unittest.TestCase):
    def test_external_world_build_uses_explicit_project_root(self):
        root = Path(__file__).parents[1]
        bootstrap = (root / "arrietty_bootstrap.py").read_text(encoding="utf-8")
        launcher = (root / "tools" / "launch_live_test.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn('os.environ.get("ARRIETTY_PROJECT_ROOT"', bootstrap)
        self.assertIn("$env:ARRIETTY_PROJECT_ROOT = $ProjectRoot", launcher)

    def test_launcher_selects_rendered_xr_before_starting_the_game(self):
        root = Path(__file__).parents[1]
        registered = []
        game_settings = SimpleNamespace(use_viewport_render=False)
        xr_shading = SimpleNamespace(
            type="SOLID",
            use_scene_lights_render=False,
            use_scene_world_render=False,
        )
        viewport_shading = SimpleNamespace(type="SOLID")
        area = SimpleNamespace(
            spaces=SimpleNamespace(
                active=SimpleNamespace(shading=viewport_shading)
            )
        )
        fake_bpy = SimpleNamespace(
            app=SimpleNamespace(
                timers=SimpleNamespace(
                    register=lambda callback, **_kwargs: registered.append(callback)
                )
            ),
            context=SimpleNamespace(
                scene=SimpleNamespace(game_settings=game_settings),
                window_manager=SimpleNamespace(
                    xr_session_settings=SimpleNamespace(shading=xr_shading)
                ),
            ),
        )
        startup = root / "tools" / "launch_openxr_game.py"
        launcher = (root / "tools" / "launch_live_test.ps1").read_text(
            encoding="utf-8"
        )

        with patch.dict(
            os.environ,
            {"ARRIETTY_XR_SHADING": "RENDERED"},
        ), patch.dict(sys.modules, {"bpy": fake_bpy}):
            globals_ = runpy.run_path(str(startup))
            globals_["_configure_render_mode"](area)

        self.assertTrue(game_settings.use_viewport_render)
        self.assertEqual(viewport_shading.type, "RENDERED")
        self.assertEqual(xr_shading.type, "RENDERED")
        self.assertTrue(xr_shading.use_scene_lights_render)
        self.assertTrue(xr_shading.use_scene_world_render)
        self.assertIn('[string]$Shading = "Rendered"', launcher)
        self.assertIn(
            "$env:ARRIETTY_XR_SHADING = $Shading.ToUpperInvariant()",
            launcher,
        )

    def test_world_installer_applies_runtime_render_and_collision_roles(self):
        root = Path(__file__).parents[1]
        installer = (root / "tools" / "install_tuval_world.py").read_text(
            encoding="utf-8"
        )

        self.assertIn('obj.game.physics_type = "NO_COLLISION"', installer)
        self.assertIn('obj.game.physics_type = "STATIC"', installer)
        self.assertIn("obj.visible_shadow = cast_shadow", installer)

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

    def test_google_tile_wait_mode_detects_live_objects(self):
        registered = []
        fake_bpy = SimpleNamespace(
            app=SimpleNamespace(
                timers=SimpleNamespace(
                    register=lambda callback, **_kwargs: registered.append(callback)
                )
            ),
            data=SimpleNamespace(
                objects=[{"secret_world_google_live": True}]
            ),
        )
        launcher = Path(__file__).parents[1] / "tools" / "launch_openxr_game.py"

        with patch.dict(
            os.environ,
            {"ARRIETTY_WAIT_FOR_GOOGLE_TILES": "1"},
        ), patch.dict(sys.modules, {"bpy": fake_bpy}):
            globals_ = runpy.run_path(str(launcher))

        self.assertTrue(globals_["_wait_for_google_tiles"])
        self.assertTrue(globals_["_google_tiles_ready"]())


if __name__ == "__main__":
    unittest.main()
