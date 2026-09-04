"""Build the bicycle-fixed three-section instrument panel in the UPBGE scene.

The panel root is parented to ``ArriettyRuntime`` and its exposed custom
properties are the intended adjustment points for the later HMD fit test.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys

import bpy


DEFAULT_OUTPUT = Path(r"C:\Users\azoo\git\Arrietty-UP\Arrietty-UP.blend")
PANEL_PREFIX = "Instrument_"
PFD_RADIUS_METERS = 0.132
PFD_HORIZON_RADIUS_METERS = 0.190
PFD_MASK_OUTER_RADIUS_METERS = 0.242


def _requested_output() -> Path:
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--panel-output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(arguments).panel_output


def _material(name: str, color: tuple[float, float, float, float], emission: float):
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = color
    value.use_nodes = True
    value.use_backface_culling = False
    principled = value.node_tree.nodes.get("Principled BSDF")
    if principled is not None:
        principled.inputs["Base Color"].default_value = color
        principled.inputs["Roughness"].default_value = 0.72
        principled.inputs["Emission Color"].default_value = color
        principled.inputs["Emission Strength"].default_value = emission
    return value


def _parent_at(obj, parent, location) -> None:
    obj.parent = parent
    obj.matrix_parent_inverse.identity()
    obj.location = location


def _empty(name: str, parent, location=(0.0, 0.0, 0.0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.04
    _parent_at(obj, parent, location)
    return obj


def _box(name: str, parent, location, dimensions, material):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    _parent_at(obj, parent, location)
    obj.data.materials.append(material)
    return obj


def _semicircle(name: str, parent, upper: bool, radius: float, material):
    vertices = [(0.0, 0.0, 0.0)]
    segments = 64
    start = 0.0 if upper else math.pi
    vertices.extend(
        (
            radius * math.cos(start + math.pi * index / segments),
            0.0,
            radius * math.sin(start + math.pi * index / segments),
        )
        for index in range(segments + 1)
    )
    faces = [(0, index + 2, index + 1) for index in range(segments)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    _parent_at(obj, parent, (0.0, 0.0, 0.0))
    return obj


def _aperture_mask(name: str, parent, location, inner_radius: float, outer_radius: float, material):
    """Create an opaque annulus that clips moving PFD geometry physically."""
    segments = 64
    vertices = []
    for index in range(segments):
        angle = 2.0 * math.pi * index / segments
        direction = (math.cos(angle), math.sin(angle))
        vertices.extend(
            (
                (inner_radius * direction[0], 0.0, inner_radius * direction[1]),
                (outer_radius * direction[0], 0.0, outer_radius * direction[1]),
            )
        )
    faces = []
    for index in range(segments):
        next_index = (index + 1) % segments
        faces.append((2 * index, 2 * next_index, 2 * next_index + 1, 2 * index + 1))
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    _parent_at(obj, parent, location)
    return obj


def _ring(name: str, parent, location, radius: float, material):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=radius,
        minor_radius=0.0025,
        major_segments=64,
        minor_segments=8,
    )
    obj = bpy.context.object
    obj.name = name
    _parent_at(obj, parent, location)
    obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    obj.data.materials.append(material)
    return obj


def _drive_panel_placement(panel) -> None:
    """Make the named placement properties live Blender adjustment controls."""
    for data_path, index, property_name, expression in (
        ("location", 1, "panel_forward_m", "-value"),
        ("location", 2, "panel_center_height_m", "value"),
        (
            "rotation_euler",
            0,
            "panel_tilt_degrees",
            "value * 0.0174532925199433",
        ),
    ):
        curve = panel.driver_add(data_path, index)
        driver = curve.driver
        driver.type = "SCRIPTED"
        driver.expression = expression
        variable = driver.variables.new()
        variable.name = "value"
        variable.type = "SINGLE_PROP"
        variable.targets[0].id = panel
        variable.targets[0].data_path = f'["{property_name}"]'


def _text(
    name: str,
    parent,
    body: str,
    location,
    size: float,
    material,
    *,
    align: str = "LEFT",
):
    curve = bpy.data.curves.new(f"{name}_Font", type="FONT")
    curve.body = body
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.resolution_u = 8
    obj = bpy.data.objects.new(name, curve)
    bpy.context.scene.collection.objects.link(obj)
    _parent_at(obj, parent, location)
    # Font local X/Y becomes the rider's screen-right/up axes and faces local Y+.
    obj.rotation_euler = (math.radians(-90.0), math.radians(180.0), 0.0)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.game_property_new(type="STRING", name="Text")
    # UPBGE's BL_ConvertProperties passes a string property's internal pointer
    # directly to strlen(). A newly-created empty RNA string may retain a null
    # pointer, so keep authored blank labels non-empty until the runtime owns
    # and updates the converted property.
    obj.game.properties[-1].value = body if body else " "
    return obj


def _delete_previous_panel() -> None:
    for obj in tuple(bpy.data.objects):
        if obj.name == "InstrumentPanelRoot" or obj.name.startswith(PANEL_PREFIX):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)


def _section_frame(parent, center_x: float, width: float, height: float, materials):
    black, frame = materials
    _box(
        f"{PANEL_PREFIX}Section_{center_x:+.3f}",
        parent,
        (center_x, 0.0, 0.0),
        (width, 0.020, height),
        black,
    )
    edge = 0.005
    front = 0.014
    for index, (x, z, w, h) in enumerate(
        (
            (center_x, height / 2.0 - edge / 2.0, width, edge),
            (center_x, -height / 2.0 + edge / 2.0, width, edge),
            (center_x - width / 2.0 + edge / 2.0, 0.0, edge, height),
            (center_x + width / 2.0 - edge / 2.0, 0.0, edge, height),
        )
    ):
        _box(
            f"{PANEL_PREFIX}Frame_{center_x:+.3f}_{index}",
            parent,
            (x, front, z),
            (w, 0.003, h),
            frame,
        )


def _build_left(panel, white, cyan, red, amber):
    # The rider faces world Y-, so rider-left is panel-local X+.
    x0 = 0.510
    _text("Instrument_LeftHeading", panel, "BICYCLE", (x0, 0.022, 0.166), 0.018, cyan)

    _text("Instrument_HeartRateLabel", panel, "HEART RATE", (x0, 0.022, 0.122), 0.017, white)
    _text("Instrument_HeartRateValue", panel, "---", (x0, 0.022, 0.074), 0.055, red)
    _text("Instrument_HeartRateUnit", panel, "bpm", (0.335, 0.022, 0.073), 0.016, red)

    _text("Instrument_PowerLabel", panel, "T2 POWER", (x0, 0.022, 0.018), 0.017, white)
    _text("Instrument_PowerValue", panel, "0", (x0, 0.022, -0.030), 0.055, cyan)
    _text("Instrument_PowerUnit", panel, "W", (0.330, 0.022, -0.031), 0.018, cyan)

    _text("Instrument_GroundSpeedLabel", panel, "GROUND", (x0, 0.022, -0.079), 0.014, white)
    _text("Instrument_GroundSpeedValue", panel, " 0.0 km/h", (0.415, 0.022, -0.079), 0.018, white)
    _text("Instrument_GradeLabel", panel, "T2 GRADE", (x0, 0.022, -0.111), 0.014, white)
    _text("Instrument_GradeValue", panel, "--.- %", (0.385, 0.022, -0.111), 0.018, white)
    _text("Instrument_ModeLabel", panel, "MODE", (x0, 0.022, -0.148), 0.014, white)
    _text("Instrument_ModeValue", panel, "STANDBY", (0.420, 0.022, -0.148), 0.018, amber)
    _text("Instrument_ElapsedLabel", panel, "ELAPSED", (x0, 0.022, -0.178), 0.013, white)
    _text("Instrument_ElapsedValue", panel, "0:00:00", (0.420, 0.022, -0.178), 0.016, amber)


def _build_pfd(panel, black, dark, white, sky, ground, cyan, amber, magenta, red):
    _text(
        "Instrument_PFDHeading",
        panel,
        "PRIMARY FLIGHT DISPLAY",
        (0.0, 0.030, 0.112),
        0.010,
        cyan,
        align="CENTER",
    )
    _text(
        "Instrument_PFDState",
        panel,
        "P +0.0  B +0.0  ALT 0.0 m",
        (0.0, 0.030, -0.164),
        0.012,
        amber,
        align="CENTER",
    )

    # Horizontal heading tape. The game-frame path updates these authored
    # objects through UPBGE's bge API and never imports bpy.
    _box(
        "Instrument_CompassTape",
        panel,
        (0.0, 0.019, 0.163),
        (0.300, 0.008, 0.064),
        dark,
    )
    _text(
        "Instrument_CompassLabel",
        panel,
        "HDG",
        (0.124, 0.030, 0.185),
        0.009,
        white,
        align="CENTER",
    )
    heading_tick_specs = (
        ("M2", 0.118),
        ("M1", 0.068),
        ("P1", -0.068),
        ("P2", -0.118),
    )
    for suffix, x in heading_tick_specs:
        _text(
            f"Instrument_HeadingTick_{suffix}",
            panel,
            "000",
            (x, 0.030, 0.163),
            0.011,
            white,
            align="CENTER",
        )
        _box(
            f"Instrument_HeadingTickLine_{suffix}",
            panel,
            (x, 0.030, 0.143),
            (0.002, 0.003, 0.009),
            white,
        )
    _box(
        "Instrument_HeadingWindow",
        panel,
        (0.0, 0.031, 0.163),
        (0.050, 0.005, 0.034),
        black,
    )
    _text(
        "Instrument_HeadingValue",
        panel,
        "000",
        (0.0, 0.037, 0.163),
        0.020,
        amber,
        align="CENTER",
    )
    _box(
        "Instrument_CompassIndex",
        panel,
        (0.0, 0.037, 0.140),
        (0.003, 0.003, 0.011),
        amber,
    )
    home_marker = _text(
        "Instrument_CompassHomeMarker",
        panel,
        "HOME",
        (0.0, 0.038, 0.136),
        0.010,
        magenta,
        align="CENTER",
    )
    home_marker["panel_base_y"] = 0.038
    home_marker["panel_base_z"] = 0.136
    home_marker["navigation_source"] = "UPBGE RUNTIME NO BPY"

    # Vertical airspeed and altitude tapes.
    for name, x, label in (("Airspeed", 0.195, "AIR km/h"), ("Altitude", -0.195, "ALT m")):
        _box(f"Instrument_{name}Tape", panel, (x, 0.019, -0.006), (0.088, 0.008, 0.306), dark)
        _text(f"Instrument_{name}Label", panel, label, (x, 0.030, 0.129), 0.012, white, align="CENTER")
        _box(f"Instrument_{name}Window", panel, (x, 0.030, -0.006), (0.085, 0.005, 0.043), black)

    _text("Instrument_AirspeedValue", panel, "0", (0.195, 0.036, -0.006), 0.026, amber, align="CENTER")
    _text(
        "Instrument_StallSpeedValue",
        panel,
        "STALL 18",
        (0.195, 0.030, -0.177),
        0.009,
        red,
        align="CENTER",
    )
    _text("Instrument_AltitudeValue", panel, "0", (-0.195, 0.036, -0.006), 0.026, amber, align="CENTER")
    tick_specs = (("M2", -0.112), ("M1", -0.061), ("P1", 0.049), ("P2", 0.100))
    for suffix, z in tick_specs:
        _text(f"Instrument_AirspeedTick_{suffix}", panel, "", (0.195, 0.030, z), 0.013, white, align="CENTER")
        _text(f"Instrument_AltitudeTick_{suffix}", panel, "", (-0.195, 0.030, z), 0.013, white, align="CENTER")
        _box(f"Instrument_AirTickLine_{suffix}", panel, (0.151, 0.030, z), (0.012, 0.003, 0.002), white)
        _box(f"Instrument_AltTickLine_{suffix}", panel, (-0.151, 0.030, z), (0.012, 0.003, 0.002), white)

    # Use ordinary meshes and a foreground annulus instead of a node shader.
    # UPBGE/OpenXR renders this physical depth mask consistently in both eyes.
    attitude = _empty("Instrument_PFD_Attitude", panel, (0.0, 0.013, 0.0))
    attitude["panel_base_y"] = 0.013
    attitude["pfd_render_path"] = "CIRCULAR_MASKED_GEOMETRY"
    _semicircle(
        "Instrument_PFD_Sky",
        attitude,
        True,
        PFD_HORIZON_RADIUS_METERS,
        sky,
    )
    _semicircle(
        "Instrument_PFD_Ground",
        attitude,
        False,
        PFD_HORIZON_RADIUS_METERS,
        ground,
    )
    _box(
        "Instrument_PFD_HorizonLine",
        attitude,
        (0.0, 0.001, 0.0),
        (2.0 * PFD_HORIZON_RADIUS_METERS, 0.002, 0.004),
        white,
    )
    ladder = _empty("Instrument_PFD_Ladder", attitude, (0.0, 0.001, 0.0))
    for pitch in (-20, -10, -5, 5, 10, 20):
        width = 0.080 if abs(pitch) % 10 == 0 else 0.045
        _box(
            f"Instrument_PitchMark_{pitch:+03d}",
            ladder,
            (0.0, 0.0, pitch * 0.004),
            (width, 0.002, 0.003),
            white,
        )

    clip_mask = _aperture_mask(
        "Instrument_PFD_ClipMask",
        panel,
        (0.0, 0.017, 0.0),
        PFD_RADIUS_METERS,
        PFD_MASK_OUTER_RADIUS_METERS,
        black,
    )
    clip_mask["pfd_clip_path"] = "OPAQUE_ANNULUS"

    # Mask and bezel share one depth plane so an oblique HMD view cannot
    # introduce a one-eye/one-line-width parallax offset.
    _ring("Instrument_PFD_Bezel", panel, (0.0, 0.017, 0.0), 0.1345, white)

    # Fixed aircraft symbol: it does not move with the horizon/ladder group.
    _box("Instrument_AircraftLeft", panel, (-0.041, 0.021, -0.006), (0.058, 0.004, 0.005), magenta)
    _box("Instrument_AircraftRight", panel, (0.041, 0.021, -0.006), (0.058, 0.004, 0.005), magenta)
    _box("Instrument_AircraftCenter", panel, (0.0, 0.021, -0.012), (0.005, 0.004, 0.018), magenta)


def _build_right(panel, white, cyan, amber):
    x0 = -0.295
    _text("Instrument_RightHeading", panel, "PHYSICS / DEBUG", (x0, 0.022, 0.166), 0.016, cyan)
    _text(
        "Instrument_PhysicsText",
        panel,
        "ALT       0.0 m\nV/S     +0.0 m/s\nPITCH   +0.0 deg\nBANK    +0.0 deg\nAOA     +0.0 deg\nCAD      0.0 rpm\nHEAD    +0.0 deg",
        (x0, 0.022, 0.105),
        0.014,
        white,
    )
    _text(
        "Instrument_DebugText",
        panel,
        "T2  IDLE\nHR  DISCONNECTED\nSTR IDLE +0.0\nCMD P+0 R+0\nTUNE OFF\nFAN 0/-- WAIT\nVOICE IDLE\nXR NOT CHECKED\nFRAME  0.0 ms",
        (x0, 0.022, -0.055),
        0.012,
        amber,
    )


def build_panel(scene=None):
    scene = scene or bpy.context.scene
    runtime_root = scene.objects.get("ArriettyRuntime")
    if runtime_root is None:
        raise RuntimeError("ArriettyRuntime must exist before building the panel")

    _delete_previous_panel()
    black = _material("InstrumentPanelBlack", (0.006, 0.009, 0.013, 1.0), 0.05)
    dark = _material("InstrumentTapeDark", (0.018, 0.026, 0.038, 1.0), 0.10)
    frame = _material("InstrumentFrame", (0.18, 0.22, 0.27, 1.0), 0.20)
    white = _material("InstrumentWhite", (0.86, 0.94, 1.0, 1.0), 1.4)
    cyan = _material("InstrumentCyan", (0.05, 0.85, 1.0, 1.0), 1.8)
    red = _material("InstrumentRed", (1.0, 0.08, 0.05, 1.0), 1.8)
    amber = _material("InstrumentAmber", (1.0, 0.60, 0.03, 1.0), 1.7)
    magenta = _material("InstrumentAircraft", (1.0, 0.05, 0.75, 1.0), 2.0)
    sky = _material("InstrumentSky", (0.015, 0.25, 0.62, 1.0), 0.65)
    ground = _material("InstrumentGround", (0.38, 0.13, 0.035, 1.0), 0.55)

    panel = _empty("InstrumentPanelRoot", runtime_root, (0.0, -1.3, 1.0))
    panel.rotation_euler = (math.radians(46.565), 0.0, 0.0)
    panel["panel_forward_m"] = 1.3
    panel["panel_center_height_m"] = 1.0
    panel["panel_tilt_degrees"] = 46.565
    panel["panel_total_width_m"] = 1.08
    panel["panel_total_height_m"] = 0.40
    panel["panel_layout"] = "LEFT:BICYCLE CENTER:PFD RIGHT:PHYSICS_DEBUG"
    _drive_panel_placement(panel)

    _section_frame(panel, -0.405, 0.270, 0.400, (black, frame))
    _section_frame(panel, 0.000, 0.500, 0.400, (black, frame))
    _section_frame(panel, 0.405, 0.270, 0.400, (black, frame))
    _build_left(panel, white, cyan, red, amber)
    _build_pfd(panel, black, dark, white, sky, ground, cyan, amber, magenta, red)
    _build_right(panel, white, cyan, amber)

    scene["instrument_panel_version"] = 5
    scene["instrument_panel_mount"] = "BICYCLE_FIXED"
    scene["instrument_compass_runtime"] = "UPBGE RUNTIME NO BPY"
    return panel


if __name__ == "__main__":
    panel = build_panel()
    output = _requested_output()
    bpy.ops.wm.save_as_mainfile(filepath=str(output), check_existing=False)
    print(
        "ARRIETTY_INSTRUMENT_PANEL_BUILT",
        {
            "output": str(output),
            "root": panel.name,
            "parent": panel.parent.name,
            "location": tuple(round(value, 3) for value in panel.location),
            "tilt_degrees": panel["panel_tilt_degrees"],
        },
    )
