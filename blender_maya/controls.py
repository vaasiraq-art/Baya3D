"""Baya 3D controls for Blender 5.3; a complete Maya-inspired keymap and toolset.

Importing and registering this module never saves preferences. The installer
explicitly calls install_keyconfig(), then decides when preferences are saved.
"""

import ast
import importlib.util
import math
import os
import pprint
import time

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty, StringProperty
from mathutils import Vector


KEYCONFIG_NAME = "Baya_3D"
_PREVIEW_UID = "_maya_style_preview_modifier_uid"
_NORMALS_UID = "_maya_style_preview_normals_modifier_uid"
_NORMALS_GROUP_TAG = "_maya_style_preview_normals_group"
_PREVIEW_WIRE = "_maya_style_preview_wire_display"
_last_tools = {}
_keyconfig_repair_attempts = 0
_hotbox_active = False
_snap_hold_active = False
_basic_tools = {
    "builtin.select",
    "builtin.select_box",
    "builtin.select_circle",
    "builtin.select_lasso",
    "builtin.move",
    "builtin.rotate",
    "builtin.scale",
    "builtin.transform",
}


def _view_poll(context):
    return context.area is not None and context.area.type == 'VIEW_3D'


def is_hotbox_active():
    return _hotbox_active


def is_snap_hold_active():
    return _snap_hold_active


def _preview_normals_group():
    """Smooth only the evaluated preview geometry; never change base mesh flags."""
    for group in bpy.data.node_groups:
        if group.bl_idname == 'GeometryNodeTree' and group.get(_NORMALS_GROUP_TAG) == 1:
            return group
    group = bpy.data.node_groups.new("Baya Preview Smooth Normals", 'GeometryNodeTree')
    group[_NORMALS_GROUP_TAG] = 1
    group.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    group.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    source = group.nodes.new('NodeGroupInput')
    source.location = (-220, 0)
    smooth = group.nodes.new('GeometryNodeSetShadeSmooth')
    smooth.domain = 'FACE'
    smooth.inputs['Selection'].default_value = True
    smooth.inputs['Shade Smooth'].default_value = True
    target = group.nodes.new('NodeGroupOutput')
    target.location = (220, 0)
    group.links.new(source.outputs['Geometry'], smooth.inputs['Mesh'])
    group.links.new(smooth.outputs['Mesh'], target.inputs['Geometry'])
    return group


def _tool_key(context):
    return (context.workspace.as_pointer(), context.mode)


def _remember_tool(context):
    tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
    if tool and tool.idname and tool.idname not in _basic_tools:
        _last_tools[_tool_key(context)] = tool.idname


def _watch_tools():
    # Also remember tools picked with Blender's toolbar, not only our menus.
    try:
        for window in bpy.context.window_manager.windows:
            with bpy.context.temp_override(window=window):
                _remember_tool(bpy.context)
    except (ReferenceError, RuntimeError, AttributeError):
        pass
    return 0.35


class MAYA_STYLE_OT_tool(bpy.types.Operator):
    bl_idname = "maya_style.tool"
    bl_label = "Baya Tool"
    bl_description = "Select a transform or modeling tool"
    name: StringProperty(default="builtin.select_box")

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def execute(self, context):
        _remember_tool(context)
        try:
            result = bpy.ops.wm.tool_set_by_id(name=self.name, cycle=False)
            if self.name not in _basic_tools:
                _last_tools[_tool_key(context)] = self.name
            return result
        except RuntimeError:
            self.report({'WARNING'}, f"Tool '{self.name}' is unavailable in this mode")
            return {'CANCELLED'}


class MAYA_STYLE_OT_last_tool(bpy.types.Operator):
    bl_idname = "maya_style.last_tool"
    bl_label = "Last Modeling Tool"
    bl_description = "Return to the last tool other than Select, Move, Rotate or Scale"

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def execute(self, context):
        name = _last_tools.get(_tool_key(context))
        if not name:
            self.report({'INFO'}, "Choose a modeling tool first; Y recalls tools other than Q/W/E/R")
            return {'CANCELLED'}
        try:
            return bpy.ops.wm.tool_set_by_id(name=name, cycle=False)
        except RuntimeError:
            self.report({'WARNING'}, "The previous tool is unavailable in this mode")
            return {'CANCELLED'}


class MAYA_STYLE_OT_smooth_preview(bpy.types.Operator):
    bl_idname = "maya_style.smooth_preview"
    bl_label = "Smooth Mesh Preview"
    bl_description = "1: base mesh; 2: cage and smooth preview; 3: smooth preview"
    bl_options = {'REGISTER', 'UNDO'}
    level: IntProperty(default=3, min=1, max=3)

    @classmethod
    def poll(cls, context):
        return _view_poll(context) and context.mode in {'OBJECT', 'EDIT_MESH'} and any(
            obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        changed = 0
        for obj in context.selected_objects:
            if obj.type != 'MESH' or not obj.is_editable:
                continue
            uid = obj.get(_PREVIEW_UID)
            mod = next((m for m in obj.modifiers if m.type == 'SUBSURF'
                        and str(m.persistent_uid) == uid), None)
            normals_uid = obj.get(_NORMALS_UID)
            normals = next((m for m in obj.modifiers if m.type == 'NODES'
                            and str(m.persistent_uid) == normals_uid), None)
            if self.level != 2 and _PREVIEW_WIRE in obj:
                obj.show_wire, obj.show_all_edges = obj[_PREVIEW_WIRE]
                del obj[_PREVIEW_WIRE]
            if self.level == 1:
                if mod:
                    mod.show_viewport = False
                    changed += 1
                if normals:
                    normals.show_viewport = False
                continue
            if mod is None:
                mod = obj.modifiers.new("Baya Smooth Preview", 'SUBSURF')
                obj[_PREVIEW_UID] = str(mod.persistent_uid)
                # Viewport preview is intentionally excluded from renders.
                mod.show_render = False
                mod.levels = 2
            mod.show_viewport = True
            mod.show_in_editmode = True
            mod.show_on_cage = self.level == 3
            mod.show_only_control_edges = self.level == 2
            if normals is None:
                normals = obj.modifiers.new("Baya Preview Smooth Normals", 'NODES')
                obj[_NORMALS_UID] = str(normals.persistent_uid)
                normals.node_group = _preview_normals_group()
                normals.show_render = False
            normals.show_viewport = True
            normals.show_in_editmode = True
            if self.level == 2:
                if _PREVIEW_WIRE not in obj:
                    obj[_PREVIEW_WIRE] = [int(obj.show_wire), int(obj.show_all_edges)]
                obj.show_wire = True
                obj.show_all_edges = True
            changed += 1
        if not changed and self.level > 1:
            self.report({'WARNING'}, "No editable mesh objects selected")
            return {'CANCELLED'}
        return {'FINISHED'}


class MAYA_STYLE_OT_preview_divisions(bpy.types.Operator):
    bl_idname = "maya_style.preview_divisions"
    bl_label = "Smooth Preview Divisions"
    bl_description = "Increase or decrease subdivisions of the active smooth mesh preview"
    bl_options = {'REGISTER', 'UNDO'}
    delta: IntProperty(default=1, min=-1, max=1)

    @classmethod
    def poll(cls, context):
        if not _view_poll(context) or context.mode not in {'OBJECT', 'EDIT_MESH'}:
            return False
        return any(obj.type == 'MESH' and obj.is_editable and any(
            mod.type == 'SUBSURF' and mod.show_viewport and
            str(mod.persistent_uid) == obj.get(_PREVIEW_UID)
            for mod in obj.modifiers) for obj in context.selected_objects)

    def execute(self, context):
        for obj in context.selected_objects:
            if obj.type != 'MESH' or not obj.is_editable:
                continue
            uid = obj.get(_PREVIEW_UID)
            for mod in obj.modifiers:
                if mod.type == 'SUBSURF' and mod.show_viewport and str(mod.persistent_uid) == uid:
                    # Maya Page Up / Page Down affect preview divisions. Keep
                    # unrelated subdivision modifiers and render levels intact.
                    mod.levels = max(1, min(6, mod.levels + self.delta))
                    break
        return {'FINISHED'}


class MAYA_STYLE_OT_shading(bpy.types.Operator):
    bl_idname = "maya_style.shading"
    bl_label = "Viewport Display"
    bl_description = "Switch Maya-style viewport shading modes (4/5/6/7) or Wireframe on Shaded"
    mode: EnumProperty(items=[(value, label, "") for value, label in (
        ('WIREFRAME', "Wireframe"),
        ('SOLID', "Shaded"),
        ('MATERIAL', "Textured / Material Preview"),
        ('RENDERED', "Scene Lights / Rendered"),
        ('WIRE_ON_SHADED', "Wireframe on Shaded"),
        ('XRAY', "X-Ray Toggle"),
    )])

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def execute(self, context):
        space = context.space_data
        if self.mode == 'WIRE_ON_SHADED':
            space.overlay.show_wireframes = not space.overlay.show_wireframes
            return {'FINISHED'}
        if self.mode == 'XRAY':
            space.shading.show_xray = not space.shading.show_xray
            return {'FINISHED'}
        space.shading.type = self.mode
        if self.mode == 'RENDERED':
            space.shading.use_scene_lights_render = True
            space.shading.use_scene_world_render = True
        return {'FINISHED'}


class MAYA_STYLE_OT_component(bpy.types.Operator):
    bl_idname = "maya_style.component"
    bl_label = "Selection Mode"
    bl_description = "Choose object, vertex, edge, face, multi-component or UV selection"
    mode: EnumProperty(items=[(value, label, "") for value, label in (
        ('TOGGLE', "Object / Component"),
        ('OBJECT', "Object"),
        ('VERT', "Vertex"),
        ('EDGE', "Edge"),
        ('FACE', "Face"),
        ('MULTI', "Multi-Component (Vert + Edge + Face)"),
        ('UV', "UV"),
    )], default='TOGGLE')

    @classmethod
    def poll(cls, context):
        return _view_poll(context) and context.object is not None

    def execute(self, context):
        if self.mode == 'UV':
            return bpy.ops.maya_style.uv_mode()
        obj = context.object
        if self.mode == 'OBJECT' or (self.mode == 'TOGGLE' and context.mode != 'OBJECT'):
            return bpy.ops.object.mode_set(mode='OBJECT')
        if obj.type != 'MESH':
            if self.mode == 'TOGGLE' and obj.type in {'CURVE', 'SURFACE', 'ARMATURE', 'LATTICE', 'META'}:
                return bpy.ops.object.mode_set(mode='EDIT')
            self.report({'INFO'}, "Vertex, edge and face shortcuts require a mesh")
            return {'CANCELLED'}
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        if self.mode == 'MULTI':
            context.tool_settings.mesh_select_mode = (True, True, True)
        elif self.mode != 'TOGGLE':
            bpy.ops.mesh.select_mode(type=self.mode)
        return {'FINISHED'}


class MAYA_STYLE_OT_uv_mode(bpy.types.Operator):
    bl_idname = "maya_style.uv_mode"
    bl_label = "UV Components"
    bl_description = "Edit UV vertices in the UV Editing workspace; return with the Baya 3D workspace tab"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == 'MESH'

    def execute(self, context):
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        context.scene.tool_settings.use_uv_select_sync = True
        context.scene.tool_settings.uv_select_mode = 'VERTEX'
        workspace = bpy.data.workspaces.get("UV Editing")
        if workspace is not None and context.window is not None:
            context.window.workspace = workspace
        return {'FINISHED'}


class MAYA_STYLE_OT_duplicate(bpy.types.Operator):
    bl_idname = "maya_style.duplicate"
    bl_label = "Duplicate"
    bl_description = "Duplicate selected objects or mesh components in place"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not _view_poll(context):
            return False
        if context.mode == 'OBJECT':
            return bool(context.selected_objects)
        return context.mode == 'EDIT_MESH' and context.object is not None

    def execute(self, context):
        if context.mode == 'EDIT_MESH':
            return bpy.ops.mesh.duplicate()
        return bpy.ops.object.duplicate(linked=False)


class MAYA_STYLE_OT_snap_hold(bpy.types.Operator):
    bl_idname = "maya_style.snap_hold"
    bl_label = "Maya Snap (X: Grid, C: Curve/Edge, V: Point/Vertex)"
    bl_description = "Hold X for Grid Snap, C for Edge/Curve Snap, or V for Vertex Snap; click in UI to toggle"
    mode: EnumProperty(items=[
        ('INCREMENT', "Snap to Grid (X)", "Snap to grid increments"),
        ('GRID', "Snap to Grid (X)", "Snap to grid increments"),
        ('EDGE', "Snap to Curve / Edge (C)", "Snap to edges and curves"),
        ('CURVE', "Snap to Curve / Edge (C)", "Snap to edges and curves"),
        ('VERTEX', "Snap to Point / Vertex (V)", "Snap to vertices and points"),
        ('POINT', "Snap to Point / Vertex (V)", "Snap to vertices and points"),
        ('FACE', "Snap to Face / Live Surface", "Project onto face surfaces"),
    ], default='INCREMENT')
    toggle: BoolProperty(default=False)

    _key_type = 'X'
    _prev_use_snap = False
    _prev_elements = None

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def _target_element(self):
        return {'GRID': 'INCREMENT', 'CURVE': 'EDGE', 'POINT': 'VERTEX'}.get(self.mode, self.mode)

    def execute(self, context):
        ts = context.scene.tool_settings
        elem = self._target_element()
        target_set = {elem} if elem != 'FACE' else {'FACE', 'FACE_PROJECT'}
        if ts.use_snap and ts.snap_elements == target_set:
            ts.use_snap = False
        else:
            ts.use_snap = True
            ts.snap_elements = target_set
        return {'FINISHED'}

    def invoke(self, context, event):
        global _snap_hold_active
        if self.toggle or event.type not in {'X', 'C', 'V'}:
            return self.execute(context)
        if _snap_hold_active:
            return {'PASS_THROUGH'}
        ts = context.scene.tool_settings
        elem = self._target_element()
        self._key_type = event.type
        self._prev_use_snap = bool(ts.use_snap)
        self._prev_elements = set(ts.snap_elements)
        ts.use_snap = True
        ts.snap_elements = {elem}
        _snap_hold_active = True
        labels = {'INCREMENT': "Grid Snap (X)", 'EDGE': "Curve/Edge Snap (C)", 'VERTEX': "Point/Vertex Snap (V)"}
        context.workspace.status_text_set(f"Maya Snap Active: {labels.get(elem, elem)}  |  Release {self._key_type} to restore")
        context.window_manager.modal_handler_add(self)
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _restore(self, context):
        global _snap_hold_active
        _snap_hold_active = False
        ts = context.scene.tool_settings
        ts.use_snap = self._prev_use_snap
        if self._prev_elements:
            ts.snap_elements = self._prev_elements
        context.workspace.status_text_set(None)
        if context.screen:
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()

    def modal(self, context, event):
        if event.type in {'ESC', 'WINDOW_DEACTIVATE'} or (event.type == self._key_type and event.value == 'RELEASE'):
            self._restore(context)
            return {'FINISHED'}
        return {'PASS_THROUGH'}

    def cancel(self, context):
        self._restore(context)


class MAYA_STYLE_OT_pivot_mode(bpy.types.Operator):
    bl_idname = "maya_style.pivot_mode"
    bl_label = "Maya Pivot Controls (D / Insert)"
    bl_description = "Toggle Pivot Edit mode (D / Insert), Center Pivot, or move Pivot to Bottom / World Origin"
    bl_options = {'REGISTER', 'UNDO'}
    action: EnumProperty(items=[
        ('TOGGLE', "Edit Pivot Mode (D / Insert)", "Toggle transform affect-only-origins (Maya Edit Pivot)"),
        ('CENTER', "Center Pivot", "Move object pivot to bounding box center"),
        ('BOTTOM', "Pivot to Bottom", "Move object pivot to the bottom center of its bounding box"),
        ('ORIGIN', "Pivot to World Origin (0,0,0)", "Move object pivot to the world origin"),
        ('CURSOR', "Pivot to 3D Cursor", "Move object pivot to the 3D cursor"),
        ('RESET_POS', "Reset Pivot Position", "Center pivot on geometry"),
    ], default='TOGGLE')

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def execute(self, context):
        ts = context.scene.tool_settings
        if self.action == 'TOGGLE':
            ts.use_transform_data_origin = not ts.use_transform_data_origin
            if ts.use_transform_data_origin:
                if context.mode == 'OBJECT':
                    try:
                        bpy.ops.wm.tool_set_by_id(name="builtin.move", cycle=False)
                    except RuntimeError:
                        pass
                context.workspace.status_text_set("Maya Pivot Edit Mode: ON  |  Use W/E to move/orient pivot  |  Press D or Insert to exit")
            else:
                context.workspace.status_text_set(None)
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.tag_redraw()
            return {'FINISHED'}

        if context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if not context.selected_editable_objects:
            self.report({'WARNING'}, "Select an editable object first")
            return {'CANCELLED'}

        if self.action in {'CENTER', 'RESET_POS'}:
            return bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

        if self.action == 'CURSOR':
            return bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        saved_cursor = context.scene.cursor.location.copy()
        try:
            if self.action == 'ORIGIN':
                context.scene.cursor.location = (0.0, 0.0, 0.0)
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            elif self.action == 'BOTTOM':
                for obj in list(context.selected_editable_objects):
                    if not obj.bound_box:
                        continue
                    world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
                    xs = [pt.x for pt in world_corners]
                    ys = [pt.y for pt in world_corners]
                    zs = [pt.z for pt in world_corners]
                    bottom_center = Vector(((min(xs) + max(xs)) * 0.5, (min(ys) + max(ys)) * 0.5, min(zs)))
                    context.scene.cursor.location = bottom_center
                    with context.temp_override(selected_editable_objects=[obj], selected_objects=[obj], active_object=obj, object=obj):
                        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        finally:
            context.scene.cursor.location = saved_cursor
        return {'FINISHED'}


class MAYA_STYLE_OT_poly_action(bpy.types.Operator):
    bl_idname = "maya_style.poly_action"
    bl_label = "Maya Polygon / Scene Operation"
    bl_description = "Execute a Maya-equivalent polygon, history, transform, hierarchy or selection action"
    bl_options = {'REGISTER', 'UNDO'}
    action: EnumProperty(items=[
        ('COMBINE', "Combine", "Combine selected polygon meshes into one mesh"),
        ('SEPARATE', "Separate", "Separate loose mesh shells or selected faces into objects"),
        ('EXTRACT_FACES', "Extract Faces", "Separate selected faces into a new mesh object"),
        ('DUPLICATE_FACES', "Duplicate Faces", "Duplicate selected faces as a new mesh shell"),
        ('DELETE_HISTORY', "Delete by Type > History", "Apply construction modifiers while preserving smooth preview"),
        ('FREEZE_ALL', "Freeze Transformations", "Apply location, rotation and scale to object geometry"),
        ('RESET_TRANSFORMS', "Reset Transformations", "Reset location and rotation to 0 and scale to 1"),
        ('CENTER_PIVOT', "Center Pivot", "Move pivot to bounding-box center"),
        ('FILL_HOLE', "Fill Hole", "Fill boundary holes on the mesh"),
        ('BRIDGE', "Bridge", "Bridge selected edge loops or faces"),
        ('POKE_FACES', "Poke", "Poke selected faces from their center"),
        ('POKE', "Poke", "Poke selected faces from their center"),
        ('TRIANGULATE', "Triangulate", "Convert selected faces to triangles"),
        ('QUADRANGULATE', "Quadrangulate", "Convert triangles to quads"),
        ('CIRCULARIZE', "Circularize", "Round selected vertices, edges or faces into a circle"),
        ('REVERSE_NORMALS', "Reverse Normals", "Flip polygon face normals"),
        ('CONFORM_NORMALS', "Conform Normals", "Recalculate polygon normals consistently outside"),
        ('SOFTEN_EDGE', "Soften Edge", "Clear sharp edges and set smooth shading"),
        ('HARDEN_EDGE', "Harden Edge", "Mark sharp edges or set flat shading"),
        ('BOOLEAN_UNION', "Boolean Union", "Union selected meshes"),
        ('BOOLEAN_DIFFERENCE', "Boolean Difference", "Subtract active/second mesh from first mesh"),
        ('BOOLEAN_INTERSECT', "Boolean Intersection", "Intersect selected meshes"),
        ('MIRROR_X', "Mirror X", "Mirror mesh across X axis with clipping"),
        ('MIRROR_Y', "Mirror Y", "Mirror mesh across Y axis with clipping"),
        ('MIRROR_Z', "Mirror Z", "Mirror mesh across Z axis with clipping"),
        ('SMOOTH_MESH', "Smooth (Subdivide)", "Subdivide mesh geometry with smoothing"),
        ('REDUCE_MESH', "Reduce (Decimate)", "Add a Decimate modifier to reduce polygon count"),
        ('REDUCE', "Reduce (Decimate)", "Add a Decimate modifier to reduce polygon count"),
        ('REMESH', "Remesh", "Apply or add a Voxel Remesh modifier"),
        ('GROUP', "Group (Ctrl+G)", "Group selected objects under a new null/empty node"),
        ('UNGROUP', "Ungroup", "Unparent children of the selected group node, keeping transforms"),
        ('LOCATOR', "Create Locator", "Create a Maya-style Locator (Empty axes)"),
        ('SOFT_SELECT_TOGGLE', "Soft Selection Toggle (B)", "Toggle proportional editing (Maya Soft Selection)"),
        ('CONVERT_TO_VERTICES', "Convert Selection to Vertices", "Convert current component selection to vertices"),
        ('CONVERT_TO_VERTS', "Convert Selection to Vertices", "Convert current component selection to vertices"),
        ('CONVERT_TO_EDGES', "Convert Selection to Edges", "Convert current component selection to edges"),
        ('CONVERT_TO_FACES', "Convert Selection to Faces", "Convert current component selection to faces"),
        ('DELETE_EDGE_VERTEX', "Delete Edge / Vertex", "Dissolve selected edges and their leftover vertices"),
    ], default='DELETE_HISTORY')

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def execute(self, context):
        act = {
            'POKE': 'POKE_FACES',
            'REDUCE': 'REDUCE_MESH',
            'CONVERT_TO_VERTS': 'CONVERT_TO_VERTICES',
        }.get(self.action, self.action)
        if act == 'LOCATOR':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.empty_add(type='PLAIN_AXES')
            if context.active_object:
                context.active_object.name = "locator1"
            return {'FINISHED'}

        if act == 'SOFT_SELECT_TOGGLE':
            ts = context.scene.tool_settings
            if context.mode == 'OBJECT':
                ts.use_proportional_edit_objects = not ts.use_proportional_edit_objects
            else:
                ts.use_proportional_edit = not ts.use_proportional_edit
            return {'FINISHED'}

        if act == 'GROUP':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            selected = list(context.selected_objects)
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0.0, 0.0, 0.0))
            group_obj = context.active_object
            group_obj.name = "group1"
            for obj in selected:
                if obj != group_obj:
                    mat = obj.matrix_world.copy()
                    obj.parent = group_obj
                    obj.matrix_world = mat
            for obj in context.selected_objects:
                obj.select_set(False)
            group_obj.select_set(True)
            context.view_layer.objects.active = group_obj
            return {'FINISHED'}

        if act == 'UNGROUP':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            children = []
            for obj in list(context.selected_objects):
                for child in list(obj.children):
                    mat = child.matrix_world.copy()
                    child.parent = obj.parent
                    child.matrix_world = mat
                    children.append(child)
                if obj.type == 'EMPTY' and not obj.children:
                    bpy.data.objects.remove(obj, do_unlink=True)
            for child in children:
                child.select_set(True)
            if children:
                context.view_layer.objects.active = children[0]
            return {'FINISHED'}

        obj = context.object
        if obj is None:
            self.report({'WARNING'}, "Select an object first")
            return {'CANCELLED'}

        if act == 'CENTER_PIVOT':
            return bpy.ops.maya_style.pivot_mode(action='CENTER')

        if act == 'FREEZE_ALL':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            return bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        if act == 'RESET_TRANSFORMS':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            for item in context.selected_editable_objects:
                item.location = (0.0, 0.0, 0.0)
                item.rotation_euler = (0.0, 0.0, 0.0)
                item.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
                item.scale = (1.0, 1.0, 1.0)
            return {'FINISHED'}

        if act == 'DELETE_HISTORY':
            was_edit = context.mode == 'EDIT_MESH'
            if was_edit:
                bpy.ops.object.mode_set(mode='OBJECT')
            applied = 0
            for item in context.selected_editable_objects:
                if item.type != 'MESH':
                    continue
                preview_uids = {item.get(_PREVIEW_UID), item.get(_NORMALS_UID)}
                for mod in list(item.modifiers):
                    if str(mod.persistent_uid) in preview_uids:
                        continue
                    try:
                        with context.temp_override(object=item, active_object=item):
                            bpy.ops.object.modifier_apply(modifier=mod.name)
                            applied += 1
                    except RuntimeError:
                        pass
            if was_edit:
                bpy.ops.object.mode_set(mode='EDIT')
            self.report({'INFO'}, f"Construction history cleared ({applied} modifier(s) baked)")
            return {'FINISHED'}

        if act == 'COMBINE':
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            meshes = [item for item in context.selected_editable_objects if item.type == 'MESH']
            if len(meshes) < 2:
                self.report({'WARNING'}, "Select at least two polygon meshes to Combine")
                return {'CANCELLED'}
            if context.view_layer.objects.active not in meshes:
                context.view_layer.objects.active = meshes[-1]
            return bpy.ops.object.join()

        if act == 'SEPARATE':
            if obj.type != 'MESH':
                return {'CANCELLED'}
            if context.mode == 'EDIT_MESH':
                return bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        if act == 'EXTRACT_FACES':
            if obj.type != 'MESH':
                return {'CANCELLED'}
            if context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        if act == 'DUPLICATE_FACES':
            if obj.type != 'MESH':
                return {'CANCELLED'}
            if context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        if act in {'BOOLEAN_UNION', 'BOOLEAN_DIFFERENCE', 'BOOLEAN_INTERSECT'}:
            if context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            meshes = [item for item in context.selected_editable_objects if item.type == 'MESH']
            if len(meshes) < 2:
                self.report({'WARNING'}, "Select at least two meshes for Boolean operation")
                return {'CANCELLED'}
            active = context.active_object if context.active_object in meshes else meshes[0]
            cutters = [m for m in meshes if m != active]
            op_map = {
                'BOOLEAN_UNION': 'UNION',
                'BOOLEAN_DIFFERENCE': 'DIFFERENCE',
                'BOOLEAN_INTERSECT': 'INTERSECT',
            }
            for cutter in cutters:
                mod = active.modifiers.new(name=f"Baya_{op_map[act].title()}", type='BOOLEAN')
                mod.operation = op_map[act]
                mod.object = cutter
                cutter.display_type = 'WIRE'
                cutter.hide_render = True
            return {'FINISHED'}

        if act in {'MIRROR_X', 'MIRROR_Y', 'MIRROR_Z'}:
            if obj.type != 'MESH':
                return {'CANCELLED'}
            mod = obj.modifiers.new(name="Baya_Mirror", type='MIRROR')
            axis_idx = {'MIRROR_X': 0, 'MIRROR_Y': 1, 'MIRROR_Z': 2}[act]
            mod.use_axis = (axis_idx == 0, axis_idx == 1, axis_idx == 2)
            mod.use_bisect_axis = (axis_idx == 0, axis_idx == 1, axis_idx == 2)
            mod.use_clip = True
            return {'FINISHED'}

        if act == 'REDUCE_MESH':
            if obj.type != 'MESH':
                return {'CANCELLED'}
            mod = obj.modifiers.new(name="Baya_Reduce", type='DECIMATE')
            mod.ratio = 0.5
            return {'FINISHED'}

        if act == 'REMESH':
            if obj.type != 'MESH':
                return {'CANCELLED'}
            mod = obj.modifiers.new(name="Baya_Remesh", type='REMESH')
            mod.voxel_size = 0.1
            return {'FINISHED'}

        if act == 'SMOOTH_MESH':
            if obj.type != 'MESH':
                return {'CANCELLED'}
            was_object = context.mode == 'OBJECT'
            if was_object:
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.subdivide(number_cuts=1, smoothness=1.0)
            if was_object:
                bpy.ops.object.mode_set(mode='OBJECT')
            return {'FINISHED'}

        if act in {'CONVERT_TO_VERTICES', 'CONVERT_TO_EDGES', 'CONVERT_TO_FACES'}:
            if obj.type != 'MESH':
                return {'CANCELLED'}
            if context.mode != 'EDIT_MESH':
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
            target = {
                'CONVERT_TO_VERTICES': 'VERT',
                'CONVERT_TO_EDGES': 'EDGE',
                'CONVERT_TO_FACES': 'FACE',
            }[act]
            bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type=target)
            return {'FINISHED'}

        if obj.type != 'MESH':
            return {'CANCELLED'}

        was_object = context.mode == 'OBJECT'
        if was_object and act in {'FILL_HOLE', 'REVERSE_NORMALS', 'CONFORM_NORMALS', 'SOFTEN_EDGE', 'HARDEN_EDGE', 'TRIANGULATE', 'QUADRANGULATE', 'POKE_FACES'}:
            if act == 'SOFTEN_EDGE':
                return bpy.ops.object.shade_smooth()
            if act == 'HARDEN_EDGE':
                return bpy.ops.object.shade_flat()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')

        try:
            if act == 'FILL_HOLE':
                bpy.ops.mesh.edge_face_add()
            elif act == 'BRIDGE':
                bpy.ops.mesh.bridge_edge_loops()
            elif act == 'POKE_FACES':
                bpy.ops.mesh.poke()
            elif act == 'TRIANGULATE':
                bpy.ops.mesh.quads_convert_to_tris()
            elif act == 'QUADRANGULATE':
                bpy.ops.mesh.tris_convert_to_quads()
            elif act == 'CIRCULARIZE':
                bpy.ops.transform.tosphere(value=1.0)
            elif act == 'REVERSE_NORMALS':
                bpy.ops.mesh.flip_normals()
            elif act == 'CONFORM_NORMALS':
                bpy.ops.mesh.normals_make_consistent(inside=False)
            elif act == 'SOFTEN_EDGE':
                bpy.ops.mesh.mark_sharp(clear=True)
                bpy.ops.mesh.faces_shade_smooth()
            elif act == 'HARDEN_EDGE':
                bpy.ops.mesh.mark_sharp(clear=False)
            elif act == 'DELETE_EDGE_VERTEX':
                bpy.ops.mesh.dissolve_edges(use_verts=True)
        except RuntimeError as exc:
            self.report({'WARNING'}, str(exc))
            if was_object and context.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')
            return {'CANCELLED'}

        if was_object and context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


class MAYA_STYLE_OT_assign_shader(bpy.types.Operator):
    bl_idname = "maya_style.assign_shader"
    bl_label = "Assign Maya-Style Material"
    bl_description = "Create and assign a Maya-equivalent shader (Standard Surface, Lambert, Blinn, Phong, Surface Shader)"
    bl_options = {'REGISTER', 'UNDO'}
    shader_type: EnumProperty(items=[
        ('STANDARD_SURFACE', "Standard Surface", "Modern PBR surface shader"),
        ('LAMBERT', "Lambert", "Matte diffuse surface shader with no specular highlight"),
        ('BLINN', "Blinn", "Soft metallic/glossy highlight shader"),
        ('PHONG', "Phong", "Sharp glossy highlight shader"),
        ('SURFACE_SHADER', "Surface Shader", "Unlit flat emission surface shader"),
    ], default='STANDARD_SURFACE')

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type in {'MESH', 'CURVE', 'SURFACE', 'FONT', 'META'}

    def execute(self, context):
        presets = {
            'STANDARD_SURFACE': ("standardSurface1", (0.8, 0.8, 0.8, 1.0), 0.25, 0.0, 0.5),
            'LAMBERT': ("lambert1", (0.5, 0.5, 0.5, 1.0), 1.0, 0.0, 0.0),
            'BLINN': ("blinn1", (0.6, 0.6, 0.65, 1.0), 0.35, 0.15, 0.6),
            'PHONG': ("phong1", (0.7, 0.7, 0.75, 1.0), 0.12, 0.0, 0.8),
            'SURFACE_SHADER': ("surfaceShader1", (0.9, 0.9, 0.9, 1.0), 1.0, 0.0, 0.0),
        }
        base_name, color, roughness, metallic, spec = presets[self.shader_type]
        mat = bpy.data.materials.new(name=base_name)
        mat.use_nodes = True
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is not None:
            bsdf.inputs['Base Color'].default_value = color
            bsdf.inputs['Roughness'].default_value = roughness
            bsdf.inputs['Metallic'].default_value = metallic
            if 'Specular IOR Level' in bsdf.inputs:
                bsdf.inputs['Specular IOR Level'].default_value = spec
            if self.shader_type == 'SURFACE_SHADER' and 'Emission Color' in bsdf.inputs:
                bsdf.inputs['Emission Color'].default_value = color
                if 'Emission Strength' in bsdf.inputs:
                    bsdf.inputs['Emission Strength'].default_value = 1.0

        targets = [o for o in context.selected_editable_objects if hasattr(o.data, 'materials')] or [context.object]
        for obj in targets:
            if not obj.data.materials:
                obj.data.materials.append(mat)
            elif context.mode == 'EDIT_MESH' and obj == context.object:
                obj.data.materials.append(mat)
                obj.active_material_index = len(obj.data.materials) - 1
                bpy.ops.object.material_slot_assign()
            else:
                obj.data.materials[obj.active_material_index] = mat
        return {'FINISHED'}


class MAYA_STYLE_OT_command_exec(bpy.types.Operator):
    bl_idname = "maya_style.command_exec"
    bl_label = "Execute MEL / Python Command"
    bl_description = "Execute the command in Baya's bottom command bar (supports common MEL commands and Python)"
    bl_options = {'REGISTER', 'UNDO'}
    command: StringProperty(default="")
    language: StringProperty(default="MEL")

    def execute(self, context):
        state = getattr(context.scene, "maya_style", None)
        raw = (self.command or (state.command_input if state else "")).strip()
        if not raw:
            self.report({'INFO'}, "Enter a MEL or Python command first (e.g., polyCube, polySphere, FreezeTransformations)")
            return {'CANCELLED'}

        cmd_clean = raw.rstrip(";").strip()
        head = cmd_clean.split()[0] if cmd_clean.split() else ""
        mel_map = {
            "polyCube": lambda: bpy.ops.mesh.primitive_cube_add(),
            "CreatePolygonCube": lambda: bpy.ops.mesh.primitive_cube_add(),
            "polySphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(),
            "CreatePolygonSphere": lambda: bpy.ops.mesh.primitive_uv_sphere_add(),
            "polyCylinder": lambda: bpy.ops.mesh.primitive_cylinder_add(),
            "CreatePolygonCylinder": lambda: bpy.ops.mesh.primitive_cylinder_add(),
            "polyCone": lambda: bpy.ops.mesh.primitive_cone_add(),
            "CreatePolygonCone": lambda: bpy.ops.mesh.primitive_cone_add(),
            "polyPlane": lambda: bpy.ops.mesh.primitive_plane_add(),
            "CreatePolygonPlane": lambda: bpy.ops.mesh.primitive_plane_add(),
            "polyTorus": lambda: bpy.ops.mesh.primitive_torus_add(),
            "CreatePolygonTorus": lambda: bpy.ops.mesh.primitive_torus_add(),
            "circle": lambda: bpy.ops.curve.primitive_nurbs_circle_add(),
            "spaceLocator": lambda: bpy.ops.maya_style.poly_action(action='LOCATOR'),
            "CreateLocator": lambda: bpy.ops.maya_style.poly_action(action='LOCATOR'),
            "CenterPivot": lambda: bpy.ops.maya_style.poly_action(action='CENTER_PIVOT'),
            "DeleteHistory": lambda: bpy.ops.maya_style.poly_action(action='DELETE_HISTORY'),
            "FreezeTransformations": lambda: bpy.ops.maya_style.poly_action(action='FREEZE_ALL'),
            "ResetTransformations": lambda: bpy.ops.maya_style.poly_action(action='RESET_TRANSFORMS'),
            "CombinePolygons": lambda: bpy.ops.maya_style.poly_action(action='COMBINE'),
            "polyUnite": lambda: bpy.ops.maya_style.poly_action(action='COMBINE'),
            "SeparatePolygon": lambda: bpy.ops.maya_style.poly_action(action='SEPARATE'),
            "polySeparate": lambda: bpy.ops.maya_style.poly_action(action='SEPARATE'),
            "polyExtrudeFacet": lambda: bpy.ops.mesh.extrude_region_move(),
            "PolyExtrude": lambda: bpy.ops.mesh.extrude_region_move(),
            "polyBevel3": lambda: bpy.ops.mesh.bevel(),
            "BevelPolygon": lambda: bpy.ops.mesh.bevel(),
            "polySmooth": lambda: bpy.ops.maya_style.poly_action(action='SMOOTH_MESH'),
            "SmoothPolygon": lambda: bpy.ops.maya_style.poly_action(action='SMOOTH_MESH'),
            "FillHole": lambda: bpy.ops.maya_style.poly_action(action='FILL_HOLE'),
            "group": lambda: bpy.ops.maya_style.poly_action(action='GROUP'),
            "ungroup": lambda: bpy.ops.maya_style.poly_action(action='UNGROUP'),
            "duplicate": lambda: bpy.ops.maya_style.duplicate(),
            "SelectAll": lambda: bpy.ops.object.select_all(action='SELECT') if context.mode == 'OBJECT' else bpy.ops.mesh.select_all(action='SELECT'),
        }

        try:
            if head in mel_map:
                mel_map[head]()
                msg = f"Result: {head}"
            elif cmd_clean.startswith("select"):
                if "-cl" in cmd_clean or "-clear" in cmd_clean:
                    if context.mode == 'OBJECT':
                        bpy.ops.object.select_all(action='DESELECT')
                    else:
                        bpy.ops.mesh.select_all(action='DESELECT')
                    msg = "Result: selection cleared"
                else:
                    if context.mode == 'OBJECT':
                        bpy.ops.object.select_all(action='SELECT')
                    else:
                        bpy.ops.mesh.select_all(action='SELECT')
                    msg = "Result: selected all"
            elif cmd_clean.startswith("bpy."):
                tree = ast.parse(cmd_clean, mode='eval')
                if not isinstance(tree.body, ast.Call):
                    raise ValueError("Only bpy.ops.* calls or MEL commands are supported")
                node = tree.body.func
                parts = []
                while isinstance(node, ast.Attribute):
                    parts.append(node.attr)
                    node = node.value
                if isinstance(node, ast.Name):
                    parts.append(node.id)
                parts.reverse()
                if len(parts) != 4 or parts[0] != "bpy" or parts[1] != "ops":
                    raise ValueError("Only bpy.ops.<category>.<operator>(...) is allowed")
                op_mod = getattr(bpy.ops, parts[2])
                op_fn = getattr(op_mod, parts[3])
                kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in tree.body.keywords if kw.arg}
                res = op_fn(**kwargs)
                msg = f"Result: {res}"
            else:
                self.report({'WARNING'}, f"Unrecognized command '{head}'. Try MEL (polyCube, FreezeTransformations, DeleteHistory) or bpy.ops.*")
                return {'CANCELLED'}
        except Exception as exc:
            if state is not None and hasattr(state, 'last_command_result'):
                state.last_command_result = f"Error: {exc}"
            self.report({'WARNING'}, f"Command error: {exc}")
            return {'CANCELLED'}

        if state is not None and hasattr(state, 'last_command_result'):
            state.last_command_result = msg
        self.report({'INFO'}, f"// {msg} //")
        return {'FINISHED'}


class MAYA_STYLE_MT_assign_material(bpy.types.Menu):
    bl_label = "Assign New Material"
    bl_idname = "MAYA_STYLE_MT_assign_material"

    def draw(self, context):
        lay = self.layout
        for stype, label, icon in [
            ('STANDARD_SURFACE', "Standard Surface", 'SHADING_RENDERED'),
            ('LAMBERT', "Lambert (Matte)", 'SHADING_SOLID'),
            ('BLINN', "Blinn (Soft Specular)", 'MATERIAL'),
            ('PHONG', "Phong (Sharp Specular)", 'NODE_MATERIAL'),
            ('SURFACE_SHADER', "Surface Shader (Unlit)", 'LIGHT_SUN'),
        ]:
            lay.operator("maya_style.assign_shader", text=label, icon=icon).shader_type = stype


class MAYA_STYLE_MT_normals(bpy.types.Menu):
    bl_label = "Normals / Soften-Harden"
    bl_idname = "MAYA_STYLE_MT_normals"

    def draw(self, context):
        lay = self.layout
        lay.operator("maya_style.poly_action", text="Soften Edge (Smooth)", icon='SHADING_SOLID').action = 'SOFTEN_EDGE'
        lay.operator("maya_style.poly_action", text="Harden Edge (Sharp)", icon='MOD_EDGESPLIT').action = 'HARDEN_EDGE'
        lay.separator()
        lay.operator("maya_style.poly_action", text="Reverse Normals", icon='FILE_REFRESH').action = 'REVERSE_NORMALS'
        lay.operator("maya_style.poly_action", text="Conform Normals", icon='CHECKMARK').action = 'CONFORM_NORMALS'


class MAYA_STYLE_MT_components(bpy.types.Menu):
    bl_label = "Selection Marking Menu"

    def draw(self, context):
        pie = self.layout.menu_pie()
        if context.scene and context.scene.tool_settings.use_transform_data_origin:
            # Matches Maya buildObjectMenuItemsNow.mel when in Edit Pivot mode
            pie.operator("maya_style.pivot_mode", text="Pivot to Bottom", icon='TRIA_DOWN').action = 'BOTTOM'
            pie.operator("maya_style.pivot_mode", text="Exit Pivot Mode  D", icon='CHECKMARK').action = 'TOGGLE'
            pie.operator("maya_style.pivot_mode", text="Center Pivot", icon='PIVOT_MEDIAN').action = 'CENTER'
            pie.operator("maya_style.pivot_mode", text="Pivot to Origin (0,0,0)", icon='OBJECT_ORIGIN').action = 'ORIGIN'
            pie.operator("maya_style.pivot_mode", text="Pivot to 3D Cursor", icon='PIVOT_CURSOR').action = 'CURSOR'
            pie.operator("maya_style.poly_action", text="Freeze Transformations", icon='FREEZE').action = 'FREEZE_ALL'
            pie.operator("maya_style.poly_action", text="Reset Transformations", icon='LOOP_BACK').action = 'RESET_TRANSFORMS'
            pie.operator("view3d.view_selected", text="Frame Selection  F")
            return

        for label, mode in (
            ("Vertex  F9", 'VERT'),
            ("Edge  F10", 'EDGE'),
            ("Object Mode  F8", 'OBJECT'),
            ("Face  F11", 'FACE'),
        ):
            pie.operator("maya_style.component", text=label).mode = mode
        pie.operator("maya_style.component", text="Multi-Component").mode = 'MULTI'
        pie.operator("maya_style.uv_mode", text="UV  F12")
        pie.menu("MAYA_STYLE_MT_assign_material", text="Assign New Material", icon='MATERIAL')
        menu = "VIEW3D_MT_edit_mesh_context_menu" if context.mode == 'EDIT_MESH' else "VIEW3D_MT_object_context_menu"
        pie.menu(menu, text="Context / Actions")


class MAYA_STYLE_MT_create(bpy.types.Menu):
    bl_label = "Create Marking Menu"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("mesh.primitive_cube_add", text="Cube", icon='MESH_CUBE')
        pie.operator("mesh.primitive_uv_sphere_add", text="Sphere", icon='MESH_UVSPHERE')
        pie.operator("mesh.primitive_plane_add", text="Plane", icon='MESH_PLANE')
        pie.operator("mesh.primitive_cylinder_add", text="Cylinder", icon='MESH_CYLINDER')
        pie.operator("mesh.primitive_cone_add", text="Cone", icon='MESH_CONE')
        pie.operator("mesh.primitive_torus_add", text="Torus", icon='MESH_TORUS')
        pie.menu("VIEW3D_MT_add", text="All Create Commands", icon='ADD')
        pie.operator("mesh.primitive_circle_add", text="Circle / Disc", icon='MESH_CIRCLE')


class MAYA_STYLE_MT_context_tools(bpy.types.Menu):
    """Context-sensitive Shift+RMB Poly Tools Marking Menu (matches Maya contextPolyToolsMM.mel)."""
    bl_label = "Context Poly Tools Marking Menu"
    bl_idname = "MAYA_STYLE_MT_context_tools"

    def draw(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            MAYA_STYLE_MT_create.draw(self, context)
            return

        pie = self.layout.menu_pie()
        if context.mode != 'EDIT_MESH':
            # Object Mode Mesh Marking Menu (matches contextPolyToolsObjectMM.mel)
            pie.operator("mesh.knife_tool" if context.mode == 'EDIT_MESH' else "maya_style.component",
                         text="Multi-Cut / Component Mode", icon='MOD_TRIANGULATE').mode = 'EDGE' if context.mode != 'EDIT_MESH' else 'EDGE'
            pie.operator("maya_style.poly_action", text="Smooth Mesh", icon='MOD_SUBSURF').action = 'SMOOTH_MESH'
            pie.operator("maya_style.poly_action", text="Combine Meshes", icon='AUTOMERGE_ON').action = 'COMBINE'
            pie.operator("maya_style.poly_action", text="Delete History", icon='CHECKMARK').action = 'DELETE_HISTORY'
            pie.operator("maya_style.poly_action", text="Mirror X", icon='MOD_MIRROR').action = 'MIRROR_X'
            pie.operator("maya_style.poly_action", text="Separate Shells", icon='MOD_EXPLODE').action = 'SEPARATE'
            pie.operator("maya_style.poly_action", text="Boolean Difference", icon='MOD_BOOLEAN').action = 'BOOLEAN_DIFFERENCE'
            pie.menu("MAYA_STYLE_MT_normals", text="Soften / Harden Edge", icon='NORMALS_FACE')
            return

        sel_mode = context.tool_settings.mesh_select_mode
        if sel_mode[2]:
            # Face Mode (matches contextPolyToolsFaceMM.mel)
            pie.operator("mesh.knife_tool", text="Multi-Cut / Knife", icon='MOD_TRIANGULATE')
            pie.operator("mesh.bevel", text="Bevel Face", icon='MOD_BEVEL')
            pie.operator("mesh.extrude_region_move", text="Extrude Face  Ctrl+E", icon='MOD_SOLIDIFY')
            pie.operator("mesh.merge", text="Merge to Center", icon='AUTOMERGE_ON').type = 'CENTER'
            pie.operator("maya_style.poly_action", text="Extract / Separate Faces", icon='MOD_EXPLODE').action = 'EXTRACT_FACES'
            pie.operator("mesh.poke", text="Poke Face", icon='VERTEXSEL')
            pie.operator("mesh.inset", text="Inset / Wedge Face", icon='FACESEL')
            pie.menu("MAYA_STYLE_MT_normals", text="Face Normals", icon='NORMALS_FACE')
        elif sel_mode[1]:
            # Edge Mode (matches contextPolyToolsEdgeMM.mel)
            pie.operator("mesh.knife_tool", text="Multi-Cut / Knife", icon='MOD_TRIANGULATE')
            pie.operator("mesh.bevel", text="Bevel Edge", icon='MOD_BEVEL')
            pie.operator("mesh.extrude_region_move", text="Extrude Edge  Ctrl+E", icon='MOD_SOLIDIFY')
            pie.operator("mesh.bridge_edge_loops", text="Bridge Edges", icon='EDGESEL')
            pie.operator("mesh.loopcut_slide", text="Insert Edge Loop", icon='MOD_EDGESPLIT')
            pie.operator("maya_style.poly_action", text="Fill Hole", icon='FACESEL').action = 'FILL_HOLE'
            pie.operator("maya_style.poly_action", text="Delete Edge/Vertex", icon='X').action = 'DELETE_EDGE_VERTEX'
            pie.menu("MAYA_STYLE_MT_normals", text="Soften / Harden Edge", icon='NORMALS_FACE')
        else:
            # Vertex Mode (matches contextPolyToolsVertexMM.mel)
            pie.operator("mesh.knife_tool", text="Multi-Cut / Knife", icon='MOD_TRIANGULATE')
            op = pie.operator("mesh.bevel", text="Chamfer Vertex", icon='MOD_BEVEL')
            op.affect = 'VERTICES'
            pie.operator("mesh.extrude_verts_indiv", text="Extrude Vertex", icon='VERTEXSEL')
            pie.operator("mesh.merge", text="Merge to Center", icon='AUTOMERGE_ON').type = 'CENTER'
            pie.operator("mesh.vert_connect_path", text="Connect Vertices", icon='EDGESEL')
            pie.operator("mesh.vertices_smooth", text="Average Vertices", icon='SMOOTHCURVE')
            pie.operator("mesh.dissolve_verts", text="Delete Vertex", icon='X')
            pie.operator("mesh.remove_doubles", text="Merge by Distance", icon='AUTOMERGE_ON')


class MAYA_STYLE_MT_convert_selection(bpy.types.Menu):
    """Ctrl+RMB Selection Conversion Marking Menu."""
    bl_label = "Convert Selection Marking Menu"
    bl_idname = "MAYA_STYLE_MT_convert_selection"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.operator("maya_style.poly_action", text="To Vertices", icon='VERTEXSEL').action = 'CONVERT_TO_VERTICES'
        pie.operator("mesh.loop_multi_select", text="To Edge Loop", icon='EDGESEL').ring = False
        pie.operator("maya_style.poly_action", text="To Faces", icon='FACESEL').action = 'CONVERT_TO_FACES'
        pie.operator("maya_style.poly_action", text="To Edges", icon='EDGESEL').action = 'CONVERT_TO_EDGES'
        pie.operator("mesh.select_linked", text="To UV / Mesh Shell", icon='UV_ISLANDSEL')
        pie.operator("mesh.loop_multi_select", text="To Edge Ring", icon='EDGESEL').ring = True
        pie.operator("mesh.select_less", text="Shrink Selection  <", icon='REMOVE')
        pie.operator("mesh.select_more", text="Grow Selection  >", icon='ADD')


class MAYA_STYLE_MT_hotbox(bpy.types.Menu):
    bl_label = "Baya 3D Hotbox"

    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.menu("MAYA_STYLE_MT_display", text="Display / View")
        pie.menu("MAYA_STYLE_MT_shelf_create", text="Create")
        pie.operator("screen.region_quadview", text="Single / Four Views  Space")
        pie.operator("wm.call_menu_pie", text="Selection  RMB").name = "MAYA_STYLE_MT_components"
        pie.menu("TOPBAR_MT_file", text="File")
        pie.menu("MAYA_STYLE_MT_modify", text="Modify")
        pie.menu("MAYA_STYLE_MT_mesh", text="Mesh / Edit Mesh")
        pie.menu("MAYA_STYLE_MT_windows", text="Windows / Menu Sets")


class MAYA_STYLE_OT_hotbox(bpy.types.Operator):
    bl_idname = "maya_style.hotbox"
    bl_label = "Space: Four Views / Hotbox"
    bl_description = "Tap Space to toggle four views; hold Space for the hotbox pie menu"
    _timer = None
    _started = 0.0
    _opened_pie = False

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def _cleanup(self, context):
        global _hotbox_active
        _hotbox_active = False
        if self._timer is not None:
            try:
                context.window_manager.event_timer_remove(self._timer)
            except Exception:
                pass
            self._timer = None
        if context.workspace:
            context.workspace.status_text_set(None)

    def invoke(self, context, event):
        global _hotbox_active
        if _hotbox_active or getattr(event, "is_repeat", False):
            return {'CANCELLED'}
        _hotbox_active = True
        self._opened_pie = False
        self._started = time.monotonic()
        self._timer = context.window_manager.event_timer_add(0.04, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'WINDOW_DEACTIVATE'}:
            self._cleanup(context)
            return {'CANCELLED'}
        if event.type == 'SPACE' and event.value == 'RELEASE':
            opened = self._opened_pie
            self._cleanup(context)
            if not opened:
                return bpy.ops.screen.region_quadview()
            return {'FINISHED'}
        if event.type == 'TIMER' and not self._opened_pie and time.monotonic() - self._started >= 0.20:
            self._opened_pie = True
            self._cleanup(context)
            bpy.ops.wm.call_menu_pie('INVOKE_DEFAULT', name="MAYA_STYLE_MT_hotbox")
            return {'FINISHED'}
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        self._cleanup(context)


class MAYA_STYLE_OT_scrub(bpy.types.Operator):
    bl_idname = "maya_style.scrub"
    bl_label = "Scrub Timeline"
    bl_description = "Hold K and drag the middle mouse button to scrub; release K to finish"
    _dragging = False

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def invoke(self, context, event):
        self._dragging = False
        self._original = context.scene.frame_current
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set("K + middle mouse drag: scrub  |  Release K: finish  |  Esc: cancel")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        cancelled = event.type == 'ESC' or (event.type == 'RIGHTMOUSE' and event.value == 'PRESS')
        if cancelled or event.type == 'WINDOW_DEACTIVATE' or (event.type == 'K' and event.value == 'RELEASE'):
            if cancelled:
                context.scene.frame_set(self._original)
            context.workspace.status_text_set(None)
            return {'CANCELLED'} if cancelled else {'FINISHED'}
        if event.type == 'MIDDLEMOUSE':
            self._dragging = event.value == 'PRESS'
            self._anchor_x = event.mouse_x
            self._anchor_frame = context.scene.frame_current
        if event.type == 'MOUSEMOVE' and self._dragging:
            frame = self._anchor_frame + round((event.mouse_x - self._anchor_x) / 8)
            context.scene.frame_set(max(-1048574, min(1048574, frame)))
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        context.scene.frame_set(self._original)
        context.workspace.status_text_set(None)


def _item(operator, key, properties=None, **event):
    return (operator, {"type": key, "value": 'PRESS', **event},
            {"properties": list((properties or {}).items())} if properties else None)


def keyconfig_data():
    """Fresh complete keymap data, removing collisions before overlaying controls."""
    path = os.path.join(bpy.utils.system_resource('SCRIPTS'), "presets", "keyconfig", "keymap_data", "industry_compatible_data.py")
    spec = importlib.util.spec_from_file_location("_maya_style_industry_keymaps", path)
    industry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(industry)
    data = industry.generate_keymaps(industry.Params(
        use_mouse_emulate_3_button=bpy.context.preferences.inputs.use_mouse_emulate_3_button))
    maps = {name: payload["items"] for name, args, payload in data}
    # Native mode handlers run before the general 3D View handler. Remove their
    # competing number bindings explicitly, rather than relying on addon order.
    view_maps = {'3D View', '3D View Generic', 'Object Mode', 'Object Non-modal', 'Mesh', 'Pose'}
    numbers = {'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN'}
    plain_reserved = numbers | {
        'F2', 'F3', 'F4', 'F5', 'F6', 'F8', 'F9', 'F10', 'F11', 'F12',
        'Y', 'G', 'K', 'B', 'D', 'INSERT', 'X', 'C', 'V', 'P',
        'SPACE', 'PAGE_UP', 'PAGE_DOWN',
    }
    for name, args, payload in data:
        result = []
        for op, event, props in payload['items']:
            plain = not any(event.get(mod, False) for mod in ('ctrl', 'alt', 'shift', 'oskey'))
            key = event['type']
            if name in view_maps and plain and key in plain_reserved:
                continue
            if name == 'Frames' and plain and key == 'SPACE':
                continue
            if name == 'Object Mode' and key == 'D' and event.get('ctrl') and not event.get('shift') and not event.get('alt'):
                continue
            if name in view_maps and key == 'G' and event.get('ctrl') and not event.get('shift') and not event.get('alt'):
                continue
            if name in {'Object Mode', 'Mesh'} and key == 'RIGHTMOUSE' and plain:
                continue
            if name in {'3D View', 'Object Mode', 'Mesh'} and key == 'RIGHTMOUSE' and event.get('shift') and not event.get('alt') and not event.get('ctrl'):
                continue
            if name in {'3D View', 'Object Mode', 'Mesh'} and key == 'RIGHTMOUSE' and event.get('ctrl') and not event.get('alt') and not event.get('shift'):
                continue
            if name in view_maps and key == 'E' and event.get('ctrl') and not event.get('alt') and not event.get('shift'):
                continue
            if name in view_maps and key == 'A' and event.get('ctrl') and not event.get('alt'):
                continue
            if name in view_maps and plain and key in {'Q', 'W', 'E', 'R', 'T'} and op == 'wm.tool_set_by_id':
                # Presets load before add-ons. Native operator properties are
                # available at that point; custom properties would be discarded
                # and W/E/R would silently become the default Select tool.
                tool = {'Q': 'builtin.select_box', 'W': 'builtin.move',
                        'E': 'builtin.rotate', 'R': 'builtin.scale',
                        'T': 'builtin.transform'}[key]
                result.append(_item('wm.tool_set_by_id', key, {'name': tool, 'cycle': False}))
            else:
                result.append((op, event, props))
        payload['items'][:] = result

    for key, level in [('ONE', 1), ('TWO', 2), ('THREE', 3)]:
        maps['3D View'].append(_item('maya_style.smooth_preview', key, {'level': level}))
    for key, delta in [('PAGE_UP', 1), ('PAGE_DOWN', -1)]:
        maps['3D View'].append(_item('maya_style.preview_divisions', key, {'delta': delta}, repeat=True))
    for key, mode in [('FOUR', 'WIREFRAME'), ('FIVE', 'SOLID'), ('SIX', 'MATERIAL'), ('SEVEN', 'RENDERED')]:
        maps['3D View'].append(_item('maya_style.shading', key, {'mode': mode}))
    maps['3D View'].append(_item('maya_style.shading', 'FIVE', {'mode': 'WIRE_ON_SHADED'}, alt=True))
    for key, mode in [('F8', 'TOGGLE'), ('F9', 'VERT'), ('F10', 'EDGE'), ('F11', 'FACE'), ('F12', 'UV')]:
        maps['3D View'].append(_item('maya_style.component', key, {'mode': mode}))
    for key, shelf in [('F2', 'MODEL'), ('F3', 'RIG'), ('F4', 'ANIM'), ('F5', 'FX'), ('F6', 'RENDER')]:
        maps['3D View'].append(_item('maya_style.shelf', key, {'name': shelf}))
    for key, snap_mode in [('X', 'INCREMENT'), ('C', 'EDGE'), ('V', 'VERTEX')]:
        maps['3D View'].append(_item('maya_style.snap_hold', key, {'mode': snap_mode, 'toggle': False}))
    maps['3D View'].extend([
        _item('maya_style.last_tool', 'Y'),
        _item('screen.repeat_last', 'G'),
        _item('maya_style.poly_action', 'B', {'action': 'SOFT_SELECT_TOGGLE'}),
        _item('maya_style.pivot_mode', 'D', {'action': 'TOGGLE'}),
        _item('maya_style.pivot_mode', 'INSERT', {'action': 'TOGGLE'}),
        _item('maya_style.poly_action', 'G', {'action': 'GROUP'}, ctrl=True),
        _item('maya_style.hotbox', 'SPACE'),
        _item('maya_style.scrub', 'K'),
        _item('maya_style.channel_toggle', 'A', ctrl=True),
        _item('wm.call_menu_pie', 'RIGHTMOUSE', {'name': 'MAYA_STYLE_MT_components'}),
        _item('wm.call_menu_pie', 'RIGHTMOUSE', {'name': 'MAYA_STYLE_MT_context_tools'}, shift=True),
        _item('wm.call_menu_pie', 'RIGHTMOUSE', {'name': 'MAYA_STYLE_MT_convert_selection'}, ctrl=True),
    ])
    maps['Object Mode'].extend([
        _item('maya_style.duplicate', 'D', ctrl=True),
        _item('object.parent_set', 'P', {'type': 'OBJECT'}),
        _item('object.parent_clear', 'P', {'type': 'CLEAR_KEEP_TRANSFORM'}, shift=True),
    ])
    for name, operator in [('Object Mode', 'object.select_all'), ('Mesh', 'mesh.select_all'), ('Pose', 'pose.select_all')]:
        maps[name].append(_item(operator, 'A', {'action': 'SELECT'}, ctrl=True, shift=True))
        maps[name].append(_item(operator, 'I', {'action': 'INVERT'}, ctrl=True, shift=True))
    maps['Mesh'].extend([
        _item('mesh.extrude_region_move', 'E', ctrl=True),
        _item('mesh.bevel', 'B', ctrl=True),
        _item('maya_style.duplicate', 'D', ctrl=True),
        _item('maya_style.poly_action', 'DEL', {'action': 'DELETE_EDGE_VERTEX'}, ctrl=True),
        _item('maya_style.poly_action', 'BACK_SPACE', {'action': 'DELETE_EDGE_VERTEX'}, ctrl=True),
    ])
    maps['Frames'].extend([
        _item('screen.animation_play', 'V', alt=True),
        _item('screen.frame_offset', 'COMMA', {'delta': -1}, alt=True, repeat=True),
        _item('screen.frame_offset', 'PERIOD', {'delta': 1}, alt=True, repeat=True),
        _item('screen.keyframe_jump', 'COMMA', {'next': False}),
        _item('screen.keyframe_jump', 'PERIOD', {'next': True}),
    ])
    # Maya uses ,/. for keys, so remove the Industry pivot/orientation pies.
    maps['3D View'][:] = [i for i in maps['3D View'] if not (
        i[1]['type'] in {'COMMA', 'PERIOD'} and not any(i[1].get(m) for m in ('ctrl', 'alt', 'shift', 'oskey')))]
    maps['Screen'].append(_item('ed.redo', 'Y', ctrl=True, repeat=True))
    return data


def install_keyconfig(*, write_preset=True):
    """Create/activate Baya_3D and optionally persist its reloadable preset.

    The caller must save user preferences when desired. Writing this preset does
    not change startup.blend or overwrite a different keyconfig preset.
    """
    from bl_keymap_utils.io import keyconfig_init_from_data
    data = keyconfig_data()
    configs = bpy.context.window_manager.keyconfigs
    old = configs.get(KEYCONFIG_NAME)
    if old is not None:
        configs.remove(old)
    config = configs.new(KEYCONFIG_NAME)
    keyconfig_init_from_data(config, data)
    configs.active = config
    if write_preset:
        folder = bpy.utils.user_resource('SCRIPTS', path=os.path.join('presets', 'keyconfig'), create=True)
        path = os.path.join(folder, KEYCONFIG_NAME + '.py')
        with open(path, 'w', encoding='utf-8') as stream:
            stream.write("# Baya 3D key configuration, generated by blender_maya.\n"
                         "# Self-contained: key presets load before add-on import paths.\n"
                         "import bpy\n"
                         "from bl_keymap_utils.io import keyconfig_init_from_data\n"
                         "keyconfig_data = " + pprint.pformat(data, width=120) + "\n"
                         "config = bpy.context.window_manager.keyconfigs.new(" + repr(KEYCONFIG_NAME) + ")\n"
                         "keyconfig_init_from_data(config, keyconfig_data)\n")
    return config


def repair_keyconfig():
    """Rebuild the active Baya preset after custom operator RNA is available.

    Blender initializes key presets before enabling add-ons. That first pass
    cannot retain custom operator arguments such as preview levels or selection
    modes. Rebuilding once after registration also refreshes the effective user
    maps. This never chooses Baya over another active keymap or saves anything.
    """
    configs = bpy.context.window_manager.keyconfigs
    if configs.active is None or configs.active.name != KEYCONFIG_NAME:
        return False
    configs.update()
    # Once hydrated, file loads need no rebuild. In particular, do not disturb
    # user edits made later in the session merely because another file opens.
    needs_repair = False
    for map_name, _args, payload in keyconfig_data():
        keymap = configs.active.keymaps.get(map_name)
        if keymap is None:
            needs_repair = True
            break
        for operator, event, data in payload['items']:
            native_tool = (map_name in {'Object Mode', 'Mesh', 'Pose'}
                           and operator == 'wm.tool_set_by_id'
                           and event['type'] in {'Q', 'W', 'E', 'R', 'T'}
                           and not any(event.get(mod, False) for mod in ('ctrl', 'alt', 'shift', 'oskey')))
            if not native_tool and not (operator.startswith('maya_style.') and data):
                continue
            item = next((item for item in keymap.keymap_items
                         if item.idname == operator and item.type == event['type']
                         and item.value == event['value']
                         and all(bool(getattr(item, mod)) == bool(event.get(mod, False))
                                 for mod in ('ctrl', 'alt', 'shift', 'oskey'))), None)
            if item is None or any(not item.properties.is_property_set(prop)
                                   for prop, _value in data.get('properties', [])):
                needs_repair = True
                break
        if needs_repair:
            break
    if not needs_repair:
        return True
    install_keyconfig(write_preset=False)
    configs.update()
    return True


def _repair_keyconfig_deferred():
    global _keyconfig_repair_attempts
    _keyconfig_repair_attempts += 1
    configs = bpy.context.window_manager.keyconfigs
    if configs.active is not None and configs.active.name == KEYCONFIG_NAME:
        repair_keyconfig()
        return None
    # At application startup the selected preset may not have initialized yet.
    # Retry briefly, but never force a different active configuration.
    requested = bpy.context.preferences.keymap.active_keyconfig
    if requested == KEYCONFIG_NAME and _keyconfig_repair_attempts < 20:
        return 0.1
    return None


def _schedule_keyconfig_repair():
    global _keyconfig_repair_attempts
    _keyconfig_repair_attempts = 0
    if not bpy.app.timers.is_registered(_repair_keyconfig_deferred):
        bpy.app.timers.register(_repair_keyconfig_deferred, first_interval=0.1)


@persistent
def _repair_keyconfig_after_load(_dummy):
    configs = bpy.context.window_manager.keyconfigs
    if configs.active is not None and configs.active.name == KEYCONFIG_NAME:
        _schedule_keyconfig_repair()


_classes = (
    MAYA_STYLE_OT_tool,
    MAYA_STYLE_OT_last_tool,
    MAYA_STYLE_OT_smooth_preview,
    MAYA_STYLE_OT_preview_divisions,
    MAYA_STYLE_OT_shading,
    MAYA_STYLE_OT_component,
    MAYA_STYLE_OT_uv_mode,
    MAYA_STYLE_OT_duplicate,
    MAYA_STYLE_OT_snap_hold,
    MAYA_STYLE_OT_pivot_mode,
    MAYA_STYLE_OT_poly_action,
    MAYA_STYLE_OT_assign_shader,
    MAYA_STYLE_OT_command_exec,
    MAYA_STYLE_MT_assign_material,
    MAYA_STYLE_MT_normals,
    MAYA_STYLE_MT_components,
    MAYA_STYLE_MT_create,
    MAYA_STYLE_MT_context_tools,
    MAYA_STYLE_MT_convert_selection,
    MAYA_STYLE_MT_hotbox,
    MAYA_STYLE_OT_hotbox,
    MAYA_STYLE_OT_scrub,
)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    if not bpy.app.background and not bpy.app.timers.is_registered(_watch_tools):
        bpy.app.timers.register(_watch_tools, first_interval=0.35, persistent=True)
    if not bpy.app.background:
        if _repair_keyconfig_after_load not in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.append(_repair_keyconfig_after_load)
        _schedule_keyconfig_repair()


def unregister():
    global _hotbox_active, _snap_hold_active
    _hotbox_active = False
    _snap_hold_active = False
    if bpy.app.timers.is_registered(_watch_tools):
        bpy.app.timers.unregister(_watch_tools)
    if bpy.app.timers.is_registered(_repair_keyconfig_deferred):
        bpy.app.timers.unregister(_repair_keyconfig_deferred)
    if _repair_keyconfig_after_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_repair_keyconfig_after_load)
    _last_tools.clear()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
