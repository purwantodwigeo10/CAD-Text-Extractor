# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from .cte_dialog import CADTextExtractorDialog

class CADTextExtractorPlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.menu = 'RUANG SPASIAL'
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(QIcon(icon_path), 'CAD Text Extractor', self.iface.mainWindow())
        self.action.setObjectName('CADTextExtractorAction')
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.action:
            self.iface.removePluginMenu(self.menu, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        self.dialog = CADTextExtractorDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
