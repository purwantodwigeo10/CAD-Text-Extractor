# -*- coding: utf-8 -*-

def classFactory(iface):
    from .cte_plugin import CADTextExtractorPlugin
    return CADTextExtractorPlugin(iface)
