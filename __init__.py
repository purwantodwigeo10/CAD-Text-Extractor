# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later

def classFactory(iface):
    from .cte_plugin import CADTextExtractorPlugin
    return CADTextExtractorPlugin(iface)
