"""Baya 3D application menu. Restores the native UI cleanly when disabled."""
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
    brand.ui_units_x = 6.0
    brand.menu('BAYA_MT_application', text='Baya 3D', icon_value=icon)
    lay.menu('TOPBAR_MT_file')
    lay.menu('TOPBAR_MT_edit')
    lay.menu('TOPBAR_MT_render')
    if bpy.data.project:
        lay.menu('TOPBAR_MT_project')
    lay.menu('TOPBAR_MT_window')
    lay.menu('TOPBAR_MT_help')


def draw_brand_status(self, context):
    self.layout.label(text='Baya 3D  |  Maya-style workspace')


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
