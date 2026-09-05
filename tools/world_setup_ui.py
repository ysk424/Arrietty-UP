"""Editor-only preflight UI. Never imported by the game-frame package."""
import importlib.util
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone

import bpy
from bpy.props import StringProperty
from bpy.app.handlers import persistent

_solar = None
_playing = False
_keymaps = []
_focus_attempts = 0


def load_solar():
    global _solar
    if _solar is None:
        path = os.environ.get('SECRET_WORLD_SOLAR_MODULE','').strip()
        if not path:
            return None
        spec = importlib.util.spec_from_file_location('secret_world_solar_adapter',Path(path))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _solar = module
    return _solar


def pending(scene):
    return (scene.arrietty_local_date+' '+scene.arrietty_local_time).strip() != scene.get('arrietty_applied_datetime','')


class ARRIETTY_OT_apply_world_time(bpy.types.Operator):
    bl_idname = 'arrietty.apply_world_time'
    bl_label = '日時を適用'
    bl_description = 'ツバル現地日時を太陽・空へ反映します（ゲーム中は時刻固定）'

    @classmethod
    def poll(cls, context):
        return not _playing and _solar is not None

    def execute(self, context):
        scene = context.scene
        try:
            result = _solar.apply(scene,scene.arrietty_local_date,scene.arrietty_local_time)
        except (ValueError,RuntimeError,KeyError) as error:
            self.report({'ERROR'},str(error))
            return {'CANCELLED'}
        scene['arrietty_applied_datetime'] = (scene.arrietty_local_date+' '+scene.arrietty_local_time).strip()
        scene['arrietty_solar_status'] = '方位 %.1f° / 高度 %.1f°' % (result['azimuth_degrees'],result['elevation_degrees'])
        for window in context.window_manager.windows:
            for area in window.screen.areas: area.tag_redraw()
        print('ARRIETTY_WORLD_TIME_APPLIED '+result['local'],flush=True)
        return {'FINISHED'}


class ARRIETTY_OT_start_prepared_game(bpy.types.Operator):
    bl_idname = 'arrietty.start_prepared_game'
    bl_label = 'ゲーム開始（P）'

    @classmethod
    def poll(cls, context):
        return not _playing and context.area is not None and context.area.type == 'VIEW_3D'

    def execute(self, context):
        if _solar is not None and pending(context.scene):
            self.report({'WARNING'},'先に「日時を適用」を押してください')
            return {'CANCELLED'}
        region = next(r for r in context.area.regions if r.type=='WINDOW')
        with context.temp_override(region=region):
            bpy.ops.view3d.game_start()
        return {'FINISHED'}


class ARRIETTY_PT_world_setup(bpy.types.Panel):
    bl_label = '飛行前の日時設定'
    bl_idname = 'ARRIETTY_PT_world_setup'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Arrietty'

    def draw(self, context):
        layout,scene = self.layout,context.scene
        if _solar is None:
            layout.label(text='Secret Worldランチャーから起動してください')
            return
        layout.label(text='ツバル現地時間（UTC+12）')
        layout.prop(scene,'arrietty_local_date')
        layout.prop(scene,'arrietty_local_time')
        layout.operator('arrietty.apply_world_time',icon='LIGHT_SUN')
        if pending(scene):
            layout.label(text='変更はまだ適用されていません',icon='INFO')
        else:
            layout.label(text=scene.get('arrietty_solar_status','適用済み'))
        layout.label(text='指定日時で固定・Escで設定へ戻る')
        layout.operator('arrietty.start_prepared_game',icon='PLAY')


@persistent
def game_pre(_scene=None):
    global _playing
    _playing = True
    print('ARRIETTY_GAME_ENTERED',flush=True)


@persistent
def game_post(_scene=None):
    global _playing
    _playing = False
    # Game teardown restores editor datablocks. Reapply once after teardown.
    bpy.app.timers.register(restore_preview,first_interval=.25)


def restore_preview():
    if _playing:
        return None
    scene = bpy.context.scene
    if _solar is not None:
        value = scene.get('arrietty_applied_datetime','')
        if value:
            date,time = value.split(' ',1)
            _solar.apply(scene,date,time)
    print('ARRIETTY_WAITING_FOR_PLAY',flush=True)
    return None


def focus_setup_panel():
    global _focus_attempts
    _focus_attempts += 1
    found = False
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type == 'UI' and hasattr(region,'active_panel_category'):
                    try:
                        region.active_panel_category = 'Arrietty'
                        found = True
                    except (TypeError,ValueError,AttributeError):
                        pass  # Categories become available after the first draw.
            area.tag_redraw()
    return .25 if not found and _focus_attempts < 12 else None


def register():
    solar = load_solar()
    for cls in (ARRIETTY_OT_apply_world_time,ARRIETTY_OT_start_prepared_game,ARRIETTY_PT_world_setup):
        bpy.utils.register_class(cls)
    bpy.types.Scene.arrietty_local_date = StringProperty(name='日付',description='YYYY-MM-DD（例: 2026-09-05）')
    bpy.types.Scene.arrietty_local_time = StringProperty(name='現地時刻',description='24時間表記 HH:MM（例: 17:45）')
    if hasattr(bpy.app.handlers,'game_pre'):
        bpy.app.handlers.game_pre.append(game_pre)
        bpy.app.handlers.game_post.append(game_post)
    if solar is not None:
        cfg = solar.configuration()
        scene = bpy.context.scene
        local = datetime.now(timezone(timedelta(hours=cfg['utc_offset_hours'])))
        saved = scene.get('secret_world_solar_local','')
        scene.arrietty_local_date = saved[:10] if saved else local.date().isoformat()
        scene.arrietty_local_time = saved[11:16] if saved else cfg['default_time']
        bpy.ops.arrietty.apply_world_time()
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig is not None:
        keymap = keyconfig.keymaps.new(name='3D View',space_type='VIEW_3D')
        item = keymap.keymap_items.new('arrietty.start_prepared_game','P','PRESS')
        _keymaps.append((keymap,item))
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.show_region_ui = True
                area.tag_redraw()
    if not bpy.app.background:
        bpy.app.timers.register(focus_setup_panel,first_interval=.25)
    print('ARRIETTY_WORLD_SETUP_READY',flush=True)
