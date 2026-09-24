# CAD Text Extractor

CAD Text Extractor is a QGIS plugin for exporting source geometries and selected attribute fields to an AutoCAD-compatible DXF file.

## Main features

- Exports point, line, and polygon geometries to DXF R12 ASCII.
- Exports one or more selected attribute fields as CAD TEXT entities.
- Supports centroid, inside-point, line-midpoint, and original-point placement.
- Automatically adjusts polygon text height according to feature area.
- Arranges multiple values vertically around the selected anchor point.
- Uses Middle Center text alignment.
- Displays export progress from 0 to 100 percent.

## Compatibility

- QGIS 3.22 through QGIS 3.99.
- Windows, Linux, and macOS where the supported QGIS version is available.
- DXF R12 ASCII output for broad CAD compatibility.

## Installation

1. Download the release ZIP.
2. In QGIS, open **Plugins > Manage and Install Plugins**.
3. Select **Install from ZIP**.
4. Choose the downloaded ZIP and install it.
5. Enable **CAD Text Extractor** if it is not enabled automatically.

## Basic use

1. Open CAD Text Extractor from the Vector menu or its toolbar button.
2. Select a vector layer already loaded in QGIS, or browse to vector data.
3. Select the attribute fields to export.
4. Choose the placement mode.
5. Select an output `.dxf` file.
6. Run the export and wait until progress reaches 100 percent.

## Support

- User guide and activation: https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis
- Issue tracker: https://github.com/purwantodwigeo10/CAD-Text-Extractor/issues

## License

This project is licensed under the GNU General Public License v3.0 or later. See `LICENSE` for details.

Copyright (C) 2026 Dwi Purwanto (Ruang Spasial).
