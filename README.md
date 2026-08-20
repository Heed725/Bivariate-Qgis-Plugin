# Bivariate QGIS Plugin

**Bivariate choropleth mapping for QGIS with 3×3, 4×4 and 5×5 vector/raster classification, Staridas palette import, Leaflet export, and native Print Layout legends.**

[![QGIS](https://img.shields.io/badge/QGIS-3.16%2B-green?style=flat&logo=qgis&logoColor=white)](https://qgis.org)
[![Version](https://img.shields.io/badge/version-0.0.4-orange?style=flat)](https://github.com/Heed725/Bivariate-Qgis-Plugin)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

> Made by [Hemed Lungo](https://github.com/Heed725) · Version **0.0.4** · QGIS ≥ 3.16

## Version 0.0.4

This release keeps the version at **0.0.4** and adds automatic Print Layout layer sensing plus a single axis convention shared by the map and the Print Layout legend.

- **Variable 1 is always Y / vertical.**
- **Variable 2 is always X / horizontal.**
- Vector `Bi_Class` codes store **X first + Y second**: `A1`, `B2`, `C3`, etc.
- Raster bivariate codes also store **X first + Y second**: `11`, `22`, `33`, etc.
- Therefore the map colours/classes and the Print Layout legend matrix correspond directly.
- Print Layout Box and Diamond legends can auto-detect the bivariate layer actually rendered by a layout map.
- Supports both vector and raster bivariate layers.
- Detects 3×3, 4×4 and 5×5 bivariate class grids.
- Vector sensing reads categorized renderer classes such as `A1 … C3`, `A1 … D4`, or `A1 … E5`.
- Raster sensing reads paletted raster values such as `11 … 33`, `11 … 44`, or `11 … 55`.
- The plugin prefers the live layer renderer, so symbology changes can be reflected by the layout legend.
- The legend properties panel includes Auto, Manual, explicit Source layer selection, and Rescan layout.

## Main features

- 30 built-in bivariate colour palettes.
- 3×3, 4×4 and 5×5 bivariate classification.
- Staridas labelled HEX, CSS and JSON palette import.
- Vector bivariate classification and styling.
- Raster bivariate generation and QML styling.
- Native QGIS Print Layout **Box Legend** and **Diamond Legend** items.
- Automatic raster/vector sensing in Print Layout.
- Transpose axes option for manual legend/palette workflows.
- Standalone Leaflet HTML export.

## Installation

1. Download the `0.0.4` plugin ZIP from the GitHub release.
2. Open **QGIS → Plugins → Manage and Install Plugins**.
3. Choose **Install from ZIP**.
4. Select the ZIP and install it.
5. Enable **Bivariate QGIS Plugin**.

For manual installation, place the plugin folder in your QGIS profile's `python/plugins` directory and restart QGIS.

## One axis convention everywhere

The plugin now deliberately uses the same orientation in processing, map symbology, raster codes, and Print Layout legends:

| Variable | Axis | Low → high classes |
|---|---|---|
| **Variable 1** | **Y / vertical** | `1 → 3`, `1 → 4`, or `1 → 5` |
| **Variable 2** | **X / horizontal** | Vector: `A → C/D/E`; Raster: `1 → 3/4/5` |

The important rule is:

> **Bivariate class code = X class first, Y class second.**

For vector data, `C3` means high Variable 2 / X and high Variable 1 / Y.
For raster data, `33` means exactly the same thing.

## Processing tools

The tools appear under **Processing Toolbox → Bivariate QGIS Plugin → Cartography**.

### Bivariate Choropleth Classification

Classifies two numeric vector attributes into a 3×3, 4×4 or 5×5 bivariate class field.

The vector classifier uses:

- **Variable 1 → Y axis / vertical**
- **Variable 2 → X axis / horizontal**

The output `Bi_Class` is written as **Variable 2 letter first + Variable 1 number second**.

### Example: Rainfall as Variable 1 and Temperature as Variable 2

Suppose you choose:

- **Variable 1 = Rainfall**
- **Variable 2 = Temperature**
- **Grid size = 3×3**

The map classification and the Print Layout legend both use this exact matrix:

```text
                         RAINFALL — Variable 1 (Y)
                                  ↑
High rainfall (3)       A3        B3        C3
Mid rainfall  (2)       A2        B2        C2
Low rainfall  (1)       A1        B1        C1
                         └─────────┬─────────┘
                    Low temp    Mid temp    High temp   → TEMPERATURE
                       (A)         (B)         (C)        Variable 2 (X)
```

So:

| Class | Meaning |
|---|---|
| `A1` | Low temperature + low rainfall |
| `C1` | High temperature + low rainfall |
| `A3` | Low temperature + high rainfall |
| `C3` | High temperature + high rainfall |

If a polygon is styled as `C3` on the QGIS map, the `C3` / top-right legend cell in Print Layout uses that same class colour.

For larger grids the same rule is preserved. A 4×4 vector grid uses `A–D` on X and `1–4` on Y; a 5×5 vector grid uses `A–E` on X and `1–5` on Y.

### Apply Bivariate Color Scheme (Vector)

Applies one of the built-in or imported palettes to a categorized vector layer. The styled layer stores its bivariate dimension and palette metadata so Print Layout legends can identify it reliably.

### Bivariate Raster Generator

The raster tool follows the same convention as the vector tool and Print Layout:

- **Raster A = Variable 1 = Y axis**
- **Raster B = Variable 2 = X axis**
- Combined raster code = **Raster B/X class first + Raster A/Y class second**

For the Rainfall/Temperature example:

- **Raster A = Rainfall**
- **Raster B = Temperature**

Then raster code `31` means **high temperature + low rainfall**, while `13` means **low temperature + high rainfall**. Code `33` is high temperature + high rainfall.

This numeric order is intentional so the raster map and Print Layout legend use the same cell positions and colours.

### Bivariate Style Generator (Raster)

Creates and optionally applies a paletted QML style. The style uses the same numeric code order expected by the Print Layout legend: **X first, Y second**.

### Bivariate Leaflet Exporter

Exports a classified vector layer to a standalone interactive Leaflet HTML map.

## Print Layout workflow

1. Add your styled bivariate raster or vector layer to the QGIS project.
2. Open a **Print Layout** and add a map item containing that layer.
3. Choose **Add Item → Bivariate Box Legend** or **Bivariate Diamond Legend**.
4. In **Item Properties → Print Layout layer sensing**, keep **Auto — detect from Print Layout map** or choose a specific source layer.
5. Use **Rescan layout** after changing the map's layer set or symbology.
6. The detected legend uses the same class colours and class positions as the map layer.
7. If no valid bivariate renderer is detected, switch to Manual and choose the palette/grid size yourself.

The detector first checks layers actually rendered by the Print Layout map through `QgsLayoutItemMap.layersToRender()`. If the layout has no resolvable map layers, it falls back to project raster/vector layers.

### Print Layout labels

The Print Layout label fields now use the same variable numbering as the processing tools:

- **Variable 2 (X)** — horizontal axis
- **Variable 1 (Y)** — vertical axis

For Rainfall/Temperature enter:

- **Variable 2 (X) = Temperature (°C)**
- **Variable 1 (Y) = Rainfall (mm)**

This means there is no separate Print Layout axis convention to remember.

## Print Layout properties

- Source layer: Auto, Manual, or an explicit raster/vector layer.
- Palette: built-in palette or custom Staridas import.
- Grid size: 3×3, 4×4 or 5×5.
- Transpose axes for manual workflows.
- Cell size and gap.
- Fit and center grid inside item.
- **Variable 2 (X)** label.
- **Variable 1 (Y)** label.
- Show axis labels.
- Show class codes.
- Outline colour and width.

## Staridas palette support

The plugin supports labelled output from the **Staridas Geography Bivariate Color Palette Builder**, including formats such as:

```text
A1 #FAEEC6
A2 #B8BD74
A3 #768D21
```

It also accepts CSS variables and JSON. Labels are used to preserve the correct bivariate class order even when entries are shuffled.

## Repository structure

```text
__init__.py
plugin_core.py
metadata.txt
palettes.py
bivariate_provider.py
bivariate_choropleth.py
apply_bivariate_colors.py
bivariate_raster_generator.py
bivariate_style_generator.py
bivariate_export_leaflet.py
layout_items.py
bivariate_legend_box_generator.py
bivariate_legend_diamond_generator.py
icon.png
```

## Requirements

- QGIS 3.16 or later.
- Python included with QGIS.
- GDAL/OGR and NumPy bundled with normal QGIS installations.

## Credits

- **Spiros Staridas** — creator of the Staridas Geography Bivariate Color Palette Builder and its labelled palette export formats used by this plugin.
- **Joshua Stevens** — bivariate choropleth methodology reference.
- **DataPlotly** — inspiration for the QGIS custom Print Layout item registration pattern.
- Bivariate cartography community — palette inspiration.

## License

GNU General Public License v2.0 or later.

---

**Bivariate QGIS Plugin · v0.0.4 · Hemed Lungo**
