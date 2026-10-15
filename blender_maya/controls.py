"""Baya 3D controls for Blender 5.3; a complete Maya-inspired keymap.

Importing and registering this module never saves preferences. The installer
explicitly calls install_keyconfig(), then decides when preferences are saved.
"""

import importlib.util
import os
import pprint
import time

import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty, IntProperty, StringProperty


KEYCONFIG_NAME = "Baya_3D"
_PREVIEW_UID = "_maya_style_preview_modifier_uid"
_NORMALS_UID = "_maya_style_preview_normals_modifier_uid"
_NORMALS_GROUP_TAG = "_maya_style_preview_normals_group"
_PREVIEW_WIRE = "_maya_style_preview_wire_display"
_last_tools = {}
_keyconfig_repair_attempts = 0
_basic_tools = {"builtin.select", "builtin.select_box", "builtin.select_circle",
                "builtin.select_lasso", "builtin.move", "builtin.rotate", "builtin.scale",
                "builtin.transform"}


def _view_poll(context):
    return context.area is not None and context.area.type == 'VIEW_3D'


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
        return bpy.ops.wm.tool_set_by_id(name=self.name, cycle=False)


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
    mode: EnumProperty(items=[(value, label, "") for value, label in (
        ('WIREFRAME', "Wireframe"), ('SOLID', "Shaded"),
        ('MATERIAL', "Textured / Material Preview"), ('RENDERED', "Scene Lights / Rendered"))])

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def execute(self, context):
        context.space_data.shading.type = self.mode
        if self.mode == 'RENDERED':
            context.space_data.shading.use_scene_lights_render = True
            context.space_data.shading.use_scene_world_render = True
        return {'FINISHED'}


class MAYA_STYLE_OT_component(bpy.types.Operator):
    bl_idname = "maya_style.component"
    bl_label = "Selection Mode"
    bl_description = "Choose object, vertex, edge, face or UV selection"
    mode: EnumProperty(items=[(value, label, "") for value, label in (
        ('TOGGLE', "Object / Component"), ('OBJECT', "Object"), ('VERT', "Vertex"),
        ('EDGE', "Edge"), ('FACE', "Face"), ('UV', "UV"))], default='TOGGLE')

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
            self.report({'INFO'}, "Vertex, edge and face shortcuts require a mesh")
            return {'CANCELLED'}
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        if self.mode != 'TOGGLE':
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
        workspace = bpy.data.workspaces.get("UV Editing")
        if workspace is None:
            self.report({'WARNING'}, "Use a UV Editor to select UV components; UV Editing workspace is missing")
            return {'CANCELLED'}
        if context.mode != 'EDIT_MESH':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type='FACE')
        context.scene.tool_settings.use_uv_select_sync = False
        context.scene.tool_settings.uv_select_mode = 'VERTEX'
        context.window.workspace = workspace
        return {'FINISHED'}


class MAYA_STYLE_OT_duplicate(bpy.types.Operator):
    bl_idname = "maya_style.duplicate"
    bl_label = "Duplicate"
    bl_description = "Duplicate selected objects in place"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return _view_poll(context) and context.mode == 'OBJECT' and bool(context.selected_objects)

    def execute(self, context):
        return bpy.ops.object.duplicate(linked=False)


class MAYA_STYLE_MT_components(bpy.types.Menu):
    bl_label = "Selection Marking Menu"
    def draw(self, context):
        pie = self.layout.menu_pie()
        for label, mode in (("Vertex  F9", 'VERT'), ("Edge  F10", 'EDGE'),
                            ("Object  F8", 'OBJECT'), ("Face  F11", 'FACE')):
            pie.operator("maya_style.component", text=label).mode = mode
        pie.operator("maya_style.uv_mode", text="UV  F12")
        menu = "VIEW3D_MT_edit_mesh_context_menu" if context.mode == 'EDIT_MESH' else "VIEW3D_MT_object_context_menu"
        pie.menu(menu, text="Context Commands")
        pie.operator("view3d.view_selected", text="Frame Selection  F")
        pie.operator("view3d.view_all", text="Frame All  A").center = False


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
        pie.operator("mesh.primitive_circle_add", text="Circle", icon='MESH_CIRCLE')


class MAYA_STYLE_MT_hotbox(bpy.types.Menu):
    bl_label = "Baya 3D Hotbox"
    def draw(self, context):
        pie = self.layout.menu_pie()
        pie.menu("VIEW3D_MT_view", text="View")
        pie.menu("VIEW3D_MT_add", text="Create")
        pie.operator("screen.region_quadview", text="Single / Four Views")
        pie.operator("wm.call_menu_pie", text="Selection").name = "MAYA_STYLE_MT_components"
        pie.menu("TOPBAR_MT_file", text="File")
        pie.menu("TOPBAR_MT_edit", text="Edit")
        pie.menu("VIEW3D_MT_edit_mesh" if context.mode == 'EDIT_MESH' else "VIEW3D_MT_object", text="Mesh / Object")
        pie.operator("wm.search_menu", text="Search Commands", icon='VIEWZOOM')


class MAYA_STYLE_OT_hotbox(bpy.types.Operator):
    bl_idname = "maya_style.hotbox"
    bl_label = "Space: Four Views / Hotbox"
    bl_description = "Tap Space to toggle four views; hold Space for the hotbox pie menu"
    _timer = None
    _started = 0.0

    @classmethod
    def poll(cls, context):
        return _view_poll(context)

    def _cleanup(self, context):
        if self._timer is not None:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def invoke(self, context, event):
        self._started = time.monotonic()
        self._timer = context.window_manager.event_timer_add(0.05, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'WINDOW_DEACTIVATE'}:
            self._cleanup(context)
            return {'CANCELLED'}
        if event.type == 'SPACE' and event.value == 'RELEASE':
            self._cleanup(context)
            return bpy.ops.screen.region_quadview()
        if event.type == 'TIMER' and time.monotonic() - self._started >= 0.22:
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
    plain_reserved = numbers | {'F2', 'F3', 'F4', 'F5', 'F6', 'F8', 'F9', 'F10', 'F11', 'F12', 'Y', 'K', 'SPACE', 'PAGE_UP', 'PAGE_DOWN'}
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
            if name in {'Object Mode', 'Mesh'} and key == 'RIGHTMOUSE' and plain:
                continue
            if name == '3D View' and key == 'RIGHTMOUSE' and event.get('shift') and not event.get('alt') and not event.get('ctrl'):
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
    for key, mode in [('F8', 'TOGGLE'), ('F9', 'VERT'), ('F10', 'EDGE'), ('F11', 'FACE'), ('F12', 'UV')]:
        maps['3D View'].append(_item('maya_style.component', key, {'mode': mode}))
    for key, shelf in [('F2', 'MODEL'), ('F3', 'RIG'), ('F4', 'ANIM'), ('F5', 'FX'), ('F6', 'RENDER')]:
        maps['3D View'].append(_item('maya_style.shelf', key, {'name': shelf}))
    maps['3D View'].extend([
        _item('maya_style.last_tool', 'Y'),
        _item('maya_style.hotbox', 'SPACE'),
        _item('maya_style.scrub', 'K'),
        _item('maya_style.channel_toggle', 'A', ctrl=True),
        _item('wm.call_menu_pie', 'RIGHTMOUSE', {'name': 'MAYA_STYLE_MT_components'}),
        _item('wm.call_menu_pie', 'RIGHTMOUSE', {'name': 'MAYA_STYLE_MT_create'}, shift=True),
    ])
    maps['Object Mode'].append(_item('maya_style.duplicate', 'D', ctrl=True))
    for name, operator in [('Object Mode', 'object.select_all'), ('Mesh', 'mesh.select_all'), ('Pose', 'pose.select_all')]:
        maps[name].append(_item(operator, 'A', {'action': 'SELECT'}, ctrl=True, shift=True))
        maps[name].append(_item(operator, 'I', {'action': 'INVERT'}, ctrl=True, shift=True))
    maps['Mesh'].append(_item('mesh.extrude_region_move', 'E', ctrl=True))
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
    MAYA_STYLE_OT_tool, MAYA_STYLE_OT_last_tool, MAYA_STYLE_OT_smooth_preview,
    MAYA_STYLE_OT_preview_divisions,
    MAYA_STYLE_OT_shading, MAYA_STYLE_OT_component, MAYA_STYLE_OT_uv_mode,
    MAYA_STYLE_OT_duplicate, MAYA_STYLE_MT_components, MAYA_STYLE_MT_create,
    MAYA_STYLE_MT_hotbox, MAYA_STYLE_OT_hotbox, MAYA_STYLE_OT_scrub,
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
    if bpy.app.timers.is_registered(_watch_tools):
        bpy.app.timers.unregister(_watch_tools)
    if bpy.app.timers.is_registered(_repair_keyconfig_deferred):
        bpy.app.timers.unregister(_repair_keyconfig_deferred)
    if _repair_keyconfig_after_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_repair_keyconfig_after_load)
    _last_tools.clear()
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
