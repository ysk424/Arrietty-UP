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
PFD_PITCH_METERS_PER_DEGREE = 0.004


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


def _math_socket(nodes, links, operation: str, left, right=None):
    node = nodes.new("ShaderNodeMath")
    node.operation = operation
    if hasattr(left, "is_output"):
        links.new(left, node.inputs[0])
    else:
        node.inputs[0].default_value = left
    if right is not None:
        if hasattr(right, "is_output"):
            links.new(right, node.inputs[1])
        else:
            node.inputs[1].default_value = right
    return node.outputs[0]


def _pfd_attitude_material(name, sky_color, ground_color, line_color):
    """Build a fixed-disc PFD material evaluated entirely by the GPU."""
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    material.use_backface_culling = False
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Roughness"].default_value = 0.72
    principled.inputs["Emission Strength"].default_value = 0.8
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    coordinates = nodes.new("ShaderNodeTexCoord")
    generated = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coordinates.outputs["Generated"], generated.inputs[0])
    object_info = nodes.new("ShaderNodeObjectInfo")
    attitude = nodes.new("ShaderNodeSeparateColor")
    attitude.mode = "RGB"
    links.new(object_info.outputs["Color"], attitude.inputs[0])

    diameter = 2.0 * PFD_RADIUS_METERS
    x_meters = _math_socket(
        nodes,
        links,
        "MULTIPLY",
        _math_socket(nodes, links, "SUBTRACT", generated.outputs["X"], 0.5),
        diameter,
    )
    z_meters = _math_socket(
        nodes,
        links,
        "MULTIPLY",
        _math_socket(nodes, links, "SUBTRACT", generated.outputs["Z"], 0.5),
        diameter,
    )
    sin_bank = _math_socket(
        nodes,
        links,
        "SUBTRACT",
        _math_socket(nodes, links, "MULTIPLY", attitude.outputs["Red"], 2.0),
        1.0,
    )
    cos_bank = _math_socket(
        nodes,
        links,
        "SUBTRACT",
        _math_socket(nodes, links, "MULTIPLY", attitude.outputs["Green"], 2.0),
        1.0,
    )
    pitch_meters = _math_socket(
        nodes,
        links,
        "MULTIPLY",
        _math_socket(nodes, links, "SUBTRACT", attitude.outputs["Blue"], 0.5),
        60.0 * PFD_PITCH_METERS_PER_DEGREE,
    )

    # Inverse-rotate the fixed disc coordinate into the moving horizon frame.
    horizon_z = _math_socket(
        nodes,
        links,
        "ADD",
        _math_socket(
            nodes,
            links,
            "ADD",
            _math_socket(nodes, links, "MULTIPLY", sin_bank, x_meters),
            _math_socket(nodes, links, "MULTIPLY", cos_bank, z_meters),
        ),
        pitch_meters,
    )
    horizon_x = _math_socket(
        nodes,
        links,
        "SUBTRACT",
        _math_socket(nodes, links, "MULTIPLY", cos_bank, x_meters),
        _math_socket(nodes, links, "MULTIPLY", sin_bank, z_meters),
    )

    sky_mask = _math_socket(nodes, links, "GREATER_THAN", horizon_z, 0.0)
    base_color = nodes.new("ShaderNodeMixRGB")
    base_color.blend_type = "MIX"
    links.new(sky_mask, base_color.inputs[0])
    base_color.inputs[1].default_value = ground_color
    base_color.inputs[2].default_value = sky_color

    graphics_mask = _math_socket(
        nodes,
        links,
        "LESS_THAN",
        _math_socket(nodes, links, "ABSOLUTE", horizon_z),
        0.002,
    )
    abs_horizon_x = _math_socket(nodes, links, "ABSOLUTE", horizon_x)
    for pitch in (-20, -10, -5, 5, 10, 20):
        width = 0.080 if abs(pitch) % 10 == 0 else 0.045
        mark_z = _math_socket(
            nodes,
            links,
            "ABSOLUTE",
            _math_socket(
                nodes,
                links,
                "SUBTRACT",
                horizon_z,
                pitch * PFD_PITCH_METERS_PER_DEGREE,
            ),
        )
        mark_mask = _math_socket(
            nodes,
            links,
            "MULTIPLY",
            _math_socket(nodes, links, "LESS_THAN", mark_z, 0.0015),
            _math_socket(nodes, links, "LESS_THAN", abs_horizon_x, width / 2.0),
        )
        graphics_mask = _math_socket(
            nodes,
            links,
            "MAXIMUM",
            graphics_mask,
            mark_mask,
        )

    final_color = nodes.new("ShaderNodeMixRGB")
    final_color.blend_type = "MIX"
    links.new(graphics_mask, final_color.inputs[0])
    links.new(base_color.outputs[0], final_color.inputs[1])
    final_color.inputs[2].default_value = line_color
    links.new(final_color.outputs[0], principled.inputs["Base Color"])
    links.new(final_color.outputs[0], principled.inputs["Emission Color"])
    return material


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


def _circle(name: str, parent, location, radius: float, material):
    vertices = [(0.0, 0.0, 0.0)]
    segments = 64
    vertices.extend(
        (
            radius * math.cos(2.0 * math.pi * index / segments),
            0.0,
            radius * math.sin(2.0 * math.pi * index / segments),
        )
        for index in range(segments)
    )
    faces = [
        (0, 1 + ((index + 1) % segments), 1 + index)
        for index in range(segments)
    ]
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


def _build_pfd(panel, black, dark, white, sky, ground, cyan, amber, magenta):
    _text("Instrument_PFDHeading", panel, "PRIMARY FLIGHT DISPLAY", (0.0, 0.030, 0.166), 0.015, cyan, align="CENTER")
    _text(
        "Instrument_PFDState",
        panel,
        "P +0.0  B +0.0  ALT 0.0 m",
        (0.0, 0.030, -0.164),
        0.012,
        amber,
        align="CENTER",
    )

    # Vertical airspeed and altitude tapes.
    for name, x, label in (("Airspeed", 0.195, "AIR km/h"), ("Altitude", -0.195, "ALT m")):
        _box(f"Instrument_{name}Tape", panel, (x, 0.019, -0.006), (0.088, 0.008, 0.306), dark)
        _text(f"Instrument_{name}Label", panel, label, (x, 0.030, 0.129), 0.012, white, align="CENTER")
        _box(f"Instrument_{name}Window", panel, (x, 0.030, -0.006), (0.085, 0.005, 0.043), black)

    _text("Instrument_AirspeedValue", panel, "0", (0.195, 0.036, -0.006), 0.026, amber, align="CENTER")
    _text("Instrument_AltitudeValue", panel, "0", (-0.195, 0.036, -0.006), 0.026, amber, align="CENTER")
    tick_specs = (("M2", -0.112), ("M1", -0.061), ("P1", 0.049), ("P2", 0.100))
    for suffix, z in tick_specs:
        _text(f"Instrument_AirspeedTick_{suffix}", panel, "", (0.195, 0.030, z), 0.013, white, align="CENTER")
        _text(f"Instrument_AltitudeTick_{suffix}", panel, "", (-0.195, 0.030, z), 0.013, white, align="CENTER")
        _box(f"Instrument_AirTickLine_{suffix}", panel, (0.151, 0.030, z), (0.012, 0.003, 0.002), white)
        _box(f"Instrument_AltTickLine_{suffix}", panel, (-0.151, 0.030, z), (0.012, 0.003, 0.002), white)

    # One fixed circular disc draws the complete moving attitude presentation.
    # Object color carries pitch/bank as a compact per-object GPU uniform.
    attitude_material = _pfd_attitude_material(
        "InstrumentPFDAttitude",
        tuple(sky.diffuse_color),
        tuple(ground.diffuse_color),
        tuple(white.diffuse_color),
    )
    attitude = _circle(
        "Instrument_PFD_Attitude",
        panel,
        (0.0, 0.018, 0.0),
        PFD_RADIUS_METERS,
        attitude_material,
    )
    attitude.color = (0.5, 1.0, 0.5, 1.0)
    attitude["pfd_render_path"] = "FIXED_DISC_GPU_MATERIAL"

    _ring("Instrument_PFD_Bezel", panel, (0.0, 0.033, 0.0), 0.1345, white)

    # Fixed aircraft symbol: it does not move with the horizon/ladder group.
    _box("Instrument_AircraftLeft", panel, (-0.041, 0.038, -0.006), (0.058, 0.004, 0.005), magenta)
    _box("Instrument_AircraftRight", panel, (0.041, 0.038, -0.006), (0.058, 0.004, 0.005), magenta)
    _box("Instrument_AircraftCenter", panel, (0.0, 0.038, -0.012), (0.005, 0.004, 0.018), magenta)


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
        "T2  IDLE\nHR  DISCONNECTED\nSTR IDLE +0.0\nCMD P+0 R+0\nTUNE OFF\nFAN 0/--\nVOICE IDLE\nXR NOT CHECKED\nFRAME  0.0 ms",
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
    _build_pfd(panel, black, dark, white, sky, ground, cyan, amber, magenta)
    _build_right(panel, white, cyan, amber)

    scene["instrument_panel_version"] = 2
    scene["instrument_panel_mount"] = "BICYCLE_FIXED"
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
