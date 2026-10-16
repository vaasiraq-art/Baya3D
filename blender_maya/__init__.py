bl_info = {
    'name': 'Baya 3D',
    'author': 'Baya 3D clean-room open-source workspace',
    'version': (2, 0, 0),
    'blender': (5, 3, 0),
    'location': 'Topbar Menu Sets > Status Line > Shelf > Right Dock (Baya)',
    'description': 'Full Maya-inspired workspace: Menu Sets, Status Line, Shelves, Channel Box (Maya Y-Up XYZ), Modeling Toolkit, Attribute Editor, Marking Menus, Hotbox, HUD & MEL Command Bar',
    'category': 'Interface',
}

from . import controls, ui, branding


def register():
    controls.register()
    ui.register()
    branding.register()


def unregister():
    branding.unregister()
    ui.unregister()
    controls.unregister()
