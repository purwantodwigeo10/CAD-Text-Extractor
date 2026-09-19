# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
import os
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .cte_dialog import CADTextExtractorDialog, HELP_URL


class CADTextExtractorPlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.help_action = None
        self.menu = 'RUANG SPASIAL'
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.action = QAction(
            QIcon(icon_path),
            'CAD Text Extractor',
            self.iface.mainWindow())
        self.action.setObjectName('CADTextExtractorAction')
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu(self.menu, self.action)
        self.iface.addToolBarIcon(self.action)

        self.help_action = QAction(
            'CAD Text Extractor Help', self.iface.mainWindow())
        self.help_action.setObjectName('CADTextExtractorHelpAction')
        self.help_action.triggered.connect(self.open_help)
        self.iface.addPluginToVectorMenu(self.menu, self.help_action)

    def unload(self):
        if self.action:
            self.iface.removePluginVectorMenu(self.menu, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None
        if self.help_action:
            self.iface.removePluginVectorMenu(self.menu, self.help_action)
            self.help_action = None

    def run(self):
        self.dialog = CADTextExtractorDialog(self.iface)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def open_help(self):
        if not QDesktopServices.openUrl(QUrl(HELP_URL)):
            QMessageBox.warning(
                self.iface.mainWindow(),
                'CAD Text Extractor',
                'The help page could not be opened in the web browser.')
