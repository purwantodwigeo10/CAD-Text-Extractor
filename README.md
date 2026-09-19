# CAD Text Extractor

CAD Text Extractor is a QGIS plugin that exports source vector geometry and
selected attribute values to an AutoCAD-compatible R12 ASCII DXF file.

## Main workflow

1. Load a point, line, or polygon vector layer in QGIS, or browse to a vector
   dataset from the plugin.
2. Select one or more attribute fields.
3. Select the placement mode and an output `.dxf` path.
4. Run the export.

The output contains:

- source geometry on the `SOURCE_FEATURES` CAD layer; and
- one CAD text layer for each selected source field.

Field order controls the text order. CAD layer names are sanitized, limited to
31 characters for R12 compatibility, and made unique when necessary.

## Compatibility

- QGIS 3.22 through 3.99
- Windows, Linux, and macOS
- AutoCAD R12 ASCII DXF with Windows CRLF line endings
- no third-party Python packages or bundled binary files

The writer supports point, line, polygon, multipart, and supported collection
geometries. Curved geometry is converted to straight segments before export.
The output retains the input coordinate values and DXF R12 does not store a
coordinate reference system. A projected CRS with suitable map units is
recommended for predictable text size and spacing.

The current export settings use a text height of 20 map units and a spacing of
0.5 map units between selected fields. The output is written to a temporary
file, validated, and then moved atomically to the selected path.

## Installation

1. Download the release ZIP from this repository's Releases page.
2. In QGIS, open **Plugins > Manage and Install Plugins**.
3. Select **Install from ZIP**, choose the downloaded ZIP, and install it.
4. Open **Vector > RUANG SPASIAL > CAD Text Extractor** or use its toolbar
   icon.

For development, copy the `cad_text_extractor_cte` directory to the active
QGIS profile's `python/plugins` directory, then restart QGIS.

## Quick test

The `sample_data` directory contains a small synthetic polygon dataset in
EPSG:32750. Load `polygons.geojson`, select `parcel_id`, `owner`, and
`land_use`, then export it to DXF. See `sample_data/README.md` for the expected
result.

## Activation and network access

The plugin may be used for two successful trial exports. Trial use is recorded
only after a valid DXF is created. Continued use requires activation through
RUANG SPASIAL License Hub.

- Product code: `CDTER`
- Fixed code: `SMI`
- Request page: <https://aktivasi.ruangspasial.my.id/request>
- User guide: <https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis>

License activation uses the RUANG SPASIAL License Hub over HTTPS. An activated
license is checked with License Hub before an export.

## Privacy

For activation and license-status checks, the plugin sends the product code,
fixed code, product name, activation code, and a Device ID to RUANG SPASIAL
License Hub. The Device ID is the first 32 uppercase characters of a SHA-256
hash derived from a stable machine identifier; the raw machine identifier is
not transmitted. Local license and trial state is stored in the current user's
application-data directory. The plugin does not transmit vector geometries,
attribute values, or DXF output.

## Support and issues

- User support: <https://aktivasi.ruangspasial.my.id/help/cad-text-extractor-qgis>
- Bug reports: <https://github.com/purwantodwigeo10/CAD-Text-Extractor/issues>
- Source code: <https://github.com/purwantodwigeo10/CAD-Text-Extractor>

Please include the QGIS version, operating system, input geometry type, steps
to reproduce, and the exact error message in a bug report. Do not include
activation codes or private datasets.

## License

Copyright (C) 2026 Dwi Purwanto / RuangSpasial.

This plugin is free software licensed under the GNU General Public License,
version 3 or any later version. See [LICENSE](LICENSE).
