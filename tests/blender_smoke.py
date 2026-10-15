# SPDX-License-Identifier: GPL-3.0-or-later
"""Run with Blender --background --factory-startup; never save user files."""

from pathlib import Path
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
    print("Baya 3D smoke checks passed: preset-before-addon repair, native tools, effective user maps, base-mesh preservation")
finally:
    blender_maya.unregister()
