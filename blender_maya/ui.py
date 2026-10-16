"""Baya 3D UI: Menu Sets, Status Line, Tabbed Shelves, Channel Box, Modeling Toolkit, Attribute Editor & HUD."""
import math
import bpy
import blf
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty

_original_tool_header = None
_hud_draw_handler = None


def _active_transform_target(context):
    obj = context.object
    if obj is None:
        return None
    return (context.active_pose_bone or obj) if context.mode == 'POSE' else obj


def _is_maya_yup(scene):
    ms = getattr(scene, 'maya_style', None)
    return ms is None or ms.coord_system == 'MAYA_Y_UP'


def _loc_index(scene, maya_axis):
    # Maya: X=right(0), Y=up(Blender Z=2), Z=depth(Blender Y=1)
    if _is_maya_yup(scene):
        return (0, 2, 1)[maya_axis]
    return maya_axis


def _get_maya_loc(axis):
    def getter(self):
        target = _active_transform_target(bpy.context)
        if target is None:
            return 0.0
        idx = _loc_index(bpy.context.scene, axis)
        return float(target.location[idx])
    return getter


def _set_maya_loc(axis):
    def setter(self, value):
        target = _active_transform_target(bpy.context)
        if target is None:
            return
        idx = _loc_index(bpy.context.scene, axis)
        target.location[idx] = float(value)
    return setter


def _get_maya_rot(axis):
    def getter(self):
        target = _active_transform_target(bpy.context)
        if target is None:
            return 0.0
        idx = _loc_index(bpy.context.scene, axis)
        return float(target.rotation_euler[idx])
    return getter


def _set_maya_rot(axis):
    def setter(self, value):
        target = _active_transform_target(bpy.context)
        if target is None:
            return
        idx = _loc_index(bpy.context.scene, axis)
        target.rotation_euler[idx] = float(value)
    return setter


def _get_maya_scale(axis):
    def getter(self):
        target = _active_transform_target(bpy.context)
        if target is None:
            return 1.0
        idx = _loc_index(bpy.context.scene, axis)
        return float(target.scale[idx])
    return getter


def _set_maya_scale(axis):
    def setter(self, value):
        target = _active_transform_target(bpy.context)
        if target is None:
            return
        idx = _loc_index(bpy.context.scene, axis)
        target.scale[idx] = float(value)
    return setter


class MAYA_STYLE_PG_workspace(bpy.types.PropertyGroup):
    menu_set: EnumProperty(
        name='Menu Set',
        description='Active Maya-style Menu Set',
        items=[
            ('MODELING', 'Modeling', 'Polygon, curve, surface and UV modeling menus (F2)', 'MESH_CUBE', 0),
            ('RIGGING', 'Rigging', 'Skeleton, skinning, deformer and constraint menus (F3)', 'ARMATURE_DATA', 1),
            ('ANIMATION', 'Animation', 'Keyframing, playback and animation editor menus (F4)', 'ANIM', 2),
            ('FX', 'FX', 'Procedural FX, cloth, particles and simulation menus (F5)', 'MOD_PHYSICS', 3),
            ('RENDERING', 'Rendering', 'Lighting, shading, cameras and render menus (F6)', 'SHADING_RENDERED', 4),
        ],
        default='MODELING',
    )
    shelf: EnumProperty(
        name='Shelf',
        description='Active Maya-style Tool Shelf',
        items=[
            ('CURVES', 'Curves', 'NURBS and Bezier curve creation and editing tools', 'CURVE_BEZCURVE', 0),
            ('MODEL', 'Polygons', 'Create and edit polygon meshes', 'MESH_CUBE', 1),
            ('SCULPT', 'Sculpting', 'Sculpt brushes, remesh and subdivision tools', 'SCULPTMODE_HLT', 2),
            ('UV', 'UV Editing', 'UV projection, seam, unwrap and layout tools', 'UV', 3),
            ('RIG', 'Rigging', 'Joints, skin binding, parenting and constraints', 'ARMATURE_DATA', 4),
            ('ANIM', 'Animation', 'Keyframes, breakdown keys and animation editors', 'ANIM', 5),
            ('RENDER', 'Rendering', 'Shaders, lights, cameras and rendering', 'SHADING_RENDERED', 6),
            ('FX', 'FX', 'Procedural geometry nodes, cloth and physics', 'MOD_PHYSICS', 7),
        ],
        default='MODEL',
    )
    right_dock: EnumProperty(
        name='Right Dock',
        description='Active right-hand dock panel mode',
        items=[
            ('ALL', 'All Panels', 'Show Channel Box, Modeling Toolkit, Attribute Editor and Display Layers', 'MENU_PANEL', 0),
            ('CHANNEL_BOX', 'Channel Box / Layers', 'Focus on Channel Box, Inputs and Display Layers', 'PROPERTIES', 1),
            ('MODELING_TOOLKIT', 'Modeling Toolkit', 'Focus on Modeling Toolkit selection, snap and mesh tools', 'MOD_BUILD', 2),
            ('ATTRIBUTE_EDITOR', 'Attribute Editor', 'Focus on node tabs, transform, shape and shader attributes', 'PREFERENCES', 3),
        ],
        default='ALL',
    )
    ae_tab: EnumProperty(
        name='Node Tab',
        description='Active node tab in the Baya Attribute Editor',
        items=[
            ('TRANSFORM', 'Transform', 'Transform node attributes', 'OBJECT_ORIGIN', 0),
            ('SHAPE', 'Shape', 'Mesh / Curve / Camera / Light shape attributes', 'MESH_DATA', 1),
            ('MATERIAL', 'Shader', 'Assigned surface shader and material properties', 'MATERIAL', 2),
            ('RENDER', 'Render', 'Scene render engine and output settings', 'SCENE', 3),
        ],
        default='TRANSFORM',
    )
    coord_system: EnumProperty(
        name='Coordinates',
        description='Coordinate axis convention shown in the Channel Box and HUD',
        items=[
            ('MAYA_Y_UP', 'Maya Y-Up (XYZ)', 'Display and edit coordinates with Y as Up and Z as Depth (Maya convention)', 'ORIENTATION_GLOBAL', 0),
            ('BLENDER_Z_UP', 'Blender Z-Up (XYZ)', 'Display and edit native Blender Z-Up coordinates', 'EMPTY_AXIS', 1),
        ],
        default='MAYA_Y_UP',
    )
    show_hud: BoolProperty(
        name='Heads Up Display',
        description='Display Maya-style viewport HUD (Poly Count, Object Details, Camera & Axis info)',
        default=True,
    )
    show_hud_polycount: BoolProperty(name='Poly Count', default=True)
    show_hud_object: BoolProperty(name='Object Details', default=True)
    show_hud_camera: BoolProperty(name='Camera & Axis Info', default=True)
    show_status_line: BoolProperty(
        name='Status Line Icons',
        description='Show Maya Status Line selection masks, snapping and history icons in the top bar',
        default=True,
    )
    command_lang: EnumProperty(
        name='Command Type',
        items=[
            ('MEL', 'MEL', 'Execute Maya-style MEL command aliases (polyCube, FreezeTransformations, DeleteHistory, etc.)'),
            ('PYTHON', 'Python', 'Execute Blender Python expressions'),
        ],
        default='MEL',
    )
    command_input: StringProperty(
        name='Command',
        description='Type a MEL command (e.g. polyCube, DeleteHistory, FreezeTransformations) or Python expression',
        default='',
    )
    last_command_result: StringProperty(
        name='Result',
        default='Ready',
    )

    maya_tx: FloatProperty(name='Translate X', subtype='DISTANCE', get=_get_maya_loc(0), set=_set_maya_loc(0))
    maya_ty: FloatProperty(name='Translate Y', subtype='DISTANCE', get=_get_maya_loc(1), set=_set_maya_loc(1))
    maya_tz: FloatProperty(name='Translate Z', subtype='DISTANCE', get=_get_maya_loc(2), set=_set_maya_loc(2))

    maya_rx: FloatProperty(name='Rotate X', subtype='ANGLE', get=_get_maya_rot(0), set=_set_maya_rot(0))
    maya_ry: FloatProperty(name='Rotate Y', subtype='ANGLE', get=_get_maya_rot(1), set=_set_maya_rot(1))
    maya_rz: FloatProperty(name='Rotate Z', subtype='ANGLE', get=_get_maya_rot(2), set=_set_maya_rot(2))

    maya_sx: FloatProperty(name='Scale X', get=_get_maya_scale(0), set=_set_maya_scale(0))
    maya_sy: FloatProperty(name='Scale Y', get=_get_maya_scale(1), set=_set_maya_scale(1))
    maya_sz: FloatProperty(name='Scale Z', get=_get_maya_scale(2), set=_set_maya_scale(2))


class MAYA_STYLE_OT_workspace(bpy.types.Operator):
    bl_idname = 'maya_style.workspace'
    bl_label = 'Open Workspace'
    bl_description = 'Switch to the matching Blender workspace'
    name: StringProperty()

    def execute(self, context):
        aliases = {
            'Materials': ('Shading',),
            'Procedural FX': ('Geometry Nodes',),
            'Baya 3D': ('Maya', 'Layout'),
            'Maya': ('Baya 3D', 'Layout'),
        }
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
    bl_label = 'Change Baya Shelf & Menu Set'
    bl_description = 'Switch the active Baya shelf and matching Menu Set'
    name: EnumProperty(items=[(v, l, '') for v, l in [
        ('CURVES', 'Curves'),
        ('MODEL', 'Modeling'),
        ('SCULPT', 'Sculpting'),
        ('UV', 'UV Editing'),
        ('RIG', 'Rigging'),
        ('ANIM', 'Animation'),
        ('FX', 'FX'),
        ('RENDER', 'Rendering'),
    ]])

    def execute(self, context):
        ms = context.scene.maya_style
        ms.shelf = self.name
        menu_map = {
            'CURVES': 'MODELING',
            'MODEL': 'MODELING',
            'SCULPT': 'MODELING',
            'UV': 'MODELING',
            'RIG': 'RIGGING',
            'ANIM': 'ANIMATION',
            'FX': 'FX',
            'RENDER': 'RENDERING',
        }
        if self.name in menu_map:
            ms.menu_set = menu_map[self.name]
        if context.screen:
            for area in context.screen.areas:
                if area.type in {'VIEW_3D', 'TOPBAR'}:
                    area.tag_redraw()
        return {'FINISHED'}


class MAYA_STYLE_OT_menu_set(bpy.types.Operator):
    bl_idname = 'maya_style.menu_set'
    bl_label = 'Switch Menu Set'
    bl_description = 'Switch the active Maya-style Menu Set'
    name: EnumProperty(items=[
        ('MODELING', 'Modeling', ''),
        ('RIGGING', 'Rigging', ''),
        ('ANIMATION', 'Animation', ''),
        ('FX', 'FX', ''),
        ('RENDERING', 'Rendering', ''),
    ])

    def execute(self, context):
        ms = context.scene.maya_style
        ms.menu_set = self.name
        shelf_map = {
            'MODELING': 'MODEL',
            'RIGGING': 'RIG',
            'ANIMATION': 'ANIM',
            'FX': 'FX',
            'RENDERING': 'RENDER',
        }
        if self.name in shelf_map:
            ms.shelf = shelf_map[self.name]
        if context.screen:
            for area in context.screen.areas:
                if area.type in {'VIEW_3D', 'TOPBAR'}:
                    area.tag_redraw()
        return {'FINISHED'}


class MAYA_STYLE_OT_channel_toggle(bpy.types.Operator):
    bl_idname = 'maya_style.channel_toggle'
    bl_label = 'Channel Box / Modeling Toolkit / Attribute Editor'
    bl_description = 'Toggle or cycle the right-hand Baya sidebar dock (Ctrl+A)'
    mode: StringProperty(default='TOGGLE')

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'VIEW_3D'

    def execute(self, context):
        space = context.space_data
        ms = context.scene.maya_style
        if self.mode in {'ALL', 'CHANNEL_BOX', 'MODELING_TOOLKIT', 'ATTRIBUTE_EDITOR'}:
            ms.right_dock = self.mode
            space.show_region_ui = True
        else:
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
    bl_description = 'Show detailed attributes in the right Properties editor or Baya Attribute Editor'
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
        if hasattr(context.scene, 'maya_style'):
            context.scene.maya_style.right_dock = 'ATTRIBUTE_EDITOR'
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.show_region_ui = True
                    area.tag_redraw()
            return {'FINISHED'}
        self.report({'INFO'}, 'Use the Baya 3D workspace for the Attribute Editor')
        return {'CANCELLED'}


class MAYA_STYLE_OT_freeze(bpy.types.Operator):
    bl_idname = 'maya_style.freeze'
    bl_label = 'Freeze Transformations'
    bl_description = 'Freeze rotation and scale on selected objects (or use Modify > Freeze All)'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT' and bool(context.selected_editable_objects)

    def execute(self, context):
        return bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


class MAYA_STYLE_OT_layer_create(bpy.types.Operator):
    bl_idname = 'maya_style.layer_create'
    bl_label = 'Create Layer from Selected'
    bl_description = 'Create a new Display Layer (Collection) and assign selected objects to it'
    bl_options = {'REGISTER', 'UNDO'}
    name: StringProperty(name='Layer Name', default='layer1')

    def execute(self, context):
        base = self.name or 'layer1'
        idx = 1
        while f'layer{idx}' in bpy.data.collections and base == 'layer1':
            idx += 1
        coll_name = f'layer{idx}' if base == 'layer1' else base
        coll = bpy.data.collections.new(coll_name)
        context.scene.collection.children.link(coll)
        for obj in context.selected_objects:
            if obj.name not in coll.objects:
                coll.objects.link(obj)
        return {'FINISHED'}


SHAPES = [
    ('mesh.primitive_cube_add', 'Cube', 'MESH_CUBE'),
    ('mesh.primitive_uv_sphere_add', 'Sphere', 'MESH_UVSPHERE'),
    ('mesh.primitive_cylinder_add', 'Cylinder', 'MESH_CYLINDER'),
    ('mesh.primitive_cone_add', 'Cone', 'MESH_CONE'),
    ('mesh.primitive_plane_add', 'Plane', 'MESH_PLANE'),
    ('mesh.primitive_torus_add', 'Torus', 'MESH_TORUS'),
]


class MAYA_STYLE_MT_shelf_create(bpy.types.Menu):
    bl_label = 'Create'
    bl_idname = 'MAYA_STYLE_MT_shelf_create'

    def draw(self, context):
        col = self.layout
        col.label(text='Polygon Primitives', icon='MESH_DATA')
        for op, label, icon in SHAPES:
            col.operator(op, text=label, icon=icon)
        col.operator('mesh.primitive_ico_sphere_add', text='Platonic / Ico Sphere', icon='MESH_ICOSPHERE')
        col.operator('mesh.primitive_grid_add', text='Subdivided Plane / Grid', icon='MESH_GRID')
        col.operator('mesh.primitive_monkey_add', text='Test Mesh (Suzanne)', icon='MESH_MONKEY')
        col.separator()
        col.label(text='NURBS & Curve Primitives', icon='CURVE_DATA')
        col.operator('curve.primitive_bezier_curve_add', text='EP / Bezier Curve', icon='CURVE_BEZCURVE')
        col.operator('curve.primitive_bezier_circle_add', text='Bezier Circle', icon='CURVE_BEZCIRCLE')
        col.operator('curve.primitive_nurbs_curve_add', text='NURBS Curve', icon='CURVE_NCURVE')
        col.operator('curve.primitive_nurbs_circle_add', text='NURBS Circle', icon='CURVE_NCIRCLE')
        col.operator('surface.primitive_nurbs_surface_sphere_add', text='NURBS Sphere', icon='SURFACE_NSPHERE')
        col.operator('surface.primitive_nurbs_surface_cylinder_add', text='NURBS Cylinder', icon='SURFACE_NCYLINDER')
        col.separator()
        col.label(text='Lights, Cameras & Locators', icon='LIGHT')
        col.operator('maya_style.poly_action', text='Locator', icon='EMPTY_AXIS').action = 'LOCATOR'
        col.operator('object.camera_add', text='Camera', icon='CAMERA_DATA')
        col.operator('object.light_add', text='Directional / Sun Light', icon='LIGHT_SUN').type = 'SUN'
        col.operator('object.light_add', text='Point Light', icon='LIGHT_POINT').type = 'POINT'
        col.operator('object.light_add', text='Spot Light', icon='LIGHT_SPOT').type = 'SPOT'
        col.operator('object.light_add', text='Area Light', icon='LIGHT_AREA').type = 'AREA'
        col.separator()
        col.operator('object.armature_add', text='Joint / Armature', icon='ARMATURE_DATA')
        col.operator('object.text_add', text='3D Type / Text', icon='FONT_DATA')


class MAYA_STYLE_MT_select(bpy.types.Menu):
    bl_label = 'Select'
    bl_idname = 'MAYA_STYLE_MT_select'

    def draw(self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        namespace = {
            'OBJECT': 'object', 'EDIT_MESH': 'mesh', 'EDIT_CURVE': 'curve',
            'EDIT_SURFACE': 'curve', 'EDIT_ARMATURE': 'armature', 'POSE': 'pose',
            'EDIT_LATTICE': 'lattice', 'EDIT_METABALL': 'mball',
            'PARTICLE': 'particle', 'EDIT_GREASE_PENCIL': 'grease_pencil',
        }.get(context.mode)
        if namespace:
            for action, label, icon in [('SELECT', 'All  (Ctrl+Shift+A)', 'SELECT_SET'),
                                        ('DESELECT', 'Deselect All', 'SELECT_SUBTRACT'),
                                        ('INVERT', 'Inverse  (Ctrl+I)', 'SELECT_INTERSECT')]:
                lay.operator(namespace + '.select_all', text=label, icon=icon).action = action
            if namespace in {'object', 'mesh', 'curve', 'armature', 'lattice', 'particle', 'grease_pencil'}:
                lay.separator()
                lay.operator(namespace + '.select_more', text='Grow Selection  (>)', icon='ADD')
                lay.operator(namespace + '.select_less', text='Shrink Selection  (<)', icon='REMOVE')
        elif context.mode == 'EDIT_TEXT':
            lay.operator('font.select_all', text='Select All Text')
        else:
            lay.label(text='Selection follows the active mode')
        if context.mode == 'EDIT_MESH':
            lay.separator()
            lay.operator('mesh.loop_multi_select', text='Select Edge Loop', icon='EDGESEL').ring = False
            lay.operator('mesh.loop_multi_select', text='Select Edge Ring', icon='EDGESEL').ring = True
            lay.operator('mesh.region_to_loop', text='Select Boundary Loop', icon='MOD_EDGESPLIT')
            lay.operator('mesh.select_linked', text='Select Shell / Element', icon='MESH_DATA')
            lay.operator('mesh.select_similar', text='Select Similar', icon='SELECT_EXTEND')
            lay.separator()
            lay.operator('maya_style.poly_action', text='Convert to Vertices  (Ctrl+F9)', icon='VERTEXSEL').action = 'CONVERT_TO_VERTS'
            lay.operator('maya_style.poly_action', text='Convert to Edges  (Ctrl+F10)', icon='EDGESEL').action = 'CONVERT_TO_EDGES'
            lay.operator('maya_style.poly_action', text='Convert to Faces  (Ctrl+F11)', icon='FACESEL').action = 'CONVERT_TO_FACES'
        lay.separator()
        lay.operator('maya_style.component', text='Object Mode  (F8)', icon='OBJECT_DATA').mode = 'OBJECT'
        col = lay.column()
        col.enabled = context.object is not None and context.object.type == 'MESH'
        for mode, label, icon in [('VERT', 'Vertex  (F9)', 'VERTEXSEL'),
                                  ('EDGE', 'Edge  (F10)', 'EDGESEL'),
                                  ('FACE', 'Face  (F11)', 'FACESEL'),
                                  ('MULTI', 'Multi-Component', 'OBJECT_DATAMODE'),
                                  ('UV', 'UV  (F12)', 'UV')]:
            col.operator('maya_style.component', text=label, icon=icon).mode = mode
        lay.separator()
        lay.operator('maya_style.poly_action', text='Soft Selection Toggle  (B)', icon='PROP_ON').action = 'SOFT_SELECT_TOGGLE'


class MAYA_STYLE_MT_modify(bpy.types.Menu):
    bl_label = 'Modify'
    bl_idname = 'MAYA_STYLE_MT_modify'

    def draw(self, context):
        lay = self.layout
        lay.operator('maya_style.poly_action', text='Freeze Transformations (All)', icon='CHECKMARK').action = 'FREEZE_ALL'
        lay.operator('maya_style.freeze', text='Freeze Rotation & Scale', icon='CHECKMARK')
        lay.operator('maya_style.poly_action', text='Reset Transformations', icon='LOOP_BACK').action = 'RESET_TRANSFORMS'
        lay.separator()
        lay.operator('maya_style.poly_action', text='Center Pivot', icon='PIVOT_MEDIAN').action = 'CENTER_PIVOT'
        lay.operator('maya_style.pivot_mode', text='Pivot to Bottom (-Y)', icon='ANCHOR_BOTTOM').action = 'BOTTOM'
        lay.operator('maya_style.pivot_mode', text='Pivot to World Origin', icon='OBJECT_ORIGIN').action = 'ORIGIN'
        lay.operator('maya_style.pivot_mode', text='Edit Pivot Mode  (D / Insert)', icon='PIVOT_CURSOR').action = 'TOGGLE'
        lay.separator()
        lay.operator('maya_style.duplicate', text='Duplicate  (Ctrl+D)', icon='DUPLICATE')
        lay.operator('maya_style.poly_action', text='Group  (Ctrl+G)', icon='GROUP').action = 'GROUP'
        lay.operator('maya_style.poly_action', text='Ungroup', icon='UNLINKED').action = 'UNGROUP'
        lay.operator('object.parent_set', text='Parent  (P)', icon='CONSTRAINT_BONE').type = 'OBJECT'
        lay.operator('object.parent_clear', text='Unparent  (Shift+P)').type = 'CLEAR_KEEP_TRANSFORM'
        lay.separator()
        lay.operator('maya_style.poly_action', text='Delete Construction History', icon='MODIFIER_OFF').action = 'DELETE_HISTORY'
        lay.menu('OBJECT_MT_modifier_add', text='Add Deformer / Modifier', icon='MODIFIER')


class MAYA_STYLE_MT_display(bpy.types.Menu):
    bl_label = 'Display'
    bl_idname = 'MAYA_STYLE_MT_display'

    def draw(self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        ms = context.scene.maya_style
        lay.label(text='Heads Up Display (HUD)', icon='INFO')
        lay.prop(ms, 'show_hud', text='Show Viewport HUD')
        lay.prop(ms, 'show_hud_polycount', text='Poly Count')
        lay.prop(ms, 'show_hud_object', text='Object Details')
        lay.prop(ms, 'show_hud_camera', text='Camera & Coordinate Axis')
        lay.separator()
        lay.label(text='Coordinate System (XYZ)', icon='ORIENTATION_GLOBAL')
        lay.prop(ms, 'coord_system', expand=True)
        lay.separator()
        for level, label in [(1, 'Base Mesh  (1)'), (2, 'Cage + Smooth Preview  (2)'),
                             (3, 'Smooth Preview  (3)')]:
            lay.operator('maya_style.smooth_preview', text=label).level = level
        lay.separator()
        for mode, label, icon in [('WIREFRAME', 'Wireframe  (4)', 'SHADING_WIRE'),
                                  ('SOLID', 'Smooth Shaded  (5)', 'SHADING_SOLID'),
                                  ('MATERIAL', 'Hardware Texturing  (6)', 'SHADING_TEXTURE'),
                                  ('RENDERED', 'Use All Lights / Rendered  (7)', 'SHADING_RENDERED')]:
            lay.operator('maya_style.shading', text=label, icon=icon).mode = mode
        lay.separator()
        lay.operator('view3d.view_selected', text='Frame Selection  (F)', icon='ZOOM_SELECTED')
        lay.operator('view3d.view_all', text='Frame All  (A)', icon='HOME').center = False
        lay.operator('view3d.localview', text='Isolate Select  (Ctrl+1)', icon='HIDE_OFF')
        lay.separator()
        lay.operator('view3d.view_persportho', text='Perspective / Orthographic', icon='VIEW_PERSPECTIVE')
        lay.menu('VIEW3D_MT_view_viewpoint', text='Orthographic Views', icon='VIEW_ORTHO')
        lay.operator('view3d.view_camera', text='Look Through Selected Camera', icon='CAMERA_DATA')
        if context.space_data and context.space_data.type == 'VIEW_3D':
            lay.separator()
            lay.prop(context.space_data.overlay, 'show_floor', text='Grid')
            lay.prop(context.space_data.overlay, 'show_wireframes', text='Wireframe on Shaded')
            lay.prop(context.space_data.overlay, 'show_face_orientation', text='Face Orientation')
            lay.prop(context.space_data.overlay, 'show_overlays', text='Viewport Overlays')


class MAYA_STYLE_MT_mesh_menu(bpy.types.Menu):
    bl_label = 'Mesh'
    bl_idname = 'MAYA_STYLE_MT_mesh_menu'

    def draw(self, context):
        lay = self.layout
        lay.operator('maya_style.poly_action', text='Combine', icon='AUTOMERGE_ON').action = 'COMBINE'
        lay.operator('maya_style.poly_action', text='Separate', icon='MOD_EXPLODE').action = 'SEPARATE'
        lay.separator()
        lay.label(text='Booleans', icon='MOD_BOOLEAN')
        lay.operator('maya_style.poly_action', text='Union').action = 'BOOLEAN_UNION'
        lay.operator('maya_style.poly_action', text='Difference (A - B)').action = 'BOOLEAN_DIFFERENCE'
        lay.operator('maya_style.poly_action', text='Intersection').action = 'BOOLEAN_INTERSECT'
        lay.separator()
        lay.operator('maya_style.poly_action', text='Smooth', icon='MOD_SUBSURF').action = 'SMOOTH_MESH'
        lay.operator('maya_style.poly_action', text='Triangulate', icon='MOD_TRIANGULATE').action = 'TRIANGULATE'
        lay.operator('maya_style.poly_action', text='Quadrangulate (Tris to Quads)', icon='MESH_GRID').action = 'QUADRANGULATE'
        lay.operator('maya_style.poly_action', text='Fill Hole', icon='FACESEL').action = 'FILL_HOLE'
        lay.separator()
        lay.operator('maya_style.poly_action', text='Mirror X', icon='MOD_MIRROR').action = 'MIRROR_X'
        lay.operator('maya_style.poly_action', text='Mirror Y', icon='MOD_MIRROR').action = 'MIRROR_Y'
        lay.operator('maya_style.poly_action', text='Mirror Z', icon='MOD_MIRROR').action = 'MIRROR_Z'
        lay.separator()
        lay.operator('maya_style.poly_action', text='Reduce (Decimate)', icon='MOD_DECIM').action = 'REDUCE'
        lay.operator('maya_style.poly_action', text='Remesh (Voxel)', icon='MOD_REMESH').action = 'REMESH'


class MAYA_STYLE_MT_mesh(bpy.types.Menu):
    bl_label = 'Edit Mesh'
    bl_idname = 'MAYA_STYLE_MT_mesh'

    def draw(self, context):
        lay = self.layout
        if context.mode != 'EDIT_MESH':
            lay.operator('maya_style.component', text='Enter Component Mode (F9-F11)', icon='EDITMODE_HLT').mode = 'FACE'
            lay.separator()
        lay.operator('mesh.extrude_region_move', text='Extrude  (Ctrl+E)', icon='MOD_SOLIDIFY')
        lay.operator('mesh.bevel', text='Bevel  (Ctrl+B)', icon='MOD_BEVEL')
        lay.operator('mesh.bridge_edge_loops', text='Bridge', icon='MOD_BUILD')
        lay.operator('mesh.inset', text='Inset Faces', icon='FACESEL')
        lay.separator()
        lay.operator('maya_style.poly_action', text='Extract Faces', icon='MOD_EXPLODE').action = 'EXTRACT_FACES'
        lay.operator('maya_style.poly_action', text='Duplicate Faces', icon='DUPLICATE').action = 'DUPLICATE_FACES'
        lay.operator('maya_style.poly_action', text='Poke Faces', icon='VERTEXSEL').action = 'POKE'
        lay.operator('maya_style.poly_action', text='Circularize Components', icon='MESH_CIRCLE').action = 'CIRCULARIZE'
        lay.separator()
        lay.operator('mesh.merge', text='Merge to Center', icon='AUTOMERGE_ON').type = 'CENTER'
        lay.operator('mesh.remove_doubles', text='Merge by Distance', icon='AUTOMERGE_ON')
        lay.operator('mesh.split', text='Detach Components', icon='UNLINKED')
        lay.operator('maya_style.poly_action', text='Delete Edge/Vertex  (Ctrl+Del)', icon='X').action = 'DELETE_EDGE_VERTEX'
        lay.separator()
        lay.operator('mesh.subdivide', text='Add Divisions (Subdivide)', icon='MESH_GRID')


class MAYA_STYLE_MT_mesh_tools(bpy.types.Menu):
    bl_label = 'Mesh Tools'
    bl_idname = 'MAYA_STYLE_MT_mesh_tools'

    def draw(self, context):
        lay = self.layout
        lay.operator('mesh.loopcut_slide', text='Insert Edge Loop', icon='MOD_EDGESPLIT')
        lay.operator('mesh.knife_tool', text='Multi-Cut / Knife Tool', icon='MOD_TRIANGULATE')
        lay.operator('mesh.offset_edge_loops_slide', text='Offset Edge Loop', icon='EDGESEL')
        lay.operator('mesh.vert_connect_path', text='Connect Components', icon='VERTEXSEL')
        lay.separator()
        lay.operator('transform.edge_slide', text='Slide Edge Tool', icon='EDGESEL')
        lay.operator('transform.vert_slide', text='Slide Vertex Tool', icon='VERTEXSEL')
        lay.operator('wm.tool_set_by_id', text='Target Weld / Poly Build (Quad Draw)', icon='SNAP_VERTEX').name = 'builtin.poly_build'
        lay.operator('mesh.rip_move', text='Rip Region', icon='UNLINKED')


class MAYA_STYLE_MT_mesh_display(bpy.types.Menu):
    bl_label = 'Mesh Display'
    bl_idname = 'MAYA_STYLE_MT_mesh_display'

    def draw(self, context):
        lay = self.layout
        lay.operator('maya_style.poly_action', text='Soften Edge', icon='SHADING_SOLID').action = 'SOFTEN_EDGE'
        lay.operator('maya_style.poly_action', text='Harden Edge', icon='SHADING_WIRE').action = 'HARDEN_EDGE'
        lay.separator()
        lay.operator('maya_style.poly_action', text='Reverse Normals', icon='FILE_REFRESH').action = 'REVERSE_NORMALS'
        lay.operator('maya_style.poly_action', text='Conform / Recalculate Normals', icon='NORMALS_FACE').action = 'CONFORM_NORMALS'
        if context.mode == 'EDIT_MESH':
            lay.separator()
            lay.operator('mesh.mark_sharp', text='Harden Selected Edges (Mark Sharp)')
            lay.operator('mesh.mark_sharp', text='Soften Selected Edges (Clear Sharp)').clear = True


class MAYA_STYLE_MT_curves(bpy.types.Menu):
    bl_label = 'Curves'
    bl_idname = 'MAYA_STYLE_MT_curves'

    def draw(self, context):
        lay = self.layout
        lay.operator('curve.primitive_bezier_curve_add', text='EP / Bezier Curve Tool', icon='CURVE_BEZCURVE')
        lay.operator('curve.primitive_nurbs_curve_add', text='CV / NURBS Curve Tool', icon='CURVE_NCURVE')
        lay.operator('curve.primitive_bezier_circle_add', text='Bezier Circle', icon='CURVE_BEZCIRCLE')
        lay.operator('curve.primitive_nurbs_circle_add', text='NURBS Circle', icon='CURVE_NCIRCLE')
        lay.separator()
        lay.operator('object.convert', text='Convert Curve to Mesh', icon='MESH_DATA').target = 'MESH'
        lay.operator('object.convert', text='Convert Mesh Edge to Curve', icon='CURVE_DATA').target = 'CURVE'


class MAYA_STYLE_MT_surfaces(bpy.types.Menu):
    bl_label = 'Surfaces'
    bl_idname = 'MAYA_STYLE_MT_surfaces'

    def draw(self, context):
        lay = self.layout
        lay.operator('surface.primitive_nurbs_surface_sphere_add', text='NURBS Sphere', icon='SURFACE_NSPHERE')
        lay.operator('surface.primitive_nurbs_surface_cylinder_add', text='NURBS Cylinder', icon='SURFACE_NCYLINDER')
        lay.operator('surface.primitive_nurbs_surface_torus_add', text='NURBS Torus', icon='SURFACE_NTORUS')
        lay.operator('surface.primitive_nurbs_surface_surface_add', text='NURBS Plane / Patch', icon='SURFACE_NSURFACE')
        lay.separator()
        lay.operator('object.convert', text='Convert NURBS to Polygons', icon='MESH_DATA').target = 'MESH'


class MAYA_STYLE_MT_deform(bpy.types.Menu):
    bl_label = 'Deform'
    bl_idname = 'MAYA_STYLE_MT_deform'

    def draw(self, context):
        lay = self.layout
        lay.operator('object.modifier_add', text='Lattice', icon='MOD_LATTICE').type = 'LATTICE'
        lay.operator('object.modifier_add', text='Nonlinear Bend / Twist / Taper', icon='MOD_SIMPLEDEFORM').type = 'SIMPLE_DEFORM'
        lay.operator('object.modifier_add', text='Curve Warp', icon='MOD_CURVE').type = 'CURVE'
        lay.operator('object.modifier_add', text='Shrinkwrap', icon='MOD_SHRINKWRAP').type = 'SHRINKWRAP'
        lay.operator('object.modifier_add', text='Smooth / Corrective Smooth', icon='MOD_SMOOTH').type = 'CORRECTIVE_SMOOTH'
        lay.operator('object.modifier_add', text='Wave Deformer', icon='MOD_WAVE').type = 'WAVE'
        lay.operator('object.modifier_add', text='Displace', icon='MOD_DISPLACE').type = 'DISPLACE'


class MAYA_STYLE_MT_uv_menu(bpy.types.Menu):
    bl_label = 'UV'
    bl_idname = 'MAYA_STYLE_MT_uv_menu'

    def draw(self, context):
        lay = self.layout
        lay.operator('maya_style.workspace', text='UV Editor', icon='UV').name = 'UV Editing'
        lay.separator()
        lay.operator('uv.unwrap', text='Unfold / Unwrap', icon='UV')
        lay.operator('uv.smart_project', text='Automatic Mapping (Smart UV)', icon='MOD_UVPROJECT')
        lay.operator('uv.cube_project', text='Cube Projection', icon='MESH_CUBE')
        lay.operator('uv.cylinder_project', text='Cylindrical Projection', icon='MESH_CYLINDER')
        lay.operator('uv.sphere_project', text='Spherical Projection', icon='MESH_UVSPHERE')
        lay.operator('uv.project_from_view', text='Camera-Based Projection', icon='CAMERA_DATA')
        if context.mode == 'EDIT_MESH':
            lay.separator()
            lay.operator('mesh.mark_seam', text='Cut UV Edges (Mark Seam)', icon='EDGESEL').clear = False
            lay.operator('mesh.mark_seam', text='Sew UV Edges (Clear Seam)', icon='EDGESEL').clear = True


class MAYA_STYLE_MT_skeleton(bpy.types.Menu):
    bl_label = 'Skeleton'
    bl_idname = 'MAYA_STYLE_MT_skeleton'

    def draw(self, context):
        lay = self.layout
        lay.operator('object.armature_add', text='Create Joints', icon='ARMATURE_DATA')
        if context.mode == 'EDIT_ARMATURE':
            lay.operator('armature.extrude_move', text='Insert / Extrude Joint', icon='BONE_DATA')
            lay.operator('armature.symmetrize', text='Mirror Joints', icon='MOD_MIRROR')
            lay.operator('armature.parent_set', text='Connect Joint').type = 'CONNECTED'
            lay.operator('armature.calculate_roll', text='Orient Joint')
        if context.object and context.object.type == 'ARMATURE':
            lay.separator()
            lay.operator('object.mode_set', text='Edit Joints', icon='EDITMODE_HLT').mode = 'EDIT'
            lay.operator('object.mode_set', text='Pose Joints', icon='POSE_HLT').mode = 'POSE'


class MAYA_STYLE_MT_skin(bpy.types.Menu):
    bl_label = 'Skin'
    bl_idname = 'MAYA_STYLE_MT_skin'

    def draw(self, context):
        lay = self.layout
        lay.operator('object.parent_set', text='Bind Skin (Automatic Weights)', icon='MOD_ARMATURE').type = 'ARMATURE_AUTO'
        lay.operator('object.parent_set', text='Bind Skin (Envelope Weights)', icon='MOD_ARMATURE').type = 'ARMATURE_ENVELOPE'
        lay.operator('object.parent_clear', text='Unbind Skin', icon='UNLINKED').type = 'CLEAR_KEEP_TRANSFORM'
        if context.object and context.object.type == 'MESH':
            lay.separator()
            lay.operator('paint.weight_paint_toggle', text='Paint Skin Weights Tool', icon='WPAINT_HLT')


class MAYA_STYLE_MT_constrain(bpy.types.Menu):
    bl_label = 'Constrain'
    bl_idname = 'MAYA_STYLE_MT_constrain'

    def draw(self, context):
        lay = self.layout
        lay.operator('object.parent_set', text='Parent  (P)', icon='CONSTRAINT_BONE').type = 'OBJECT'
        lay.operator('object.constraint_add', text='Parent Constraint (Child Of)', icon='CONSTRAINT').type = 'CHILD_OF'
        lay.operator('object.constraint_add', text='Point Constraint (Copy Location)', icon='CON_LOCLIKE').type = 'COPY_LOCATION'
        lay.operator('object.constraint_add', text='Orient Constraint (Copy Rotation)', icon='CON_ROTLIKE').type = 'COPY_ROTATION'
        lay.operator('object.constraint_add', text='Scale Constraint (Copy Scale)', icon='CON_SIZELIKE').type = 'COPY_SCALE'
        lay.operator('object.constraint_add', text='Aim Constraint (Track To)', icon='CON_TRACKTO').type = 'TRACK_TO'
        lay.operator('object.constraint_add', text='Pole Vector / Damped Track', icon='CON_DAMPTRACK').type = 'DAMPED_TRACK'


class MAYA_STYLE_MT_key(bpy.types.Menu):
    bl_label = 'Key'
    bl_idname = 'MAYA_STYLE_MT_key'

    def draw(self, context):
        lay = self.layout
        lay.operator('anim.keyframe_insert_by_name', text='Set Key  (S)', icon='KEY_HLT').type = 'LocRotScale'
        lay.operator('anim.keyframe_insert_by_name', text='Key Translate  (Shift+W)', icon='CON_LOCLIKE').type = 'Location'
        lay.operator('anim.keyframe_insert_by_name', text='Key Rotate  (Shift+E)', icon='CON_ROTLIKE').type = 'Rotation'
        lay.operator('anim.keyframe_insert_by_name', text='Key Scale  (Shift+R)', icon='CON_SIZELIKE').type = 'Scaling'
        lay.separator()
        lay.operator('anim.keyframe_delete_v3d', text='Delete Keys on Current Frame', icon='KEY_DEHLT')
        lay.prop(context.scene.tool_settings, 'use_keyframe_insert_auto', text='Auto Keyframe Toggle', icon='REC')


class MAYA_STYLE_MT_playback(bpy.types.Menu):
    bl_label = 'Playback'
    bl_idname = 'MAYA_STYLE_MT_playback'

    def draw(self, context):
        lay = self.layout
        lay.operator('screen.animation_play', text='Play / Pause  (Alt+V)', icon='PLAY')
        lay.operator('screen.frame_jump', text='Go to Start Frame', icon='REW').end = False
        lay.operator('screen.frame_jump', text='Go to End Frame', icon='FF').end = True
        lay.operator('screen.keyframe_jump', text='Previous Key  (,)', icon='PREV_KEYFRAME').next = False
        lay.operator('screen.keyframe_jump', text='Next Key  (.)', icon='NEXT_KEYFRAME').next = True
        lay.separator()
        lay.operator('render.opengl', text='Playblast (Viewport Animation)', icon='RENDER_ANIMATION').animation = True


class MAYA_STYLE_MT_fx_menu(bpy.types.Menu):
    bl_label = 'FX / Dynamics'
    bl_idname = 'MAYA_STYLE_MT_fx_menu'

    def draw(self, context):
        lay = self.layout
        lay.operator('object.modifier_add', text='Bifrost / Geometry Nodes Graph', icon='GEOMETRY_NODES').type = 'NODES'
        lay.operator('object.modifier_add', text='nCloth (Cloth Simulation)', icon='MOD_CLOTH').type = 'CLOTH'
        lay.operator('object.modifier_add', text='Passive Collider (Collision)', icon='MOD_PHYSICS').type = 'COLLISION'
        lay.operator('object.modifier_add', text='nParticles (Particle System)', icon='PARTICLES').type = 'PARTICLE_SYSTEM'
        lay.operator('object.modifier_add', text='Fluid / Smoke Domain', icon='MOD_FLUIDSIM').type = 'FLUID'
        lay.operator('object.modifier_add', text='Boss / Ocean Surface', icon='MOD_OCEAN').type = 'OCEAN'


class MAYA_STYLE_MT_shading_menu(bpy.types.Menu):
    bl_label = 'Lighting/Shading'
    bl_idname = 'MAYA_STYLE_MT_shading_menu'

    def draw(self, context):
        lay = self.layout
        lay.label(text='Assign New Material', icon='MATERIAL')
        for preset, label in [
            ('STANDARD_SURFACE', 'Standard Surface'),
            ('LAMBERT', 'Lambert (Matte)'),
            ('BLINN', 'Blinn'),
            ('PHONG', 'Phong (Glossy)'),
            ('SURFACE_SHADER', 'Surface Shader (Emission)'),
        ]:
            lay.operator('maya_style.assign_shader', text=label, icon='SHADING_RENDERED').shader_type = preset
        lay.separator()
        lay.operator('maya_style.workspace', text='Hypershade / Shader Editor', icon='NODE_MATERIAL').name = 'Materials'


class MAYA_STYLE_MT_render_menu(bpy.types.Menu):
    bl_label = 'Render'
    bl_idname = 'MAYA_STYLE_MT_render_menu'

    def draw(self, context):
        lay = self.layout
        lay.operator('render.render', text='Render Current Frame', icon='RENDER_STILL')
        lay.operator('render.render', text='Render Sequence / Animation', icon='RENDER_ANIMATION').animation = True
        lay.operator('render.view_show', text='Open Render View', icon='IMAGE_DATA')
        lay.separator()
        lay.prop(context.scene.render, 'engine', text='Renderer')


class MAYA_STYLE_MT_windows(bpy.types.Menu):
    bl_label = 'Windows'
    bl_idname = 'MAYA_STYLE_MT_windows'

    def draw(self, context):
        lay = self.layout
        lay.operator_context = 'INVOKE_REGION_WIN'
        lay.label(text='General Editors', icon='WINDOW')
        lay.operator('maya_style.channel_toggle', text='Channel Box / Layer Editor', icon='PROPERTIES').mode = 'CHANNEL_BOX'
        lay.operator('maya_style.channel_toggle', text='Modeling Toolkit', icon='MOD_BUILD').mode = 'MODELING_TOOLKIT'
        lay.operator('maya_style.channel_toggle', text='Attribute Editor', icon='PREFERENCES').mode = 'ATTRIBUTE_EDITOR'
        lay.operator('maya_style.channel_toggle', text='Show All Right-Dock Panels', icon='MENU_PANEL').mode = 'ALL'
        lay.separator()
        lay.label(text='Workspaces / Specialized Editors', icon='WORKSPACE')
        for name, label, icon in [
            ('Baya 3D', 'Baya 3D Main Viewport', 'VIEW3D'),
            ('UV Editing', 'UV Editor', 'UV'),
            ('Animation', 'Graph Editor / Dope Sheet', 'ANIM'),
            ('Materials', 'Hypershade / Node Editor', 'NODE_MATERIAL'),
            ('Rendering', 'Render View', 'RENDER_STILL'),
            ('Procedural FX', 'Bifrost / Geometry Nodes', 'GEOMETRY_NODES'),
            ('Scripting', 'Script Editor (MEL / Python)', 'CONSOLE'),
        ]:
            lay.operator('maya_style.workspace', text=label, icon=icon).name = name
        lay.separator()
        lay.operator('screen.region_quadview', text='Four View / Single View  (Space)', icon='VIEW_ORTHO')
        lay.operator('wm.call_menu_pie', text='Hotbox  (Hold Space)', icon='MENU_PANEL').name = 'MAYA_STYLE_MT_hotbox'


class MAYA_STYLE_MT_main(bpy.types.Menu):
    bl_label = 'Baya 3D'
    bl_idname = 'MAYA_STYLE_MT_main'

    def draw(self, context):
        lay = self.layout
        lay.menu('MAYA_STYLE_MT_shelf_create')
        lay.menu('MAYA_STYLE_MT_select')
        lay.menu('MAYA_STYLE_MT_modify')
        lay.menu('MAYA_STYLE_MT_mesh_menu')
        lay.menu('MAYA_STYLE_MT_mesh')
        lay.menu('MAYA_STYLE_MT_mesh_tools')
        lay.menu('MAYA_STYLE_MT_mesh_display')
        lay.menu('MAYA_STYLE_MT_uv_menu')
        lay.menu('MAYA_STYLE_MT_display')
        lay.menu('MAYA_STYLE_MT_windows')
        lay.separator()
        lay.operator('baya.about', text='About Baya 3D / Controls', icon='INFO')
        lay.separator()
        lay.operator('wm.search_menu', text='Search All Commands (Tab)', icon='VIEWZOOM')


class MAYA_STYLE_OT_about(bpy.types.Operator):
    bl_idname = 'baya.about'
    bl_label = 'About Baya 3D'
    bl_description = 'Baya 3D version, Blender engine attribution and essential Maya-style controls'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=560)

    def execute(self, context):
        return {'FINISHED'}

    def draw(self, context):
        lay = self.layout
        lay.label(text='Baya 3D — Full Maya-Style Experience', icon='VIEW3D')
        lay.label(text='Clean-room Maya-inspired UI, Status Line, Shelves, Channel Box, Modeling Toolkit & HUD.')
        lay.label(text='Powered by Blender ' + bpy.app.version_string + ' (GPL-3.0-or-later)')
        lay.separator()
        draw_shortcuts(lay)


def workspace_button(lay, name, text, icon):
    lay.operator('maya_style.workspace', text=text, icon=icon).name = name


def _draw_status_line(lay, context):
    """Draw Maya's Status Line icons (Menu Set, Selection Masks, Snapping, History, Render)."""
    ms = context.scene.maya_style
    ts = context.scene.tool_settings

    # Menu Set Dropdown
    sub = lay.row(align=True)
    sub.ui_units_x = 5.4
    sub.prop(ms, 'menu_set', text='')

    # File quick actions
    f_row = lay.row(align=True)
    f_row.operator('wm.read_homefile', text='', icon='FILE_NEW')
    f_row.operator('wm.open_mainfile', text='', icon='FILE_FOLDER')
    f_row.operator('wm.save_mainfile', text='', icon='FILE_TICK')
    f_row.operator('ed.undo', text='', icon='LOOP_BACK')
    f_row.operator('ed.redo', text='', icon='LOOP_FORWARDS')

    lay.separator(factor=0.6)

    # Selection Masks: Object (F8), Vertex (F9), Edge (F10), Face (F11), UV (F12), Multi
    m_row = lay.row(align=True)
    is_obj = context.mode == 'OBJECT'
    m_row.operator('maya_style.component', text='Obj', depress=is_obj, icon='OBJECT_DATA').mode = 'OBJECT'
    sel_mode = tuple(ts.mesh_select_mode) if context.mode == 'EDIT_MESH' else (False, False, False)
    m_row.operator('maya_style.component', text='', depress=(context.mode == 'EDIT_MESH' and sel_mode == (True, False, False)), icon='VERTEXSEL').mode = 'VERT'
    m_row.operator('maya_style.component', text='', depress=(context.mode == 'EDIT_MESH' and sel_mode == (False, True, False)), icon='EDGESEL').mode = 'EDGE'
    m_row.operator('maya_style.component', text='', depress=(context.mode == 'EDIT_MESH' and sel_mode == (False, False, True)), icon='FACESEL').mode = 'FACE'
    m_row.operator('maya_style.component', text='', depress=(context.mode == 'EDIT_MESH' and sel_mode == (True, True, True)), icon='OBJECT_DATAMODE').mode = 'MULTI'
    m_row.operator('maya_style.component', text='', depress=False, icon='UV').mode = 'UV'

    lay.separator(factor=0.6)

    # Snapping Masks: Grid (X), Curve/Edge (C), Point/Vertex (V), Pivot (D), Soft Select (B), Symmetry
    s_row = lay.row(align=True)
    snap_elems = set(ts.snap_elements)
    op = s_row.operator('maya_style.snap_hold', text='', depress=(ts.use_snap and 'INCREMENT' in snap_elems), icon='SNAP_GRID')
    op.mode = 'GRID'
    op.toggle = True
    op = s_row.operator('maya_style.snap_hold', text='', depress=(ts.use_snap and 'EDGE' in snap_elems), icon='SNAP_EDGE')
    op.mode = 'CURVE'
    op.toggle = True
    op = s_row.operator('maya_style.snap_hold', text='', depress=(ts.use_snap and 'VERTEX' in snap_elems), icon='SNAP_VERTEX')
    op.mode = 'POINT'
    op.toggle = True
    s_row.operator('maya_style.pivot_mode', text='', depress=bool(getattr(ts, 'use_transform_data_origin', False)), icon='PIVOT_CURSOR').action = 'TOGGLE'
    s_row.operator('maya_style.poly_action', text='', depress=bool(ts.use_proportional_edit), icon='PROP_ON').action = 'SOFT_SELECT_TOGGLE'

    if context.object and context.object.type == 'MESH':
        s_row.prop(context.object.data, 'use_mirror_x', text='SymX', toggle=True, icon='MOD_MIRROR')

    lay.separator(factor=0.6)

    # Construction History & Transform Quick Buttons
    h_row = lay.row(align=True)
    h_row.operator('maya_style.poly_action', text='', icon='PIVOT_MEDIAN').action = 'CENTER_PIVOT'
    h_row.operator('maya_style.poly_action', text='', icon='MODIFIER_OFF').action = 'DELETE_HISTORY'
    h_row.operator('maya_style.poly_action', text='', icon='CHECKMARK').action = 'FREEZE_ALL'


def draw_shelf(self, context):
    """Draw Maya's Status Line + Tabbed Tool Shelf in the 3D Viewport tool-header."""
    lay = self.layout
    if (context.mode.startswith(('SCULPT', 'PAINT')) or context.mode in {
            'PARTICLE', 'WEIGHT_GPENCIL', 'VERTEX_GPENCIL',
            'WEIGHT_GREASE_PENCIL', 'VERTEX_GREASE_PENCIL'}):
        lay.menu('MAYA_STYLE_MT_main', text='Baya 3D')
        if _original_tool_header:
            _original_tool_header(self, context)
        return

    ms = context.scene.maya_style
    if ms.show_status_line:
        _draw_status_line(lay, context)
        lay.separator(factor=0.8)

    # Shelf Tab Selector
    shelf_sub = lay.row(align=True)
    shelf_sub.ui_units_x = 5.2
    shelf_sub.prop(ms, 'shelf', text='')

    shelf = ms.shelf
    row = lay.row(align=True)
    if shelf == 'CURVES':
        row.operator('curve.primitive_bezier_curve_add', text='EP Curve', icon='CURVE_BEZCURVE')
        row.operator('curve.primitive_nurbs_curve_add', text='CV Curve', icon='CURVE_NCURVE')
        row.operator('curve.primitive_bezier_circle_add', text='Circle', icon='CURVE_BEZCIRCLE')
        row.operator('surface.primitive_nurbs_surface_sphere_add', text='Sphere', icon='SURFACE_NSPHERE')
        row.operator('surface.primitive_nurbs_surface_cylinder_add', text='Cylinder', icon='SURFACE_NCYLINDER')
        row.separator()
        row.operator('maya_style.poly_action', text='Locator', icon='EMPTY_AXIS').action = 'LOCATOR'
        row.operator('object.convert', text='To Poly', icon='MESH_DATA').target = 'MESH'
    elif shelf == 'MODEL':
        for op, label, icon in SHAPES:
            row.operator(op, text='', icon=icon)
        row.operator('object.text_add', text='', icon='FONT_DATA')
        row.separator()
        if context.mode == 'EDIT_MESH':
            row.operator('mesh.extrude_region_move', text='Extrude', icon='MOD_SOLIDIFY')
            row.operator('mesh.bevel', text='Bevel', icon='MOD_BEVEL')
            row.operator('mesh.bridge_edge_loops', text='Bridge', icon='MOD_BUILD')
            row.operator('mesh.loopcut_slide', text='Loop', icon='MOD_EDGESPLIT')
            row.operator('mesh.knife_tool', text='Multi-Cut', icon='MOD_TRIANGULATE')
            row.operator('mesh.merge', text='Merge', icon='AUTOMERGE_ON').type = 'CENTER'
        else:
            row.operator('maya_style.poly_action', text='Combine', icon='AUTOMERGE_ON').action = 'COMBINE'
            row.operator('maya_style.poly_action', text='Separate', icon='MOD_EXPLODE').action = 'SEPARATE'
            row.operator('maya_style.poly_action', text='Smooth', icon='MOD_SUBSURF').action = 'SMOOTH_MESH'
            row.operator('maya_style.poly_action', text='Bool -', icon='MOD_BOOLEAN').action = 'BOOLEAN_DIFFERENCE'
            row.operator('maya_style.poly_action', text='Mirror', icon='MOD_MIRROR').action = 'MIRROR_X'
            row.operator('maya_style.component', text='Edit', icon='EDITMODE_HLT').mode = 'FACE'
    elif shelf == 'SCULPT':
        workspace_button(row, 'Sculpting', 'Sculpt Mode', 'SCULPTMODE_HLT')
        row.operator('object.shade_smooth', text='Smooth Shade', icon='SHADING_SOLID')
        row.operator('object.modifier_add', text='Subdiv', icon='MOD_SUBSURF').type = 'SUBSURF'
        row.operator('object.modifier_add', text='Multires', icon='MOD_MULTIRES').type = 'MULTIRES'
        row.operator('maya_style.poly_action', text='Voxel Remesh', icon='MOD_REMESH').action = 'REMESH'
        row.operator('maya_style.poly_action', text='Decimate', icon='MOD_DECIM').action = 'REDUCE'
    elif shelf == 'UV':
        workspace_button(row, 'UV Editing', 'UV Editor', 'UV')
        row.operator('uv.unwrap', text='Unfold', icon='UV')
        row.operator('uv.smart_project', text='Auto UV', icon='MOD_UVPROJECT')
        row.operator('uv.cube_project', text='Planar/Cube', icon='MESH_CUBE')
        row.operator('uv.cylinder_project', text='Cylindrical', icon='MESH_CYLINDER')
        if context.mode == 'EDIT_MESH':
            row.operator('mesh.mark_seam', text='Cut Seam', icon='EDGESEL').clear = False
            row.operator('mesh.mark_seam', text='Sew Seam', icon='EDGESEL').clear = True
    elif shelf == 'RIG':
        row.operator('object.armature_add', text='Joint', icon='ARMATURE_DATA')
        row.operator('maya_style.poly_action', text='Locator', icon='EMPTY_AXIS').action = 'LOCATOR'
        row.operator('object.parent_set', text='Bind Skin', icon='MOD_ARMATURE').type = 'ARMATURE_AUTO'
        row.operator('paint.weight_paint_toggle', text='Weights', icon='WPAINT_HLT')
        row.operator('object.parent_set', text='Parent', icon='CONSTRAINT_BONE').type = 'OBJECT'
        row.operator('object.constraint_add', text='Parent Con', icon='CONSTRAINT').type = 'CHILD_OF'
        row.operator('object.constraint_add', text='Aim Con', icon='CON_TRACKTO').type = 'TRACK_TO'
        row.operator('object.modifier_add', text='Lattice', icon='MOD_LATTICE').type = 'LATTICE'
    elif shelf == 'ANIM':
        row.operator('anim.keyframe_insert_by_name', text='Set Key (S)', icon='KEY_HLT').type = 'LocRotScale'
        row.operator('screen.animation_play', text='Play', icon='PLAY')
        row.operator('screen.keyframe_jump', text='', icon='PREV_KEYFRAME').next = False
        row.operator('screen.keyframe_jump', text='', icon='NEXT_KEYFRAME').next = True
        row.prop(context.scene.tool_settings, 'use_keyframe_insert_auto', text='AutoKey', icon='REC')
        workspace_button(row, 'Animation', 'Graph Editor', 'GRAPH')
        row.operator('render.opengl', text='Playblast', icon='RENDER_ANIMATION').animation = True
    elif shelf == 'RENDER':
        row.operator('maya_style.assign_shader', text='Std Surface', icon='MATERIAL').shader_type = 'STANDARD_SURFACE'
        row.operator('maya_style.assign_shader', text='Lambert', icon='SHADING_SOLID').shader_type = 'LAMBERT'
        row.operator('maya_style.assign_shader', text='Blinn', icon='SHADING_RENDERED').shader_type = 'BLINN'
        row.separator()
        row.operator('object.light_add', text='Area', icon='LIGHT_AREA').type = 'AREA'
        row.operator('object.light_add', text='Sun', icon='LIGHT_SUN').type = 'SUN'
        row.operator('object.light_add', text='Point', icon='LIGHT_POINT').type = 'POINT'
        row.operator('object.camera_add', text='Cam', icon='CAMERA_DATA')
        row.separator()
        workspace_button(row, 'Materials', 'Hypershade', 'NODE_MATERIAL')
        row.operator('render.render', text='Render', icon='RENDER_STILL')
    else:
        workspace_button(row, 'Procedural FX', 'Bifrost / Nodes', 'GEOMETRY_NODES')
        row.operator('object.modifier_add', text='nCloth', icon='MOD_CLOTH').type = 'CLOTH'
        row.operator('object.modifier_add', text='Collider', icon='MOD_PHYSICS').type = 'COLLISION'
        row.operator('object.modifier_add', text='nParticles', icon='PARTICLES').type = 'PARTICLE_SYSTEM'
        row.operator('object.modifier_add', text='Fluid', icon='MOD_FLUIDSIM').type = 'FLUID'
        row.operator('object.modifier_add', text='Ocean', icon='MOD_OCEAN').type = 'OCEAN'

    lay.separator_spacer()

    # Right-Dock Workspace Toggles: Channel Box | Modeling Toolkit | Attribute Editor
    r_row = lay.row(align=True)
    r_row.operator('maya_style.channel_toggle', text='CB', depress=(ms.right_dock in {'ALL', 'CHANNEL_BOX'}), icon='PROPERTIES').mode = 'CHANNEL_BOX'
    r_row.operator('maya_style.channel_toggle', text='MTK', depress=(ms.right_dock in {'ALL', 'MODELING_TOOLKIT'}), icon='MOD_BUILD').mode = 'MODELING_TOOLKIT'
    r_row.operator('maya_style.channel_toggle', text='AE', depress=(ms.right_dock in {'ALL', 'ATTRIBUTE_EDITOR'}), icon='PREFERENCES').mode = 'ATTRIBUTE_EDITOR'
    r_row.operator('maya_style.channel_toggle', text='', icon='HIDE_OFF').mode = 'TOGGLE'
    r_row.popover(panel='VIEW3D_PT_active_tool', text='', icon='TOOL_SETTINGS')


class MAYA_STYLE_PT_dock_switcher(bpy.types.Panel):
    bl_label = 'Baya Right Dock'
    bl_idname = 'MAYA_STYLE_PT_dock_switcher'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_options = {'HIDE_HEADER'}
    bl_order = -110

    def draw(self, context):
        lay = self.layout
        ms = context.scene.maya_style
        row = lay.row(align=True)
        row.prop_enum(ms, 'right_dock', 'ALL', text='All', icon='MENU_PANEL')
        row.prop_enum(ms, 'right_dock', 'CHANNEL_BOX', text='CB', icon='PROPERTIES')
        row.prop_enum(ms, 'right_dock', 'MODELING_TOOLKIT', text='MTK', icon='MOD_BUILD')
        row.prop_enum(ms, 'right_dock', 'ATTRIBUTE_EDITOR', text='AE', icon='PREFERENCES')
        coord_row = lay.row(align=True)
        coord_row.prop(ms, 'coord_system', expand=True)


class MAYA_STYLE_PT_channels(bpy.types.Panel):
    bl_label = 'Channel Box'
    bl_idname = 'MAYA_STYLE_PT_channels'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -100

    @classmethod
    def poll(cls, context):
        ms = getattr(context.scene, 'maya_style', None)
        return ms is None or ms.right_dock in {'ALL', 'CHANNEL_BOX'}

    def draw(self, context):
        lay = self.layout
        obj = context.object
        ms = context.scene.maya_style
        if obj is None:
            lay.label(text='No object selected', icon='RESTRICT_SELECT_OFF')
            lay.label(text='Create from the Shelf or Shift+RMB.')
            return

        row = lay.row(align=True)
        row.prop(obj, 'name', text='', icon='OBJECT_DATA')
        row.operator('maya_style.poly_action', text='', icon='PIVOT_MEDIAN').action = 'CENTER_PIVOT'
        row.operator('maya_style.poly_action', text='', icon='CHECKMARK').action = 'FREEZE_ALL'

        target = _active_transform_target(context)
        if target != obj:
            lay.label(text=f'Bone: {target.name}', icon='BONE_DATA')

        is_yup = ms.coord_system == 'MAYA_Y_UP'
        axis_tag = ' (Y-Up)' if is_yup else ' (Z-Up)'

        col = lay.column(align=True)
        if is_yup:
            for attr, label in [('maya_tx', 'Translate X'), ('maya_ty', 'Translate Y'), ('maya_tz', 'Translate Z')]:
                r = col.row(align=True)
                r.label(text=label)
                r.prop(ms, attr, text='')
            col.separator(factor=0.35)
            for attr, label in [('maya_rx', 'Rotate X'), ('maya_ry', 'Rotate Y'), ('maya_rz', 'Rotate Z')]:
                r = col.row(align=True)
                r.label(text=label)
                r.prop(ms, attr, text='')
            col.separator(factor=0.35)
            for attr, label in [('maya_sx', 'Scale X'), ('maya_sy', 'Scale Y'), ('maya_sz', 'Scale Z')]:
                r = col.row(align=True)
                r.label(text=label)
                r.prop(ms, attr, text='')
        else:
            for prop, label in [('location', 'Translate'), ('rotation_euler', 'Rotate'), ('scale', 'Scale')]:
                if prop == 'rotation_euler' and target.rotation_mode in {'QUATERNION', 'AXIS_ANGLE'}:
                    qprop = 'rotation_quaternion' if target.rotation_mode == 'QUATERNION' else 'rotation_axis_angle'
                    col.prop(target, qprop, text='Rotate')
                    continue
                for i, axis in enumerate('XYZ'):
                    r = col.row(align=True)
                    r.label(text=f'{label} {axis}')
                    r.prop(target, prop, index=i, text='')
                if prop != 'scale':
                    col.separator(factor=0.35)

        col.separator(factor=0.35)
        vis_row = col.row(align=True)
        vis_row.label(text='Visibility' + axis_tag)
        vis_row.prop(obj, 'hide_viewport', text='Hide', invert_checkbox=False)

        act_row = lay.row(align=True)
        act_row.operator('maya_style.poly_action', text='Freeze', icon='CHECKMARK').action = 'FREEZE_ALL'
        act_row.operator('maya_style.poly_action', text='Reset', icon='LOOP_BACK').action = 'RESET_TRANSFORMS'
        act_row.operator('anim.keyframe_insert_by_name', text='Key (S)', icon='KEY_HLT').type = 'LocRotScale'


class MAYA_STYLE_PT_inputs(bpy.types.Panel):
    bl_label = 'SHAPES & INPUTS (History)'
    bl_idname = 'MAYA_STYLE_PT_inputs'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -99

    @classmethod
    def poll(cls, context):
        ms = getattr(context.scene, 'maya_style', None)
        return ms is None or ms.right_dock in {'ALL', 'CHANNEL_BOX'}

    def draw(self, context):
        lay = self.layout
        obj = context.object
        if not obj:
            lay.label(text='No active object')
            return
        if obj.data:
            s_row = lay.row(align=True)
            s_row.label(text='SHAPES', icon='MESH_DATA' if obj.type == 'MESH' else 'OBJECT_DATAMODE')
            s_row.prop(obj.data, 'name', text='')

        h_row = lay.row(align=True)
        h_row.label(text='INPUTS', icon='MODIFIER')
        h_row.operator('maya_style.poly_action', text='Delete History', icon='MODIFIER_OFF').action = 'DELETE_HISTORY'

        if not obj.modifiers:
            lay.label(text='polySurface (Clean History)', icon='CHECKMARK')
        for mod in obj.modifiers:
            box = lay.box()
            row = box.row(align=True)
            row.label(text=mod.name, icon='MODIFIER')
            row.prop(mod, 'show_viewport', text='', icon='RESTRICT_VIEW_OFF')
            row.prop(mod, 'show_render', text='', icon='RESTRICT_RENDER_OFF')
            if mod.type == 'SUBSURF':
                row = box.row(align=True)
                row.prop(mod, 'levels', text='Divisions')
            elif mod.type == 'BEVEL':
                row = box.row(align=True)
                row.prop(mod, 'width', text='Fraction')
                row.prop(mod, 'segments', text='Segments')
            elif mod.type == 'SOLIDIFY':
                row = box.row(align=True)
                row.prop(mod, 'thickness', text='Thickness')
            elif mod.type == 'ARRAY':
                row = box.row(align=True)
                row.prop(mod, 'count', text='Copies')
            elif mod.type == 'DECIMATE':
                row = box.row(align=True)
                row.prop(mod, 'ratio', text='Ratio')


class MAYA_STYLE_PT_modeling_toolkit(bpy.types.Panel):
    bl_label = 'Modeling Toolkit'
    bl_idname = 'MAYA_STYLE_PT_modeling_toolkit'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -98

    @classmethod
    def poll(cls, context):
        ms = getattr(context.scene, 'maya_style', None)
        return ms is None or ms.right_dock in {'ALL', 'MODELING_TOOLKIT'}

    def draw(self, context):
        lay = self.layout
        ts = context.scene.tool_settings

        # Selection Mode Masks
        box = lay.box()
        box.label(text='Selection Masks', icon='RESTRICT_SELECT_OFF')
        row = box.row(align=True)
        row.operator('maya_style.component', text='Object', depress=(context.mode == 'OBJECT')).mode = 'OBJECT'
        row.operator('maya_style.component', text='Multi', depress=(context.mode == 'EDIT_MESH' and tuple(ts.mesh_select_mode) == (True, True, True))).mode = 'MULTI'
        row = box.row(align=True)
        row.operator('maya_style.component', text='Vertex', icon='VERTEXSEL').mode = 'VERT'
        row.operator('maya_style.component', text='Edge', icon='EDGESEL').mode = 'EDGE'
        row.operator('maya_style.component', text='Face', icon='FACESEL').mode = 'FACE'
        row.operator('maya_style.component', text='UV', icon='UV').mode = 'UV'

        # Soft Selection & Symmetry
        s_box = lay.box()
        s_row = s_box.row(align=True)
        s_row.prop(ts, 'use_proportional_edit', text='Soft Select (B)', icon='PROP_ON')
        if ts.use_proportional_edit:
            s_row.prop(ts, 'proportional_size', text='Radius')
        if context.object and context.object.type == 'MESH':
            m_row = s_box.row(align=True)
            m_row.label(text='Symmetry:')
            m_row.prop(context.object.data, 'use_mirror_x', text='X', toggle=True)
            m_row.prop(context.object.data, 'use_mirror_y', text='Y', toggle=True)
            m_row.prop(context.object.data, 'use_mirror_z', text='Z', toggle=True)

        # Mesh Operations
        m_box = lay.box()
        m_box.label(text='Mesh', icon='MESH_DATA')
        r1 = m_box.row(align=True)
        r1.operator('maya_style.poly_action', text='Combine').action = 'COMBINE'
        r1.operator('maya_style.poly_action', text='Separate').action = 'SEPARATE'
        r2 = m_box.row(align=True)
        r2.operator('maya_style.poly_action', text='Smooth').action = 'SMOOTH_MESH'
        r2.operator('maya_style.poly_action', text='Boolean').action = 'BOOLEAN_DIFFERENCE'
        r3 = m_box.row(align=True)
        r3.operator('maya_style.poly_action', text='Mirror X').action = 'MIRROR_X'
        r3.operator('maya_style.poly_action', text='Remesh').action = 'REMESH'

        # Component Operations
        c_box = lay.box()
        c_box.label(text='Components', icon='EDITMODE_HLT')
        c1 = c_box.row(align=True)
        c1.operator('mesh.extrude_region_move', text='Extrude')
        c1.operator('mesh.bevel', text='Bevel')
        c2 = c_box.row(align=True)
        c2.operator('mesh.bridge_edge_loops', text='Bridge')
        c2.operator('mesh.subdivide', text='Add Divisions')
        c3 = c_box.row(align=True)
        c3.operator('maya_style.poly_action', text='Extract').action = 'EXTRACT_FACES'
        c3.operator('maya_style.poly_action', text='Circularize').action = 'CIRCULARIZE'

        # Tools
        t_box = lay.box()
        t_box.label(text='Tools', icon='TOOL_SETTINGS')
        t1 = t_box.row(align=True)
        t1.operator('mesh.knife_tool', text='Multi-Cut')
        t1.operator('mesh.loopcut_slide', text='Insert Loop')
        t2 = t_box.row(align=True)
        t2.operator('mesh.vert_connect_path', text='Connect')
        t2.operator('wm.tool_set_by_id', text='Quad Draw').name = 'builtin.poly_build'
        t3 = t_box.row(align=True)
        t3.operator('maya_style.poly_action', text='Fill Hole').action = 'FILL_HOLE'
        t3.operator('mesh.remove_doubles', text='Target Weld / Merge')


class MAYA_STYLE_PT_attribute_editor(bpy.types.Panel):
    bl_label = 'Attribute Editor'
    bl_idname = 'MAYA_STYLE_PT_attribute_editor'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -97

    @classmethod
    def poll(cls, context):
        ms = getattr(context.scene, 'maya_style', None)
        return ms is None or ms.right_dock in {'ALL', 'ATTRIBUTE_EDITOR'}

    def draw(self, context):
        lay = self.layout
        ms = context.scene.maya_style
        obj = context.object
        if obj is None:
            lay.label(text='Select an object to inspect nodes')
            return

        tabs = lay.row(align=True)
        tabs.prop(ms, 'ae_tab', expand=True)

        tab = ms.ae_tab
        if tab == 'TRANSFORM':
            box = lay.box()
            box.label(text=f'Transform: {obj.name}', icon='OBJECT_ORIGIN')
            box.prop(obj, 'rotation_mode', text='Rotate Order')
            box.prop(obj, 'parent', text='Parent')
            box.prop(obj, 'display_type', text='Drawing Override')
            box.prop(obj, 'show_in_front', text='X-Ray In Front')
        elif tab == 'SHAPE':
            box = lay.box()
            if obj.data is None:
                box.label(text='Locator / Empty Node')
                box.prop(obj, 'empty_display_type', text='Display')
                box.prop(obj, 'empty_display_size', text='Radius')
            elif obj.type == 'MESH':
                box.label(text=f'Mesh Shape: {obj.data.name}', icon='MESH_DATA')
                row = box.row(align=True)
                row.operator('maya_style.poly_action', text='Soften Normals').action = 'SOFTEN_EDGE'
                row.operator('maya_style.poly_action', text='Harden Normals').action = 'HARDEN_EDGE'
                s_row = box.row(align=True)
                s_row.label(text='Smooth Mesh Preview:')
                for lvl in (1, 2, 3):
                    s_row.operator('maya_style.smooth_preview', text=str(lvl)).level = lvl
                box.operator('maya_style.preview_divisions', text='+ Smooth Divisions').delta = 1
            elif obj.type == 'CAMERA':
                box.label(text=f'Camera Shape: {obj.data.name}', icon='CAMERA_DATA')
                box.prop(obj.data, 'lens', text='Focal Length')
                box.prop(obj.data, 'clip_start', text='Near Clip')
                box.prop(obj.data, 'clip_end', text='Far Clip')
            elif obj.type == 'LIGHT':
                box.label(text=f'Light Shape: {obj.data.name}', icon='LIGHT')
                box.prop(obj.data, 'type', text='Light Type')
                box.prop(obj.data, 'color', text='Color')
                box.prop(obj.data, 'energy', text='Intensity')
            else:
                box.label(text=f'Shape: {obj.data.name}')
        elif tab == 'MATERIAL':
            box = lay.box()
            r = box.row(align=True)
            for p, lbl in [('STANDARD_SURFACE', 'StdSurf'), ('LAMBERT', 'Lambert'), ('BLINN', 'Blinn'), ('PHONG', 'Phong')]:
                r.operator('maya_style.assign_shader', text=lbl).shader_type = p
            mat = obj.active_material
            if not mat:
                box.label(text='No shader assigned — click a preset above.')
            else:
                box.prop(mat, 'name', text='Shader')
                bsdf = mat.node_tree.nodes.get('Principled BSDF') if (mat.use_nodes and mat.node_tree) else None
                if bsdf:
                    for sock_name, label in [
                        ('Base Color', 'Color'),
                        ('Metallic', 'Metalness'),
                        ('Roughness', 'Specular Roughness'),
                        ('IOR', 'IOR'),
                        ('Emission Strength', 'Emission'),
                    ]:
                        sock = bsdf.inputs.get(sock_name)
                        if sock is not None:
                            box.prop(sock, 'default_value', text=label)
        else:
            box = lay.box()
            box.prop(context.scene.render, 'engine', text='Render Using')
            box.prop(context.scene.render, 'resolution_x', text='Width')
            box.prop(context.scene.render, 'resolution_y', text='Height')
            box.operator('render.render', text='Render Current Frame', icon='RENDER_STILL')


class MAYA_STYLE_PT_layers(bpy.types.Panel):
    bl_label = 'Display Layers'
    bl_idname = 'MAYA_STYLE_PT_layers'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_order = -96

    @classmethod
    def poll(cls, context):
        ms = getattr(context.scene, 'maya_style', None)
        return ms is None or ms.right_dock in {'ALL', 'CHANNEL_BOX'}

    def draw(self, context):
        lay = self.layout
        top = lay.row(align=True)
        top.operator('maya_style.layer_create', text='Create Layer from Selected', icon='COLLECTION_NEW')
        for coll in context.scene.collection.children:
            row = lay.row(align=True)
            row.prop(coll, 'hide_viewport', text='V', toggle=True, invert_checkbox=True)
            row.prop(coll, 'hide_select', text='R', toggle=True)
            row.prop(coll, 'name', text='')
            row.prop(coll, 'hide_render', text='', icon='RESTRICT_RENDER_OFF')
        if not context.scene.collection.children:
            lay.label(text='defaultLayer (All Objects)', icon='OUTLINER_COLLECTION')


class MAYA_STYLE_PT_reference(bpy.types.Panel):
    bl_label = 'Baya Controls & Hotkeys'
    bl_idname = 'MAYA_STYLE_PT_reference'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Baya'
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = -95

    def draw(self, context):
        draw_shortcuts(self.layout)
        self.layout.separator()
        self.layout.operator('baya.about', icon='INFO')


def draw_shortcuts(layout):
    col = layout.column(align=True)
    for text in [
        'Q / W / E / R: Select / Move / Rotate / Scale',
        'Alt + LMB / MMB / RMB: Orbit / Pan / Dolly',
        'F: Frame Selected    A: Frame All',
        '1 / 2 / 3: Base / Cage / Smooth Mesh Preview',
        '4 / 5 / 6 / 7: Wire / Shaded / Textured / Lit',
        'F8: Object / Component Mode',
        'F9 / F10 / F11 / F12: Vertex / Edge / Face / UV',
        'Hold X / C / V: Snap to Grid / Curve-Edge / Vertex',
        'D or Insert: Edit Pivot Mode',
        'B: Soft Selection Toggle',
        'G: Repeat Last Action',
        'RMB: Component & Object Marking Menu',
        'Shift + RMB: Context Modeling Tool Marking Menu',
        'Ctrl + RMB: Convert Selection Menu',
        'Ctrl + D: Duplicate    Ctrl + G: Group',
        'Ctrl + E: Extrude      Ctrl + B: Bevel',
        'S: Set Key             Alt + V: Play / Pause',
        'Tap Space: Four View   Hold Space: Hotbox',
        'Ctrl + A: Channel Box / Modeling Toolkit / AE',
        'F2-F6: Modeling / Rigging / Animation / FX / Render',
    ]:
        col.label(text=text)


def _draw_hud_text(font_id, x, y, text, color=(0.72, 0.90, 0.78, 0.95), size=11):
    blf.size(font_id, size)
    blf.color(font_id, *color)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, text)


def _draw_baya_hud():
    context = bpy.context
    if not context or not context.scene or not hasattr(context.scene, 'maya_style'):
        return
    ms = context.scene.maya_style
    if not ms.show_hud:
        return
    region = context.region
    space = context.space_data
    if not region or not space or space.type != 'VIEW_3D':
        return
    if hasattr(space, 'overlay') and not space.overlay.show_overlays:
        return

    font_id = 0
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 3, 0.0, 0.0, 0.0, 0.85)

    x_left = 18
    y_top = region.height - 68
    if getattr(space, 'show_region_tool_header', True):
        y_top -= 26

    # 1. Poly Count HUD (Maya top-left block)
    if ms.show_hud_polycount:
        meshes = [o for o in context.selected_objects if o.type == 'MESH' and o.data]
        if not meshes and context.object and context.object.type == 'MESH' and context.object.data:
            meshes = [context.object]
        verts = sum(len(o.data.vertices) for o in meshes)
        edges = sum(len(o.data.edges) for o in meshes)
        faces = sum(len(o.data.polygons) for o in meshes)
        tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons) for o in meshes)
        uvs = sum(len(o.data.loops) if o.data.uv_layers.active else 0 for o in meshes)
        for label, val in [('Verts:', verts), ('Edges:', edges), ('Faces:', faces), ('Tris:', tris), ('UVs:', uvs)]:
            _draw_hud_text(font_id, x_left, y_top, f'{label:<7} {val:>7}', (0.76, 0.92, 0.80, 0.92), 11)
            y_top -= 15
        y_top -= 6

    # 2. Object Details HUD
    if ms.show_hud_object:
        obj = context.object
        obj_name = obj.name if obj else 'None'
        mode_map = {
            'OBJECT': 'Object Mode',
            'EDIT_MESH': 'Polygon Component',
            'SCULPT': 'Sculpt',
            'POSE': 'Rig Pose',
        }
        mode_str = mode_map.get(context.mode, context.mode)
        _draw_hud_text(font_id, x_left, y_top, f'Object: {obj_name}  [{mode_str}]', (0.85, 0.88, 0.92, 0.90), 11)
        y_top -= 15

    # 3. Top-Center Active Tool / Modal Banners (Pivot Mode, Snapping, Soft Select)
    ts = context.scene.tool_settings
    banners = []
    if getattr(ts, 'use_transform_data_origin', False):
        banners.append('INSERT / D : EDIT PIVOT MODE')
    if ts.use_snap:
        elems = set(ts.snap_elements)
        if 'INCREMENT' in elems:
            banners.append('SNAP TO GRID [X]')
        elif 'EDGE' in elems:
            banners.append('SNAP TO CURVE / EDGE [C]')
        elif 'VERTEX' in elems:
            banners.append('SNAP TO POINT / VERTEX [V]')
    if ts.use_proportional_edit:
        banners.append(f'SOFT SELECT [B] ({ts.proportional_size:.2f})')
    if banners:
        banner_str = '   |   '.join(banners)
        cx = max(160, int(region.width * 0.5) - len(banner_str) * 3.5)
        _draw_hud_text(font_id, cx, region.height - 72, banner_str, (1.0, 0.78, 0.25, 0.98), 12)

    # 4. Bottom-Center Camera & Maya XYZ Axis Indicator
    if ms.show_hud_camera:
        rv3d = context.region_data
        cam_name = 'persp'
        if rv3d:
            if rv3d.view_perspective == 'CAMERA' and context.scene.camera:
                cam_name = context.scene.camera.name
            elif not rv3d.is_perspective:
                cam_name = 'ortho'
        axis_label = 'Y-Up (Maya XYZ)' if ms.coord_system == 'MAYA_Y_UP' else 'Z-Up (Blender XYZ)'
        cam_text = f'{cam_name}   |   {axis_label}'
        bx = max(120, int(region.width * 0.5) - len(cam_text) * 3.2)
        _draw_hud_text(font_id, bx, 18, cam_text, (0.76, 0.92, 0.80, 0.90), 11)

    blf.disable(font_id, blf.SHADOW)


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


def _configure_interactive_session():
    if bpy.app.background:
        return None
    try:
        apply_theme()
        wm = bpy.context.window_manager
        for win in wm.windows:
            for area in win.screen.areas:
                if area.type == 'VIEW_3D':
                    space = area.spaces.active
                    space.show_region_ui = True
                    space.show_region_tool_header = True
                    for region in area.regions:
                        if region.type == 'UI':
                            try:
                                region.active_panel_category = 'Baya'
                            except Exception:
                                pass
                    area.tag_redraw()
    except Exception:
        pass
    return None


CLASSES = (
    MAYA_STYLE_PG_workspace,
    MAYA_STYLE_OT_workspace,
    MAYA_STYLE_OT_shelf,
    MAYA_STYLE_OT_menu_set,
    MAYA_STYLE_OT_channel_toggle,
    MAYA_STYLE_OT_attributes,
    MAYA_STYLE_OT_freeze,
    MAYA_STYLE_OT_layer_create,
    MAYA_STYLE_OT_about,
    MAYA_STYLE_MT_shelf_create,
    MAYA_STYLE_MT_select,
    MAYA_STYLE_MT_modify,
    MAYA_STYLE_MT_display,
    MAYA_STYLE_MT_mesh_menu,
    MAYA_STYLE_MT_mesh,
    MAYA_STYLE_MT_mesh_tools,
    MAYA_STYLE_MT_mesh_display,
    MAYA_STYLE_MT_curves,
    MAYA_STYLE_MT_surfaces,
    MAYA_STYLE_MT_deform,
    MAYA_STYLE_MT_uv_menu,
    MAYA_STYLE_MT_skeleton,
    MAYA_STYLE_MT_skin,
    MAYA_STYLE_MT_constrain,
    MAYA_STYLE_MT_key,
    MAYA_STYLE_MT_playback,
    MAYA_STYLE_MT_fx_menu,
    MAYA_STYLE_MT_shading_menu,
    MAYA_STYLE_MT_render_menu,
    MAYA_STYLE_MT_windows,
    MAYA_STYLE_MT_main,
    MAYA_STYLE_PT_dock_switcher,
    MAYA_STYLE_PT_channels,
    MAYA_STYLE_PT_inputs,
    MAYA_STYLE_PT_modeling_toolkit,
    MAYA_STYLE_PT_attribute_editor,
    MAYA_STYLE_PT_layers,
    MAYA_STYLE_PT_reference,
)


def register():
    global _original_tool_header, _hud_draw_handler
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.maya_style = PointerProperty(type=MAYA_STYLE_PG_workspace)
    from bl_ui.space_view3d import VIEW3D_HT_tool_header
    _original_tool_header = VIEW3D_HT_tool_header.draw
    VIEW3D_HT_tool_header.draw = draw_shelf
    if _hud_draw_handler is None:
        _hud_draw_handler = bpy.types.SpaceView3D.draw_handler_add(
            _draw_baya_hud, (), 'WINDOW', 'POST_PIXEL'
        )
    if not bpy.app.background:
        bpy.app.timers.register(_configure_interactive_session, first_interval=0.2)


def unregister():
    global _original_tool_header, _hud_draw_handler
    if _hud_draw_handler is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_hud_draw_handler, 'WINDOW')
        _hud_draw_handler = None
    from bl_ui.space_view3d import VIEW3D_HT_tool_header
    if _original_tool_header is not None:
        VIEW3D_HT_tool_header.draw = _original_tool_header
        _original_tool_header = None
    if hasattr(bpy.types.Scene, 'maya_style'):
        del bpy.types.Scene.maya_style
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
