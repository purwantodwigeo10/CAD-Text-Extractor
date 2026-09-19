# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
import os
import re
import traceback

from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QTextEdit, QVBoxLayout
)
from qgis.PyQt.QtGui import QPixmap, QDesktopServices
from qgis.core import QgsMapLayerType, QgsProject, QgsVectorLayer, QgsWkbTypes

from .licensehub_cte_qgis import (
    FIXED_CODE,
    LicenseManager,
    PRODUCT_CODE,
    PRODUCT_NAME,
    TRIAL_LIMIT,
)
from .dxf_writer import SimpleDxfWriter

HELP_URL = 'https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis'
DIALOG_STYLE = (
    'QDialog { background-color: white; } '
    'QGroupBox { background-color: white; border: 1px solid #d9d9d9; '
    'margin-top: 8px; } '
    'QGroupBox::title { subcontrol-origin: margin; left: 10px; '
    'padding: 0 3px; background-color: white; } '
    'QTextEdit, QLabel { background-color: white; }'
)


class ActivationDialog(QDialog):
    def __init__(self, lm, parent=None):
        super(ActivationDialog, self).__init__(parent)
        self.lm = lm
        self.setWindowTitle('License Activation')
        window_flags = (
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.setWindowFlags(window_flags)
        self.setSizeGripEnabled(True)
        self.resize(700, 190)
        self.setStyleSheet(DIALOG_STYLE)
        self._build_ui()
        self.refresh_status(True)

    def _build_ui(self):
        main = QVBoxLayout(self)
        grid = QGridLayout()
        self.lbl_status = QLabel('-')
        self.txt_device_id = QLineEdit()
        self.txt_device_id.setReadOnly(True)
        self.btn_copy = QPushButton('Copy Device ID')
        self.btn_copy.clicked.connect(self.copy_device_id)
        self.lbl_trial = QLabel('-')
        self.txt_code = QLineEdit()
        self.txt_code.setPlaceholderText(
            'Enter the activation code from License Hub')
        grid.addWidget(QLabel('Activation Status'), 0, 0)
        grid.addWidget(self.lbl_status, 0, 1, 1, 2)
        grid.addWidget(QLabel('Device ID'), 1, 0)
        grid.addWidget(self.txt_device_id, 1, 1)
        grid.addWidget(self.btn_copy, 1, 2)
        grid.addWidget(QLabel('Trial Usage'), 2, 0)
        grid.addWidget(self.lbl_trial, 2, 1, 1, 2)
        grid.addWidget(QLabel('Activation Code'), 3, 0)
        grid.addWidget(self.txt_code, 3, 1, 1, 2)
        main.addLayout(grid)
        row = QHBoxLayout()
        self.btn_request = QPushButton('Submit Request')
        self.btn_request.clicked.connect(self.open_request_page)
        self.btn_activate = QPushButton('Activate')
        self.btn_activate.clicked.connect(self.activate_license)
        self.btn_refresh = QPushButton('Refresh Status')
        self.btn_refresh.clicked.connect(lambda: self.refresh_status(False))
        self.btn_close = QPushButton('Close')
        self.btn_close.clicked.connect(self.accept)
        row.addStretch(1)
        row.addWidget(self.btn_request)
        row.addWidget(self.btn_activate)
        row.addWidget(self.btn_refresh)
        row.addWidget(self.btn_close)
        main.addLayout(row)

    def refresh_status(self, quiet=True):
        self.txt_device_id.setText(self.lm.get_device_id())
        self._display_local_status()
        if not quiet:
            ok, msg = self.lm.refresh_activation_from_server()
            self.txt_device_id.setText(self.lm.get_device_id())
            self._display_local_status()
            if ok is True:
                QMessageBox.information(
                    self,
                    PRODUCT_NAME,
                    'License status was refreshed from the website.')
            elif ok is False:
                QMessageBox.warning(
                    self, PRODUCT_NAME, msg or 'License is not active.')
            else:
                QMessageBox.warning(
                    self,
                    PRODUCT_NAME,
                    msg or (
                        'License status could not be confirmed from the '
                        'website.'
                    ))

    def _display_local_status(self):
        status = self.lm.status_text()
        self.lbl_status.setText(status)
        remaining = self.lm.trial_remaining()
        self.lbl_trial.setText(
            '%s/%s used, %s remaining' %
            (TRIAL_LIMIT - remaining, TRIAL_LIMIT, remaining))
        if status.startswith('Active'):
            self.lbl_status.setStyleSheet('font-weight:bold;color:#0B7A2A;')
        elif status.startswith('Trial'):
            self.lbl_status.setStyleSheet('font-weight:bold;color:#B35C00;')
        elif status.startswith('Expired'):
            self.lbl_status.setStyleSheet('font-weight:bold;color:#B00020;')
        else:
            self.lbl_status.setStyleSheet('font-weight:bold;color:#7A003C;')

    def copy_device_id(self):
        QApplication.clipboard().setText(self.txt_device_id.text().strip())
        QMessageBox.information(
            self, PRODUCT_NAME, 'Device ID copied successfully.')

    def open_request_page(self):
        try:
            self.lm.open_request_url()
            QMessageBox.information(
                self,
                PRODUCT_NAME,
                (
                    'The activation request page has been opened. Please '
                    'submit the request with Product Code %s and Fixed Code '
                    '%s.'
                ) % (PRODUCT_CODE, FIXED_CODE))
        except Exception as e:
            QMessageBox.warning(
                self,
                PRODUCT_NAME,
                'Failed to open request page: %s' %
                e)

    def activate_license(self):
        ok, msg = self.lm.activate(self.txt_code.text().strip())
        self.refresh_status(True)
        if ok:
            QMessageBox.information(self, PRODUCT_NAME, msg)
            self.accept()
        else:
            QMessageBox.warning(self, PRODUCT_NAME, msg)


class CADTextExtractorDialog(QDialog):
    def __init__(self, iface, parent=None):
        super(CADTextExtractorDialog, self).__init__(parent)
        self.iface = iface
        self.lm = LicenseManager()
        self.setWindowTitle('CAD Text Extractor')
        window_flags = (
            self.windowFlags()
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.setWindowFlags(window_flags)
        self.setSizeGripEnabled(True)
        self.resize(860, 650)
        self.setStyleSheet(DIALOG_STYLE)
        self._build_ui()
        self.load_layers()
        self.refresh_license_status()

    def _build_ui(self):
        main = QVBoxLayout(self)
        hero = QGroupBox()
        hero_layout = QHBoxLayout(hero)
        self.lbl_logo = QLabel()
        self.lbl_logo.setStyleSheet('background-color: white;')
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path)
            self.lbl_logo.setPixmap(
                pix.scaled(
                    155,
                    155,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation))
        self.lbl_logo.setMinimumWidth(170)
        self.lbl_logo.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.lbl_logo)

        center = QVBoxLayout()
        self.lbl_title = QLabel(
            "<span style='font-size:24px; font-weight:700;'>"
            "CAD Text Extractor</span>")
        self.lbl_title.setTextFormat(Qt.RichText)
        self.lbl_desc = QLabel(
            'Export selected attribute fields as CAD text together with the '
            'source geometry in an AutoCAD-compatible DXF file.')
        self.lbl_desc.setWordWrap(True)
        center.addWidget(self.lbl_title)
        center.addWidget(self.lbl_desc)
        center.addStretch(1)
        hero_layout.addLayout(center, 1)

        right = QVBoxLayout()
        self.lbl_plugin_status = QLabel()
        self.lbl_plugin_status.setTextFormat(Qt.RichText)
        self.lbl_activation = QLabel()
        self.lbl_activation.setTextFormat(Qt.RichText)
        self.btn_manage = QPushButton('Manage Activation')
        self.btn_manage.clicked.connect(self.show_activation_dialog)
        self.btn_help_main = QPushButton('User Guide and Activation')
        self.btn_help_main.clicked.connect(self.open_help_page)
        right.addWidget(self.lbl_plugin_status, 0, Qt.AlignRight)
        right.addWidget(self.lbl_activation, 0, Qt.AlignRight)
        right.addWidget(self.btn_manage, 0, Qt.AlignRight)
        right.addWidget(self.btn_help_main, 0, Qt.AlignRight)
        right.addStretch(1)
        hero_layout.addLayout(right)
        main.addWidget(hero)

        tool_box = QGroupBox('CAD Export Workspace')
        layout = QVBoxLayout(tool_box)

        grid = QGridLayout()
        self.txt_input_file = QLineEdit()
        self.txt_input_file.setPlaceholderText(
            'Optional: browse source features directly from a folder')
        self.btn_input_file = QPushButton('Browse Input...')
        self.btn_input_file.clicked.connect(self.choose_input_file)
        self.cmb_layer = QComboBox()
        self.cmb_layer.currentIndexChanged.connect(self.on_layer_changed)
        self.cmb_placement = QComboBox()
        self.cmb_placement.addItems(['Auto',
                                     'Centroid (Polygon)',
                                     'Inside Point (Polygon)',
                                     'Midpoint (Line)',
                                     'Point (As-is)'])
        self.txt_output = QLineEdit()
        self.btn_output = QPushButton('Browse Output...')
        self.btn_output.clicked.connect(self.choose_output)
        self.cmb_dxf_version = QComboBox()
        self.cmb_dxf_version.addItems(
            ['DXF_R12_ASCII (Maximum Compatibility)'])

        grid.addWidget(QLabel('Input Features From Folder'), 0, 0)
        grid.addWidget(self.txt_input_file, 0, 1)
        grid.addWidget(self.btn_input_file, 0, 2)
        grid.addWidget(QLabel('Input Layer From Project'), 1, 0)
        grid.addWidget(self.cmb_layer, 1, 1, 1, 2)
        grid.addWidget(QLabel('Placement Mode'), 2, 0)
        grid.addWidget(self.cmb_placement, 2, 1, 1, 2)
        grid.addWidget(QLabel('Output CAD File (.dxf)'), 3, 0)
        grid.addWidget(self.txt_output, 3, 1)
        grid.addWidget(self.btn_output, 3, 2)
        grid.addWidget(QLabel('DXF Compatibility Mode'), 4, 0)
        grid.addWidget(self.cmb_dxf_version, 4, 1, 1, 2)
        layout.addLayout(grid)

        fields_box = QGroupBox(
            'Fields to Export (Order Follows Source Field Order)')
        fields_layout = QVBoxLayout(fields_box)
        btn_row = QHBoxLayout()
        self.btn_select_all = QPushButton('Select All')
        self.btn_select_all.clicked.connect(self.select_all_fields)
        self.btn_unselect_all = QPushButton('Unselect All')
        self.btn_unselect_all.clicked.connect(self.unselect_all_fields)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_select_all)
        btn_row.addWidget(self.btn_unselect_all)
        fields_layout.addLayout(btn_row)
        self.lst_fields = QListWidget()
        self.lst_fields.setMinimumHeight(150)
        fields_layout.addWidget(self.lst_fields)
        layout.addWidget(fields_box)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(190)
        layout.addWidget(self.log)
        main.addWidget(tool_box)

        bottom = QHBoxLayout()
        self.btn_run = QPushButton('Run')
        self.btn_run.clicked.connect(self.run_tool)
        self.btn_cancel = QPushButton('Cancel')
        self.btn_cancel.clicked.connect(self.close)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_run)
        bottom.addWidget(self.btn_cancel)
        main.addLayout(bottom)

    def open_help_page(self):
        try:
            if not QDesktopServices.openUrl(QUrl(HELP_URL)):
                raise RuntimeError('The browser did not accept the help URL.')
        except Exception as e:
            QMessageBox.warning(
                self,
                PRODUCT_NAME,
                'Failed to open help page: %s' %
                e)

    def show_activation_dialog(self):
        dlg = ActivationDialog(self.lm, self)
        dlg.exec_()
        self.refresh_license_status()

    def refresh_license_status(self):
        self.lbl_plugin_status.setText(
            "<b><span style='color:#0B7A2A;'>Plugin Status: Ready</span></b>")
        status = self.lm.status_text()
        if status.startswith('Active'):
            txt = (
                "<b><span style='color:#0B7A2A;'>"
                "Activation : Active</span></b>")
        elif status.startswith('Trial'):
            txt = (
                "<b><span style='color:#B35C00;'>"
                "Activation : Trial</span></b>")
        elif status.startswith('Expired'):
            txt = (
                "<b><span style='color:#B00020;'>"
                "Activation : Expired</span></b>")
        else:
            txt = (
                "<b><span style='color:#7A003C;'>"
                "Activation : Deactivated</span></b>")
        self.lbl_activation.setText(txt)

    def log_msg(self, msg):
        self.log.append(str(msg))

    def load_layers(self):
        self.cmb_layer.clear()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.type() == QgsMapLayerType.VectorLayer:
                self.cmb_layer.addItem(lyr.name(), lyr.id())
        self.on_layer_changed()

    def _open_vector_from_path(self, path):
        if not path or not os.path.exists(path):
            return None
        layer = QgsVectorLayer(path, os.path.basename(path), 'ogr')
        return layer if layer.isValid() else None

    def current_layer(self):
        input_path = self.txt_input_file.text().strip()
        if input_path:
            return self._open_vector_from_path(input_path)
        lid = self.cmb_layer.currentData()
        if not lid:
            return None
        return QgsProject.instance().mapLayer(lid)

    def on_layer_changed(self):
        self.lst_fields.clear()
        lyr = self.current_layer()
        if lyr is None:
            return
        for f in lyr.fields():
            item = QListWidgetItem(f.name())
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.lst_fields.addItem(item)

    def choose_input_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Select source features from folder',
            '',
            'Vector Data (*.shp *.gpkg *.geojson *.json *.kml *.tab);;'
            'All Files (*.*)'
        )
        if path:
            layer = self._open_vector_from_path(path)
            if layer is None:
                QMessageBox.warning(
                    self,
                    PRODUCT_NAME,
                    'The selected input data cannot be opened as a valid '
                    'vector layer.')
                return
            self.txt_input_file.setText(path)
            self.on_layer_changed()
            self.log_msg('Input selected from folder: %s' % path)

    def choose_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, 'Save CAD output', '', 'DXF File (*.dxf)')
        if path:
            if not path.lower().endswith('.dxf'):
                path += '.dxf'
            self.txt_output.setText(path)

    def select_all_fields(self):
        for i in range(self.lst_fields.count()):
            self.lst_fields.item(i).setCheckState(Qt.Checked)

    def unselect_all_fields(self):
        for i in range(self.lst_fields.count()):
            self.lst_fields.item(i).setCheckState(Qt.Unchecked)

    def selected_fields(self):
        names = []
        for i in range(self.lst_fields.count()):
            item = self.lst_fields.item(i)
            if item.checkState() == Qt.Checked:
                names.append(item.text())
        return names

    def run_tool(self):
        can_run, msg = self.lm.can_run()
        if not can_run:
            self.refresh_license_status()
            QMessageBox.warning(self, PRODUCT_NAME, msg)
            return
        using_trial = not self.lm.is_activated_local()
        try:
            output = self._process()
            if using_trial:
                self.lm.consume_trial_for_run()
                self.log_msg(
                    'Trial run completed. Remaining trial: %s of %s.' %
                    (self.lm.trial_remaining(), TRIAL_LIMIT))
            self.log_msg(
                'Done. Export includes source geometry and generated CAD '
                'text entities.')
            self.log_msg('Output: %s' % output)
            QMessageBox.information(
                self,
                PRODUCT_NAME,
                'Process completed.\n\nOutput: %s' %
                output)
            self.refresh_license_status()
        except Exception as e:
            self.log_msg('ERROR: %s\n%s' % (e, traceback.format_exc()))
            QMessageBox.critical(
                self,
                PRODUCT_NAME,
                'Failed to run tool:\n%s' %
                e)

    def _process(self):
        layer = self.current_layer()
        if layer is None or not layer.isValid():
            raise RuntimeError(
                'Please select input features from the project or browse '
                'data from a folder.')
        fields = self.selected_fields()
        if not fields:
            raise RuntimeError('Select at least one attribute field.')
        output = self.txt_output.text().strip()
        if not output:
            raise RuntimeError('Please choose an output DXF file.')
        if not output.lower().endswith('.dxf'):
            output += '.dxf'

        output_dir = os.path.dirname(os.path.abspath(output))
        if not os.path.isdir(output_dir):
            raise RuntimeError(
                'The output folder does not exist: %s' %
                output_dir)

        temp_output = output + '.cte_tmp'
        writer = SimpleDxfWriter(temp_output)
        writer.add_layer('SOURCE_FEATURES', color=7)
        field_layers = self._field_layer_names(fields)
        for layer_name in field_layers.values():
            writer.add_layer(layer_name, color=7)
        writer.begin()

        placement = self.cmb_placement.currentText() or 'Auto'
        # Preserve the original visual scale that produced the expected CAD
        # appearance.  Auto-scaling against the whole layer extent made text
        # enormous and covered the source geometry.
        line_gap = 0.5
        height = 20.0
        angle = 0.0

        try:
            for feat in layer.getFeatures():
                geom = feat.geometry()
                if geom is None or geom.isEmpty():
                    continue
                writer.add_geometry(geom, 'SOURCE_FEATURES')
                anchor = self._anchor_point(
                    geom, layer.geometryType(), placement)
                if anchor is None:
                    continue
                for idx, fname in enumerate(fields):
                    value = feat[fname] if layer.fields().indexOf(
                        fname) != -1 else None
                    if value is None:
                        continue
                    txt = self._to_string(value)
                    x = float(anchor.x())
                    y = float(anchor.y()) + (line_gap * idx)
                    writer.add_text(
                        x,
                        y,
                        txt,
                        field_layers[fname],
                        height=height,
                        angle=angle)

            writer.end()
            SimpleDxfWriter.validate_file(temp_output)
            os.replace(temp_output, output)
            self.log_msg(
                'DXF compatibility: AutoCAD R12 ASCII (Windows CRLF).')
            self.log_msg(
                'Text height: 20 map units; field spacing: 0.5 map units.')
        except Exception:
            writer.abort()
            if os.path.exists(temp_output):
                try:
                    os.remove(temp_output)
                except OSError as cleanup_error:
                    self.log_msg(
                        'Temporary file could not be removed: %s' %
                        cleanup_error)
            raise
        return output

    def _to_string(self, value):
        try:
            return str(value)
        except (TypeError, ValueError):
            return ''

    def _anchor_point(self, geom, geom_type, placement):
        try:
            if geom_type == QgsWkbTypes.PolygonGeometry:
                if placement == 'Centroid (Polygon)':
                    g = geom.centroid()
                else:
                    g = geom.pointOnSurface()
                return g.asPoint()
            if geom_type == QgsWkbTypes.LineGeometry:
                try:
                    return geom.interpolate(geom.length() * 0.5).asPoint()
                except (AttributeError, TypeError, ValueError):
                    return geom.centroid().asPoint()
            if (
                geom_type == QgsWkbTypes.PointGeometry
                and not geom.isMultipart()
            ):
                return geom.asPoint()
            return geom.centroid().asPoint()
        except (AttributeError, TypeError, ValueError):
            try:
                return geom.centroid().asPoint()
            except (AttributeError, TypeError, ValueError):
                return None

    def _sanitize_layer_name(self, text):
        name = str(text or 'TXT_ATTR').strip().replace(' ', '_')
        name = re.sub(r'[^A-Za-z0-9_\\-]', '', name)
        return (name or 'TXT_ATTR')[:31]

    def _field_layer_names(self, fields):
        """Return unique R12-compatible CAD layer names for source fields."""
        result = {}
        used = {'SOURCE_FEATURES'}
        for field_name in fields:
            base = self._sanitize_layer_name(field_name)
            candidate = base
            counter = 2
            while candidate.upper() in used:
                suffix = '_%s' % counter
                candidate = base[:31 - len(suffix)] + suffix
                counter += 1
            used.add(candidate.upper())
            result[field_name] = candidate
        return result
