# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with Blender --background --factory-startup; never save user files."""

from pathlib import Path
import math
import sys

import bpy
from bl_keymap_utils.io import keyconfig_init_from_data


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import blender_maya


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_keymap():
    controls = blender_maya.controls
    bpy.context.window_manager.keyconfigs.update()
    expected = {"Q": "builtin.select_box", "W": "builtin.move", "E": "builtin.rotate",
                "R": "builtin.scale", "T": "builtin.transform"}
    for config in (bpy.context.window_manager.keyconfigs.active, bpy.context.window_manager.keyconfigs.user):
        for mode in ("Object Mode", "Mesh", "Pose"):
            km = config.keymaps.get(mode)
            require(km is not None, f"Missing {mode} map in {config.name}")
            for key, target in expected.items():
                items = [item for item in km.keymap_items if item.type == key and item.active
                         and not any((item.ctrl, item.alt, item.shift, item.oskey))]
                matches = [item for item in items if item.idname == "wm.tool_set_by_id"
                           and getattr(item.properties, "name", None) == target]
                require(len(matches) == 1, f"{config.name}/{mode}/{key}: expected one native {target} binding")
                require(not matches[0].properties.cycle, f"{mode}/{key} unexpectedly cycles tools")
        view = config.keymaps.get("3D View")
        for key, level in (("ONE", 1), ("TWO", 2), ("THREE", 3)):
            items = [item for item in view.keymap_items if item.type == key and item.idname == "maya_style.smooth_preview"]
            require(len(items) == 1 and items[0].properties.level == level,
                    f"{config.name}/{key}: smooth-preview operator property lost")
        for map_name, _args, payload in controls.keyconfig_data():
            keymap = config.keymaps.get(map_name)
            for operator, event, data in payload["items"]:
                if not operator.startswith("maya_style.") or not data:
                    continue
                item = next((item for item in keymap.keymap_items
                             if item.idname == operator and item.type == event["type"]
                             and item.value == event["value"]
                             and all(bool(getattr(item, mod)) == bool(event.get(mod, False))
                                     for mod in ("ctrl", "alt", "shift", "oskey"))), None)
                require(item is not None, f"{config.name}/{map_name}/{operator}: missing binding")
                for prop, value in data.get("properties", []):
                    require(getattr(item.properties, prop) == value,
                            f"{config.name}/{map_name}/{operator}/{prop}: custom property lost")


def check_preview_preserves_data():
    scene = bpy.context.scene
    obj = next(obj for obj in scene.objects if obj.type == "MESH")
    for other in bpy.context.selected_objects:
        other.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    existing = obj.modifiers.new("Existing artist modifier", "BEVEL")
    original_positions = [tuple(vertex.co) for vertex in obj.data.vertices]
    original_shading = [face.use_smooth for face in obj.data.polygons]
    area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")
    with bpy.context.temp_override(area=area, region=region):
        require("FINISHED" in bpy.ops.maya_style.smooth_preview(level=3), "Preview could not be enabled")
        require(existing in list(obj.modifiers), "Preview removed an existing modifier")
        require([tuple(vertex.co) for vertex in obj.data.vertices] == original_positions, "Preview changed base vertex positions")
        require([face.use_smooth for face in obj.data.polygons] == original_shading, "Preview changed base face shading")
        require("FINISHED" in bpy.ops.maya_style.smooth_preview(level=1), "Preview could not be disabled")
        require(existing.show_viewport, "Disabling preview hid an existing modifier")
        preview = [modifier for modifier in obj.modifiers if modifier != existing]
        require(len(preview) == 2 and not any(modifier.show_viewport for modifier in preview), "Preview modifiers were not disabled")
        require(not any(modifier.show_render for modifier in preview), "Preview unexpectedly affects final renders")


def check_maya_workflow_and_coordinates():
    scene = bpy.context.scene
    ms = scene.maya_style
    area = next(area for area in bpy.context.screen.areas if area.type == "VIEW_3D")
    region = next(region for region in area.regions if region.type == "WINDOW")

    with bpy.context.temp_override(area=area, region=region):
        # 1. Maya Y-Up vs Blender Z-Up XYZ Coordinate Mapping
        obj = bpy.context.object
        require(ms.coord_system == "MAYA_Y_UP", "Default coordinate system should be MAYA_Y_UP")
        ms.maya_tx = 2.5
        ms.maya_ty = 7.0
        ms.maya_tz = -4.0
        require(math.isclose(obj.location.x, 2.5, abs_tol=1e-5), "Maya TX did not map to X")
        require(math.isclose(obj.location.z, 7.0, abs_tol=1e-5), "Maya TY (Up) did not map to Blender Z")
        require(math.isclose(obj.location.y, -4.0, abs_tol=1e-5), "Maya TZ (Depth) did not map to Blender Y")

        # 2. Freeze & Reset Transformations
        ms.maya_sx = 2.0
        ms.maya_sy = 3.0
        ms.maya_sz = 1.5
        require("FINISHED" in bpy.ops.maya_style.poly_action(action="FREEZE_ALL"), "Freeze All failed")
        require(all(math.isclose(v, 0.0, abs_tol=1e-5) for v in obj.location), "Freeze All did not zero location")
        require(all(math.isclose(v, 1.0, abs_tol=1e-5) for v in obj.scale), "Freeze All did not reset scale to 1")
        require("FINISHED" in bpy.ops.maya_style.poly_action(action="CENTER_PIVOT"), "Center Pivot failed")

        # 3. Component Mode Switching (F9, F10, F11, Multi, F8)
        for comp, expected_mask in [
            ("VERT", (True, False, False)),
            ("EDGE", (False, True, False)),
            ("FACE", (False, False, True)),
            ("MULTI", (True, True, True)),
        ]:
            require("FINISHED" in bpy.ops.maya_style.component(mode=comp), f"Component mode {comp} failed")
            require(bpy.context.mode == "EDIT_MESH", f"Component mode {comp} did not enter EDIT_MESH")
            require(tuple(scene.tool_settings.mesh_select_mode) == expected_mask, f"Mask mismatch for {comp}")
        require("FINISHED" in bpy.ops.maya_style.component(mode="OBJECT"), "Object mode F8 failed")
        require(bpy.context.mode == "OBJECT", "Did not return to OBJECT mode")

        # 4. Duplicate, Combine, Delete History
        require("FINISHED" in bpy.ops.maya_style.duplicate(), "Duplicate failed")
        dup = bpy.context.object
        dup.location.x += 3.0
        obj.select_set(True)
        dup.select_set(True)
        bpy.context.view_layer.objects.active = obj
        require("FINISHED" in bpy.ops.maya_style.poly_action(action="COMBINE"), "Combine failed")
        require("FINISHED" in bpy.ops.maya_style.poly_action(action="DELETE_HISTORY"), "Delete History failed")
        non_preview_mods = [m for m in obj.modifiers if not m.name.startswith("Baya ")]
        require(len(non_preview_mods) == 0, "Delete History left non-preview modifiers behind")

        # 5. Pivot Mode & Snap Toggles
        require("FINISHED" in bpy.ops.maya_style.pivot_mode(action="TOGGLE"), "Pivot toggle failed")
        require(scene.tool_settings.use_transform_data_origin is True, "Pivot mode did not enable data origin")
        require("FINISHED" in bpy.ops.maya_style.pivot_mode(action="TOGGLE"), "Pivot untoggle failed")
        require(scene.tool_settings.use_transform_data_origin is False, "Pivot mode did not disable data origin")

        require("FINISHED" in bpy.ops.maya_style.snap_hold(mode="GRID", toggle=True), "Grid snap toggle failed")
        require(scene.tool_settings.use_snap and "INCREMENT" in scene.tool_settings.snap_elements, "Grid snap not set")
        require("FINISHED" in bpy.ops.maya_style.snap_hold(mode="GRID", toggle=True), "Grid snap untoggle failed")

        # 6. Shader Assignment & Display Layers
        for shader in ("STANDARD_SURFACE", "LAMBERT", "BLINN", "PHONG", "SURFACE_SHADER"):
            require("FINISHED" in bpy.ops.maya_style.assign_shader(shader_type=shader), f"Shader {shader} failed")
        require(obj.active_material is not None, "Active material not assigned")
        require("FINISHED" in bpy.ops.maya_style.layer_create(name="props_layer"), "Layer creation failed")
        require("props_layer" in bpy.data.collections, "Display layer collection not created")

        # 7. Menu Sets, Shelves & MEL Command Line Execution
        for shelf_id in ("CURVES", "MODEL", "SCULPT", "UV", "RIG", "ANIM", "FX", "RENDER"):
            require("FINISHED" in bpy.ops.maya_style.shelf(name=shelf_id), f"Shelf {shelf_id} switch failed")
        for mel_cmd in ("polySphere", "CenterPivot", "FreezeTransformations", "DeleteHistory"):
            require("FINISHED" in bpy.ops.maya_style.command_exec(command=mel_cmd, language="MEL"), f"MEL {mel_cmd} failed")


bpy.utils.keyconfig_init()
# Reproduce the application order that caused the regression: the generated
# preset is initialized while custom operator RNA is not yet registered.
config = bpy.context.window_manager.keyconfigs.new(blender_maya.controls.KEYCONFIG_NAME)
keyconfig_init_from_data(config, blender_maya.controls.keyconfig_data())
bpy.context.window_manager.keyconfigs.active = config
blender_maya.register()
try:
    bpy.context.window_manager.keyconfigs.update()
    view = config.keymaps["3D View"]
    second = next(item for item in view.keymap_items if item.type == "TWO"
                  and item.idname == "maya_style.smooth_preview")
    require(not second.properties.is_property_set("level"), "Regression setup did not lose pre-registration RNA properties")
    require(blender_maya.controls.repair_keyconfig(), "Registered preset repair did not run")
    check_keymap()
    check_preview_preserves_data()
    check_maya_workflow_and_coordinates()
    print("Baya 3D smoke checks passed: preset-before-addon repair, native tools, effective user maps, base-mesh preservation, Maya XYZ coordinates, modeling workflow, shaders, shelves & MEL command bar")
finally:
    blender_maya.unregister()
