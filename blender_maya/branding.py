"""Baya 3D Top Menu Bar (Menu Sets) and Bottom MEL/Python Command Bar + Time Controls."""
import bpy
from bpy.utils import previews
from pathlib import Path

_original_menu_draw = None
_preview_icons = None


class BAYA_MT_application(bpy.types.Menu):
    bl_label = 'Baya 3D'
    bl_idname = 'BAYA_MT_application'

    def draw(self, context):
        lay = self.layout
        lay.operator('baya.about', text='About Baya 3D', icon='INFO')
        lay.separator()
        lay.operator('wm.window_fullscreen_toggle', text='Fullscreen / Windowed', icon='FULLSCREEN_ENTER')
        lay.operator('screen.userpref_show', text='Preferences', icon='PREFERENCES')
        lay.separator()
        lay.menu('TOPBAR_MT_blender_system', text='System Information')
        lay.operator('wm.splash_about', text='About the Blender Engine')
        lay.separator()
        lay.operator('wm.quit_blender', text='Exit Baya 3D', icon='QUIT')


def draw_application_menus(self, context):
    lay = self.layout
    icon = _preview_icons['baya'].icon_id if _preview_icons and 'baya' in _preview_icons else 0
    brand = lay.row(align=True)
    brand.ui_units_x = 5.5
    brand.menu('BAYA_MT_application', text='Baya 3D', icon_value=icon)

    ms = getattr(context.scene, 'maya_style', None) if context.scene else None
    if ms is not None:
        mset_row = lay.row(align=True)
        mset_row.ui_units_x = 5.2
        mset_row.prop(ms, 'menu_set', text='')

    # Common Maya Menu Bar items (File, Edit, Create, Select, Modify, Display, Windows)
    lay.menu('TOPBAR_MT_file')
    lay.menu('TOPBAR_MT_edit')
    lay.menu('MAYA_STYLE_MT_shelf_create')
    lay.menu('MAYA_STYLE_MT_select')
    lay.menu('MAYA_STYLE_MT_modify')
    lay.menu('MAYA_STYLE_MT_display')
    lay.menu('MAYA_STYLE_MT_windows')

    # Context-dependent Menu Set items
    mset = ms.menu_set if ms is not None else 'MODELING'
    if mset == 'MODELING':
        lay.menu('MAYA_STYLE_MT_mesh_menu')
        lay.menu('MAYA_STYLE_MT_mesh')
        lay.menu('MAYA_STYLE_MT_mesh_tools')
        lay.menu('MAYA_STYLE_MT_mesh_display')
        lay.menu('MAYA_STYLE_MT_curves')
        lay.menu('MAYA_STYLE_MT_surfaces')
        lay.menu('MAYA_STYLE_MT_deform')
        lay.menu('MAYA_STYLE_MT_uv_menu')
    elif mset == 'RIGGING':
        lay.menu('MAYA_STYLE_MT_skeleton')
        lay.menu('MAYA_STYLE_MT_skin')
        lay.menu('MAYA_STYLE_MT_deform')
        lay.menu('MAYA_STYLE_MT_constrain')
    elif mset == 'ANIMATION':
        lay.menu('MAYA_STYLE_MT_key')
        lay.menu('MAYA_STYLE_MT_playback')
        lay.menu('MAYA_STYLE_MT_deform')
        lay.menu('MAYA_STYLE_MT_constrain')
    elif mset == 'FX':
        lay.menu('MAYA_STYLE_MT_fx_menu')
        lay.menu('MAYA_STYLE_MT_deform')
    elif mset == 'RENDERING':
        lay.menu('MAYA_STYLE_MT_shading_menu')
        lay.menu('MAYA_STYLE_MT_render_menu')

    lay.menu('TOPBAR_MT_help')


def draw_brand_status(self, context):
    lay = self.layout
    scene = context.scene
    ms = getattr(scene, 'maya_style', None) if scene else None
    if ms is None:
        lay.label(text='Baya 3D  |  Maya-style workspace')
        return

    # Maya Command Line (MEL / Python) + Help/Result Line
    cmd_row = lay.row(align=True)
    lang_sub = cmd_row.row(align=True)
    lang_sub.ui_units_x = 3.2
    lang_sub.prop(ms, 'command_lang', text='')
    inp_sub = cmd_row.row(align=True)
    inp_sub.ui_units_x = 12.0
    inp_sub.prop(ms, 'command_input', text='', icon='CONSOLE')
    exec_op = cmd_row.operator('maya_style.command_exec', text='', icon='PLAY')
    exec_op.command = ms.command_input
    exec_op.language = ms.command_lang

    res_row = lay.row(align=True)
    res_row.ui_units_x = 10.0
    res_row.label(text=f'// {ms.last_command_result}')

    lay.separator(factor=0.8)

    # Compact Time / Range Controls
    t_row = lay.row(align=True)
    t_row.ui_units_x = 13.5
    t_row.operator('screen.frame_jump', text='', icon='REW').end = False
    t_row.operator('screen.keyframe_jump', text='', icon='PREV_KEYFRAME').next = False
    t_row.operator('screen.animation_play', text='', icon='PLAY')
    t_row.operator('screen.keyframe_jump', text='', icon='NEXT_KEYFRAME').next = True
    t_row.operator('screen.frame_jump', text='', icon='FF').end = True
    t_row.prop(scene, 'frame_start', text='In')
    t_row.prop(scene, 'frame_current', text='Frm')
    t_row.prop(scene, 'frame_end', text='Out')
    t_row.prop(scene.tool_settings, 'use_keyframe_insert_auto', text='', icon='REC')


def register():
    global _original_menu_draw, _preview_icons
    icon_path = Path(__file__).resolve().parent / 'assets' / 'Baya3D.png'
    if icon_path.exists():
        _preview_icons = previews.new()
        _preview_icons.load('baya', str(icon_path), 'IMAGE')
    bpy.utils.register_class(BAYA_MT_application)
    from bl_ui.space_topbar import TOPBAR_MT_editor_menus
    from bl_ui.space_statusbar import STATUSBAR_HT_header
    _original_menu_draw = TOPBAR_MT_editor_menus.draw
    TOPBAR_MT_editor_menus.draw = draw_application_menus
    STATUSBAR_HT_header.append(draw_brand_status)


def unregister():
    global _original_menu_draw, _preview_icons
    from bl_ui.space_topbar import TOPBAR_MT_editor_menus
    from bl_ui.space_statusbar import STATUSBAR_HT_header
    STATUSBAR_HT_header.remove(draw_brand_status)
    if _original_menu_draw:
        TOPBAR_MT_editor_menus.draw = _original_menu_draw
        _original_menu_draw = None
    bpy.utils.unregister_class(BAYA_MT_application)
    if _preview_icons:
        previews.remove(_preview_icons)
        _preview_icons = None
