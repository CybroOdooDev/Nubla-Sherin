# -*- coding: utf-8 -*-
from . import models
from . import wizard


def uninstall_hook(env):
    """Removes menus created from the dynamic dashboard when the module is
    uninstalled."""
    menus = env['ir.ui.menu'].search([('is_from_multi_dashboard', '=', True)])
    if menus:
        menus.unlink()
