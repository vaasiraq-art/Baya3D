"""Baya 3D shelves and attribute panels, powered by Blender."""
import bpy
from bpy.props import EnumProperty, PointerProperty, StringProperty

_original_tool_header = None


class MAYA_STYLE_PG_workspace(bpy.types.PropertyGroup):
    shelf: EnumProperty(name='Shelf', items=[
        ('MODEL', 'Poly Modeling', 'Create and edit polygon meshes', 'MESH_CUBE', 0),
        ('SCULPT', 'Sculpting', 'Sculpt and surface tools', 'SCULPTMODE_HLT', 1),
        ('RIG', 'Rigging', 'Armatures, parenting and skinning', 'ARMATURE_DATA', 2),
        ('ANIM', 'Animation', 'Keyframes and animation editors', 'ANIM', 3),
        ('RENDER', 'Rendering', 'Materials, lights and rendering', 'SHADING_RENDERED', 4),
        ('FX', 'FX', 'Procedural geometry and physics', 'MOD_PHYSICS', 5),
    ])


class MAYA_STYLE_OT_workspace(bpy.types.Operator):
    bl_idname = 'maya_style.workspace'
    bl_label = 'Open Workspace'
    bl_description = 'Switch to the matching Blender workspace'
    name: StringProperty()

    def execute(self, context):
        aliases = {'Materials': ('Shading',), 'Procedural FX': ('Geometry Nodes',),
                   'Baya 3D': ('Maya', 'Layout'), 'Maya': ('Baya 3D', 'Layout')}
        ws = bpy.data.workspaces.get(self.name)
        if ws is None:
            ws = next((bpy.data.workspaces.get(name) for name in aliases.get(self.name, ())
                       if bpy.data.workspaces.get(name) is not None), None)
        if not ws:
            self.report({'WARNING'}, 'This file does not contain the ' + self.name + ' workspace')
            return {'CANCELLED'}
        context.window.workspace = ws
        return {'FINISHED'}


class MAYA_STYLE_OT_shelf(bpy.types.Operator):
    bl_idname = 'maya_style.shelf'
    bl_label = 'Change Baya Shelf'
    bl_description = 'Show the matching modeling, rigging, animation, FX or rendering shelf'
    name: EnumProperty(items=[(v, l, '') for v, l in [('MODEL', 'Modeling'),
        ('RIG', 'Rigging'), ('ANIM', 'Animation'), ('FX', 'FX'), ('RENDER', 'Rendering')]])

    def execute(self, context):
        context.scene.maya_style.shelf = self.name
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
        return {'FINISHED'}


class MAYA_STYLE_OT_channel_toggle(bpy.types.Operator):
    bl_idname = 'maya_style.channel_toggle'
    bl_label = 'Channel Box / Attribute Editor'
    bl_description = 'Toggle the Channel Box sidebar; show object attributes in the Properties editor'

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    def execute(self, context):
        space = context.space_data
        space.show_region_ui = not space.show_region_ui
        if space.show_region_ui:
            for region in context.area.regions:
                if region.type == 'UI':
                    try:
                        region.active_panel_category = 'Baya'
                    except (TypeError, ValueError, AttributeError):
                        pass
        for area in context.screen.areas:
            if area.type == 'PROPERTIES' and context.object:
                area.spaces.active.context = 'OBJECT'
        return {'FINISHED'}


class MAYA_STYLE_OT_attributes(bpy.types.Operator):
    bl_idname = 'maya_style.attributes'
    bl_label = 'Attribute Editor'
    bl_description = 'Show detailed attributes in the right Properties editor'
    tab: StringProperty(default='OBJECT')

    def execute(self, context):
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                try:
                    area.spaces.active.context = self.tab
                except (TypeError, ValueError):
                    self.report({'INFO'}, 'Select an object that supports these attributes')
                area.tag_redraw()
                return {'FINISHED'}
        self.report({'INFO'}, 'Use the Baya 3D workspace for the Attribute Editor')
        return {'CANCELLED'}


class MAYA_STYLE_OT_freeze(bpy.types.Operator):
    bl_idname = 'maya_style.freeze'
    bl_label = 'Freeze Rotation and Scale'
    bl_description = 'Apply rotation and scale to object data using Blender Apply Transforms'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(context.selected_editable_objects)

    def execute(self, context):
        return bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


class MAYA_STYLE_MT_shelf_create(bpy.types.Menu):
    bl_label = 'Create'
    bl_idname = 'MAYA_STYLE_MT_shelf_create'

    def draw(self, context):
        col = self.layout
        col.label(text='Polygon Primitives')
        for op, label, icon in SHAPES:
            col.operator(op, text=label, icon=icon)
        col.separator()
        col.operator('curve.primitive_bezier_curve_add', text='Bezier Curve', icon='CURVE_BEZCURVE')
        col.operator('object.armature_add', text='Joint / Armature', icon='ARMATURE_DATA')
        col.operator('object.camera_add', text='Camera', icon='CAMERA_DATA')
        col.operator('object.light_add', text='Area Light', icon='LIGHT_AREA').type = 'AREA'


class MAYA_STYLE_MT_select(bpy.types.Menu):
    bl_label = 'Select'
    bl_idname = 'MAYA_STYLE_MT_select'

    def draw(self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        # Use the editor's native mode operators so Select never changes modes
        # or silently acts on objects while the user is editing components.
        namespace = {
            'OBJECT': 'object', 'EDIT_MESH': 'mesh', 'EDIT_CURVE': 'curve',
            'EDIT_SURFACE': 'curve', 'EDIT_ARMATURE': 'armature', 'POSE': 'pose',
            'EDIT_LATTICE': 'lattice', 'EDIT_METABALL': 'mball',
            'PARTICLE': 'particle', 'EDIT_GREASE_PENCIL': 'grease_pencil',
        }.get(context.mode)
        if namespace:
            for action, label, icon in [('SELECT', 'Select All', 'SELECT_SET'),
                                        ('DESELECT', 'Deselect All', 'SELECT_SUBTRACT'),
                                        ('INVERT', 'Invert Selection', 'SELECT_INTERSECT')]:
                lay.operator(namespace + '.select_all', text=label, icon=icon).action = action
            if namespace in {'object', 'mesh', 'curve', 'armature', 'lattice', 'particle', 'grease_pencil'}:
                lay.separator()
                lay.operator(namespace + '.select_more', text='Grow Selection', icon='ADD')
                lay.operator(namespace + '.select_less', text='Shrink Selection', icon='REMOVE')
        elif context.mode == 'EDIT_TEXT':
            lay.operator('font.select_all', text='Select All Text')
        else:
            lay.label(text='Selection follows the active mode')
        lay.separator()
        lay.operator('maya_style.component', text='Object Mode  F8', icon='OBJECT_DATA').mode = 'OBJECT'
        col = lay.column()
        col.enabled = context.object is not None and context.object.type == 'MESH'
        for mode, label, icon in [('VERT', 'Vertex  F9', 'VERTEXSEL'),
                                  ('EDGE', 'Edge  F10', 'EDGESEL'),
                                  ('FACE', 'Face  F11', 'FACESEL'),
                                  ('UV', 'UV  F12', 'UV')]:
            col.operator('maya_style.component', text=label, icon=icon).mode = mode


class MAYA_STYLE_MT_display(bpy.types.Menu):
    bl_label = 'Display'
    bl_idname = 'MAYA_STYLE_MT_display'

    def draw(self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        for level, label in [(1, 'Base Mesh  1'), (2, 'Cage + Smooth Preview  2'),
                             (3, 'Smooth Preview  3')]:
            lay.operator('maya_style.smooth_preview', text=label).level = level
        lay.separator()
        for mode, label, icon in [('WIREFRAME', 'Wireframe  4', 'SHADING_WIRE'),
                                  ('SOLID', 'Shaded  5', 'SHADING_SOLID'),
                                  ('MATERIAL', 'Textured / Material Preview  6', 'SHADING_TEXTURE'),
                                  ('RENDERED', 'Scene Lighting / Rendered  7', 'SHADING_RENDERED')]:
            lay.operator('maya_style.shading', text=label, icon=icon).mode = mode
        lay.separator()
        lay.operator('view3d.view_selected', text='Frame Selection  F', icon='ZOOM_SELECTED')
        lay.operator('view3d.view_all', text='Frame All  A', icon='HOME').center = False
        lay.operator('view3d.localview', text='Isolate Selection / Restore', icon='HIDE_OFF')
        lay.separator()
        lay.operator('view3d.view_persportho', text='Perspective / Orthographic', icon='VIEW_PERSPECTIVE')
        lay.menu('VIEW3D_MT_view_viewpoint', text='Front / Side / Top Views', icon='VIEW_ORTHO')
        lay.operator('view3d.view_camera', text='Active Camera', icon='CAMERA_DATA')
        if context.space_data and context.space_data.type == 'VIEW_3D':
            lay.separator()
            lay.prop(context.space_data.overlay, 'show_floor', text='Grid')
            lay.prop(context.space_data.overlay, 'show_overlays', text='Viewport Overlays')


class MAYA_STYLE_OT_about(bpy.types.Operator):
    bl_idname = 'baya.about'
    bl_label = 'About Baya 3D'
    bl_description = 'Baya 3D version, Blender engine attribution and essential controls'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=520)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        lay = self.layout
        lay.label(text='Baya 3D', icon='VIEW3D')
        lay.label(text='A Maya-inspired workspace, controls and modeling shelf.')
        lay.label(text='Powered by Blender ' + bpy.app.version_string)
        lay.separator()
        draw_shortcuts(lay)


class MAYA_STYLE_MT_modify(bpy.types.Menu):
    bl_label = 'Modify'
    bl_idname = 'MAYA_STYLE_MT_modify'

    def draw(self, context):
        lay = self.layout
        lay.operator('maya_style.freeze', icon='CHECKMARK')
        lay.operator('object.origin_set', text='Center Pivot', icon='PIVOT_MEDIAN').type = 'ORIGIN_GEOMETRY'
        lay.operator('object.duplicate', text='Duplicate', icon='DUPLICATE')
        lay.separator()
        lay.operator('object.parent_set', text='Parent', icon='CONSTRAINT_BONE').type = 'OBJECT'
        lay.operator('object.parent_clear', text='Unparent (Keep Transform)').type = 'CLEAR_KEEP_TRANSFORM'
        lay.separator()
        lay.operator('object.shade_smooth', text='Smooth Normals', icon='SHADING_SOLID')
        lay.operator('object.shade_flat', text='Flat Normals')
        lay.separator()
        lay.menu('OBJECT_MT_modifier_add', text='Add Modifier / Deformer')


class MAYA_STYLE_MT_mesh(bpy.types.Menu):
    bl_label = 'Edit Mesh'
    bl_idname = 'MAYA_STYLE_MT_mesh'

    def draw(self, context):
        lay = self.layout
        if context.mode != 'EDIT_MESH':
            lay.operator('maya_style.component', text='Enter Component Mode').mode = 'VERT'
            lay.separator()
        col = lay.column()
        col.enabled = context.mode == 'EDIT_MESH'
        col.operator('mesh.extrude_region_move', text='Extrude', icon='MOD_SOLIDIFY')
        col.operator('mesh.bevel', text='Bevel', icon='MOD_BEVEL')
        col.operator('mesh.inset', text='Inset', icon='FACESEL')
        col.operator('mesh.loopcut_slide', text='Insert Edge Loop', icon='MOD_EDGESPLIT')
        col.operator('mesh.knife_tool', text='Multi-Cut / Knife', icon='MOD_TRIANGULATE')
        col.separator()
        col.operator('mesh.merge', text='Merge Vertices', icon='AUTOMERGE_ON').type = 'CENTER'
        col.operator('mesh.remove_doubles', text='Merge by Distance')
        col.operator('mesh.bridge_edge_loops', text='Bridge')
        col.operator('mesh.subdivide', text='Subdivide')
        col.operator('mesh.normals_make_consistent', text='Recalculate Normals').inside = False
        col.separator()
        col.operator('uv.unwrap', text='Unwrap UVs', icon='UV')


class MAYA_STYLE_MT_windows(bpy.types.Menu):
    bl_label = 'Windows'
    bl_idname = 'MAYA_STYLE_MT_windows'

    def draw(self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        for name, icon in [('Baya 3D', 'VIEW3D'), ('UV Editing', 'UV'), ('Animation', 'ANIM'),
                           ('Materials', 'NODE_MATERIAL'), ('Rendering', 'RENDER_STILL'),
                           ('Procedural FX', 'GEOMETRY_NODES'), ('Scripting', 'CONSOLE')]:
            lay.operator('maya_style.workspace', text=name, icon=icon).name = name
        lay.separator()
        lay.operator('maya_style.channel_toggle', text='Channel Box / Attribute Editor')
        lay.operator('screen.region_quadview', text='Four View / Single View', icon='VIEW_ORTHO')
        lay.operator('wm.call_menu_pie', text='Hotbox', icon='MENU_PANEL').name = 'MAYA_STYLE_MT_hotbox'


class MAYA_STYLE_MT_main(bpy.types.Menu):
    bl_label = 'Baya 3D'
    bl_idname = 'MAYA_STYLE_MT_main'

    def draw(self, context):
        lay = self.layout
        lay.menu('MAYA_STYLE_MT_shelf_create')
        lay.menu('MAYA_STYLE_MT_select')
        lay.menu('MAYA_STYLE_MT_modify')
        lay.menu('MAYA_STYLE_MT_mesh')
        lay.menu('MAYA_STYLE_MT_display')
        lay.menu('MAYA_STYLE_MT_windows')
        lay.separator()
        lay.operator('baya.about', text='About Baya 3D / Controls', icon='INFO')
        lay.separator()
        lay.operator('wm.search_menu', text='Search All Commands', icon='VIEWZOOM')


SHAPES = [
    ('mesh.primitive_cube_add', 'Cube', 'MESH_CUBE'),
    ('mesh.primitive_uv_sphere_add', 'Sphere', 'MESH_UVSPHERE'),
    ('mesh.primitive_cylinder_add', 'Cylinder', 'MESH_CYLINDER'),
    ('mesh.primitive_cone_add', 'Cone', 'MESH_CONE'),
    ('mesh.primitive_plane_add', 'Plane', 'MESH_PLANE'),
    ('mesh.primitive_torus_add', 'Torus', 'MESH_TORUS'),
]


def workspace_button(lay, name, text, icon):
    lay.operator('maya_style.workspace', text=text, icon=icon).name = name


def draw_shelf(self, context):
    """Replace just the tool-header row; native main menus and toolbar remain accessible."""
    lay = self.layout
    if (context.mode.startswith(('SCULPT', 'PAINT')) or context.mode in {
            'PARTICLE', 'WEIGHT_GPENCIL', 'VERTEX_GPENCIL',
            'WEIGHT_GREASE_PENCIL', 'VERTEX_GREASE_PENCIL'}):
        lay.menu('MAYA_STYLE_MT_main', text='Baya 3D')
        if _original_tool_header:
            _original_tool_header(self, context)
        return
    lay.menu('MAYA_STYLE_MT_main', text='Baya 3D')
    lay.prop(context.scene.maya_style, 'shelf', text='')
    for menu in ['shelf_create', 'select', 'modify', 'display', 'windows']:
        lay.menu('MAYA_STYLE_MT_' + menu)
    lay.separator()
    shelf = context.scene.maya_style.shelf
    row = lay.row(align=True)
    if shelf == 'MODEL':
        for op, label, icon in SHAPES:
            row.operator(op, text='', icon=icon)
        lay.separator()
        row = lay.row(align=True)
        row.menu('MAYA_STYLE_MT_mesh', text='Edit Mesh')
        workspace_button(row, 'UV Editing', 'UV', 'UV')
    elif shelf == 'SCULPT':
        workspace_button(row, 'Sculpting', 'Sculpt', 'SCULPTMODE_HLT')
        row.operator('object.shade_smooth', text='', icon='SHADING_SOLID')
        row.operator('object.modifier_add', text='Subdiv', icon='MOD_SUBSURF').type = 'SUBSURF'
        row.operator('object.modifier_add', text='Multires', icon='MOD_MULTIRES').type = 'MULTIRES'
        row.operator('object.modifier_add', text='Mirror', icon='MOD_MIRROR').type = 'MIRROR'
    elif shelf == 'RIG':
        row.operator('object.armature_add', text='Joint', icon='ARMATURE_DATA')
        row.operator('object.parent_set', text='Bind Skin', icon='MOD_ARMATURE').type = 'ARMATURE_AUTO'
        row.operator('object.parent_set', text='Parent', icon='CONSTRAINT_BONE').type = 'OBJECT'
        row.operator('object.parent_clear', text='', icon='UNLINKED').type = 'CLEAR_KEEP_TRANSFORM'
        row.operator('maya_style.attributes', text='', icon='CONSTRAINT').tab = 'CONSTRAINT'
    elif shelf == 'ANIM':
        row.operator('anim.keyframe_insert_by_name', text='Set Key', icon='KEY_HLT').type = 'LocRotScale'
        row.operator('screen.animation_play', text='Play', icon='PLAY')
        row.operator('screen.keyframe_jump', text='', icon='PREV_KEYFRAME').next = False
        row.operator('screen.keyframe_jump', text='', icon='NEXT_KEYFRAME').next = True
        row.prop(context.scene.tool_settings, 'use_keyframe_insert_auto', text='', icon='REC')
        workspace_button(row, 'Animation', 'Graph', 'GRAPH')
    elif shelf == 'RENDER':
        workspace_button(row, 'Materials', 'Materials', 'NODE_MATERIAL')
        row.operator('object.light_add', text='Area', icon='LIGHT_AREA').type = 'AREA'
        row.operator('object.light_add', text='Sun', icon='LIGHT_SUN').type = 'SUN'
        row.operator('object.camera_add', text='Camera', icon='CAMERA_DATA')
        row.operator('maya_style.attributes', text='', icon='SCENE').tab = 'RENDER'
        row.operator('render.render', text='Render', icon='RENDER_STILL')
    else:
        workspace_button(row, 'Procedural FX', 'Nodes', 'GEOMETRY_NODES')
        row.operator('maya_style.attributes', text='', icon='PHYSICS').tab = 'PHYSICS'
        row.operator('object.modifier_add', text='Cloth', icon='MOD_CLOTH').type = 'CLOTH'
        row.operator('object.modifier_add', text='Ocean', icon='MOD_OCEAN').type = 'OCEAN'
        row.operator('object.modifier_add', text='', icon='GEOMETRY_NODES').type = 'NODES'
    lay.separator_spacer()
    row = lay.row(align=True)
    row.operator('maya_style.channel_toggle', text='', icon='PROPERTIES')
    row.operator('baya.about', text='', icon='INFO')
    # Native tool settings remain available even though the shelf occupies this row.
    row.popover(panel='VIEW3D_PT_active_tool', text='', icon='TOOL_SETTINGS')


class MAYA_STYLE_PT_channels(bpy.types.Panel):
    bl_label = 'Channel Box'
    bl_idname = 'MAYA_STYLE_PT_channels'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -100

    def draw(self, context):
        lay = self.layout
        obj = context.object
        if obj is None:
            lay.label(text='Select an object', icon='RESTRICT_SELECT_OFF')
            lay.separator()
            lay.label(text='Create from the shelf above.')
            lay.label(text='Alt + mouse to navigate.')
            return
        lay.prop(obj, 'name', text='', icon='OBJECT_DATA')
        target = (context.active_pose_bone or obj) if context.mode == 'POSE' else obj
        if target != obj:
            lay.label(text=target.name, icon='BONE_DATA')
        col = lay.column(align=True)
        for prop, label in [('location', 'Translate'), ('rotation_euler', 'Rotate'), ('scale', 'Scale')]:
            if prop == 'rotation_euler' and target.rotation_mode in {'QUATERNION', 'AXIS_ANGLE'}:
                prop = 'rotation_quaternion' if target.rotation_mode == 'QUATERNION' else 'rotation_axis_angle'
                col.prop(target, prop, text='Rotate')
                continue
            for i, axis in enumerate('XYZ'):
                row = col.row(align=True)
                row.label(text=f'{label} {axis}')
                row.prop(target, prop, index=i, text='')
            if prop != 'scale':
                col.separator(factor=0.3)
        row = lay.row(align=True)
        row.operator('anim.keyframe_insert_by_name', text='Set Key', icon='KEY_HLT').type = 'LocRotScale'
        row.operator('maya_style.attributes', text='Attributes', icon='PROPERTIES').tab = 'OBJECT'


class MAYA_STYLE_PT_inputs(bpy.types.Panel):
    bl_label = 'Inputs / History'
    bl_idname = 'MAYA_STYLE_PT_inputs'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -99

    def draw(self, context):
        lay = self.layout
        obj = context.object
        if not obj:
            lay.label(text='No active object')
            return
        if not obj.modifiers:
            lay.label(text='No modifiers')
        for mod in obj.modifiers:
            row = lay.row(align=True)
            row.label(text=mod.name, icon='MODIFIER')
            row.prop(mod, 'show_viewport', text='', icon='RESTRICT_VIEW_OFF')
            row.prop(mod, 'show_render', text='', icon='RESTRICT_RENDER_OFF')
        lay.operator('maya_style.attributes', text='Edit Inputs / Modifiers', icon='MODIFIER').tab = 'MODIFIER'


class MAYA_STYLE_PT_layers(bpy.types.Panel):
    bl_label = 'Display Layers / Collections'
    bl_idname = 'MAYA_STYLE_PT_layers'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -98

    def draw(self, context):
        lay = self.layout
        for coll in context.scene.collection.children:
            row = lay.row(align=True)
            row.prop(coll, 'hide_viewport', text='', icon='HIDE_OFF')
            row.prop(coll, 'name', text='')
            row.prop(coll, 'hide_render', text='', icon='RESTRICT_RENDER_OFF')
        if not context.scene.collection.children:
            lay.label(text='Use the Outliner to add collections')


class MAYA_STYLE_PT_reference(bpy.types.Panel):
    bl_label = 'Baya Controls'
    bl_idname = 'MAYA_STYLE_PT_reference'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = -97

    def draw(self, context):
        draw_shortcuts(self.layout)
        self.layout.separator()
        self.layout.operator('baya.about', icon='INFO')


def draw_shortcuts(layout):
    col = layout.column(align=True)
    for text in ['Q / W / E / R: select / move / rotate / scale',
                 'Alt + LMB / MMB / RMB: orbit / pan / dolly',
                 'F: frame selected    A: frame all',
                 '1 / 2 / 3: mesh / cage / smooth preview',
                 '4 / 5 / 6 / 7: viewport display',
                 'F8: object / component mode',
                 'F9 / F10 / F11 / F12: vertex / edge / face / UV',
                 'RMB: selection menu    Shift + RMB: create menu',
                 'Ctrl + D: duplicate    Ctrl + E: extrude',
                 'S: set key    Alt + V: play / pause',
                 'Tap Space: four view    Hold Space: hotbox',
                 'Ctrl + A: Channel Box / Attributes',
                 'F2-F6: modeling / rigging / animation / FX / render',
                 'Tab: search all commands']:
        col.label(text=text)


def apply_theme():
    """Apply a restrained charcoal Maya-like palette with green active outlines."""
    theme = bpy.context.preferences.themes[0]
    applied = []
    def setv(obj, key, value):
        if not hasattr(obj, key):
            return
        current = getattr(obj, key)
        if isinstance(value, tuple) and hasattr(current, '__len__'):
            value = value[:len(current)]
            if len(value) < len(current):
                value = value + (1.0,) * (len(current) - len(value))
        setattr(obj, key, value)
        applied.append(key)
    for p in theme.user_interface.bl_rna.properties:
        if p.identifier.startswith('wcol_') and p.identifier != 'wcol_state':
            widget = getattr(theme.user_interface, p.identifier)
            for key, value in {
                'inner': (.245, .245, .245, 1), 'inner_sel': (.27, .42, .48, 1),
                'outline': (.12, .12, .12, 1), 'outline_sel': (.34, .64, .70, 1),
                'text': (.87, .87, .87, 1), 'text_sel': (1, 1, 1, 1),
                'item': (.48, .70, .75, 1), 'roundness': .12, 'show_shaded': False,
            }.items():
                setv(widget, key, value)
    ui = theme.user_interface
    for key, value in {
        'panel_roundness': .12, 'panel_header': (.20, .20, .20, 1),
        'panel_back': (.23, .23, .23, 1), 'panel_sub_back': (.20, .20, .20, 1),
        'panel_text': (.86, .86, .86, 1), 'panel_title': (.90, .90, .90, 1),
        'editor_border': (.10, .10, .10, 1), 'editor_outline': (.12, .12, .12, 1),
        'editor_outline_active': (.24, .49, .53, 1), 'icon_saturation': .65,
        'axis_x': (.85, .24, .24), 'axis_y': (.38, .68, .30), 'axis_z': (.30, .50, .88),
    }.items():
        setv(ui, key, value)
    v = theme.view_3d
    for key, value in {
        'grid': (.39, .39, .39), 'grid_major': (.48, .48, .48),
        'wire': (.07, .07, .07), 'wire_edit': (.08, .08, .08),
        'object_active': (.25, .90, .55), 'object_selected': (.78, .94, .86),
        'vertex': (.10, .10, .10), 'vertex_select': (1, .62, .16),
        'edge_select': (1, .62, .16), 'face_select': (1, .54, .12, .22),
    }.items():
        setv(v, key, value)
    v.space.gradients.background_type = 'LINEAR'
    v.space.gradients.high_gradient = (.27, .28, .29)
    v.space.gradients.gradient = (.17, .18, .19)
    for p in theme.bl_rna.properties:
        if p.type == 'POINTER':
            section = getattr(theme, p.identifier)
            if hasattr(section, 'space'):
                setv(section.space, 'header', (.20, .20, .20, 1))
                setv(section.space, 'text', (.86, .86, .86))
                setv(section.space, 'text_hi', (1, 1, 1))
                setv(section.space, 'back', (.23, .23, .23))
    return {'theme': 'Maya-inspired charcoal', 'assignments': len(applied)}


CLASSES = (MAYA_STYLE_PG_workspace, MAYA_STYLE_OT_workspace, MAYA_STYLE_OT_shelf, MAYA_STYLE_OT_channel_toggle,
           MAYA_STYLE_OT_attributes, MAYA_STYLE_OT_freeze, MAYA_STYLE_OT_about, MAYA_STYLE_MT_shelf_create,
           MAYA_STYLE_MT_select, MAYA_STYLE_MT_display, MAYA_STYLE_MT_modify, MAYA_STYLE_MT_mesh, MAYA_STYLE_MT_windows,
           MAYA_STYLE_MT_main, MAYA_STYLE_PT_channels, MAYA_STYLE_PT_inputs,
           MAYA_STYLE_PT_layers, MAYA_STYLE_PT_reference)


def register():
    global _original_tool_header
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.maya_style = PointerProperty(type=MAYA_STYLE_PG_workspace)
    from bl_ui.space_view3d import VIEW3D_HT_tool_header
    _original_tool_header = VIEW3D_HT_tool_header.draw
    VIEW3D_HT_tool_header.draw = draw_shelf


def unregister():
    global _original_tool_header
    from bl_ui.space_view3d import VIEW3D_HT_tool_header
    if _original_tool_header is not None:
        VIEW3D_HT_tool_header.draw = _original_tool_header
        _original_tool_header = None
    if hasattr(bpy.types.Scene, 'maya_style'):
        del bpy.types.Scene.maya_style
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
