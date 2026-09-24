CAD TEXT EXTRACTOR - QGIS PLUGIN
================================

Product Name : CAD Text Extractor
Product Code : CDTER
Fixed Code   : SMI
Author       : Dwi Purwanto (Ruang Spasial)
Version      : 0.26.01

Main workflow:
1. Select source features from a loaded QGIS layer or browse vector data directly from a folder.
2. Select one or more fields to export as CAD text.
3. Choose placement mode.
4. Export to a CAD-friendly DXF file.

QGIS adjustment:
QGIS export is provided as DXF output. The ArcMap toolbox can export DWG through ArcPy ExportCAD, while this QGIS version writes a DXF file containing:
- source feature geometries on SOURCE_FEATURES layer
- generated CAD TEXT entities
- text layers named from each selected field

License folder:
%APPDATA%\RuangSpasial\LicenseHub\CAD_TEXT_EXTRACTOR_QGIS_CDTER_SMI\license.json

Update:
- QGIS Product Code changed to CDTER.
- Plugin logo updated.

Update:
- Main plugin window background changed to white to match the logo style.

Description update:
- CAD Text Extractor exports selected attribute fields as CAD text and source geometries into a CAD-compatible DXF output.

Single-line description update:
- Removed repeated about text in metadata.

Help button update:
- Added 'Panduan Penggunaan dan Aktivasi' button linked to https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis

Help button revision:
- Removed the help button from the License Activation dialog to avoid duplicate buttons.
- The help button remains on the main plugin page only.

Help button revision:
- Main help button label changed to English: User Guide and Activation.
- Help link uses QDesktopServices and opens: https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis

DXF export repair (V26.01):
- Fixed invalid literal line separators that caused exported DXF files to be unreadable.
- Replaced the complex modern writer with Autodesk-compatible minimal R12 ASCII DXF.
- Source geometry is written as connected R12 POLYLINE/POINT entities and attributes as TEXT entities.
- Windows CRLF line endings are enforced for stricter AutoCAD readers.
- Polygon text height is assigned automatically from area in square metres:
  <= 100 = 2; > 100-500 = 3; > 500-1,000 = 4;
  > 1,000-3,000 = 5; > 3,000-5,000 = 5.5;
  > 5,000-10,000 = 6; > 10,000-25,000 = 6.5;
  > 25,000-50,000 = 7; > 50,000 = 7.
- Line and point layers use a default text height of 5.
- Multiple selected text fields are arranged from top to bottom around the
  chosen anchor point. Three texts use one row above, one at the anchor, and
  one below. Four texts use one row above, one at the anchor, and two below.
- The empty gap between rows is half of the applicable text height.
- Every TEXT entity uses Middle Center alignment, so short and long field
  values share the same horizontal centre at the selected anchor point.
- The export window displays live progress from 0 to 100 percent and reports
  the current validation, feature-export, finalisation, and DXF-checking stage.
- Blank or entity-free DXF output is rejected instead of being reported as successful.
- DXF output is finalized atomically so an incomplete file is not presented as a successful export.
