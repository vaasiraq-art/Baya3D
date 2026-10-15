bl_info = {
    'name': 'Baya 3D',
    'author': 'Baya 3D local customization',
    'version': (1, 1, 0),
    'blender': (5, 3, 0),
    'location': 'Baya 3D > Shelf and Channel Box',
    'description': 'Baya 3D workspace with Maya-inspired controls, shelves and channel box',
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
