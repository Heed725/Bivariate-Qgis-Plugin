# Bivariate QGIS Plugin

**Bivariate choropleth mapping for QGIS with 3×3, 4×4 and 5×5 vector/raster classification, Staridas palette import, Leaflet export, and native Print Layout legends.**

[![QGIS](https://img.shields.io/badge/QGIS-3.16%2B-green?style=flat&logo=qgis&logoColor=white)](https://qgis.org)
[![Version](https://img.shields.io/badge/version-0.0.4-orange?style=flat)](https://github.com/Heed725/Bivariate-Qgis-Plugin)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

> Made by [Hemed Lungo](https://github.com/Heed725) · Version **0.0.4** · QGIS ≥ 3.16

## Version 0.0.4

This release keeps the version at **0.0.4** and adds automatic Print Layout layer sensing.

- **Print Layout Box and Diamond legends can auto-detect the bivariate layer actually rendered by a layout map.**
- Supports both **vector** and **raster** bivariate layers.
- Detects **3×3, 4×4 and 5×5** bivariate class grids.
- Vector sensing reads categorized renderer classes such as `A1 … C3`, `A1 … D4`, or `A1 … E5`.
- Raster sensing reads paletted raster values such as `11 … 33`, `11 … 44`, or `11 … 55`.
- The plugin prefers the **live layer renderer**, so symbology changes can be reflected by the layout legend.
- Vector/raster styling tools also store lightweight palette metadata as a fallback for reliable detection.
- The legend properties panel includes **Auto**, **Manual**, explicit **Source layer** selection, and **Rescan layout**.
- Existing saved legends without a linked source remain in manual mode for compatibility.

## Main features

- 30 built-in bivariate colour palettes.
- 3×3, 4×4 and 5×5 bivariate classification.
- Staridas labelled HEX, CSS and JSON palette import.
- Vector bivariate classification and styling.
- Raster bivariate generation and QML styling.
- Native QGIS Print Layout **Box Legend** and **Diamond Legend** items.
- Transpose axes option.
- Standalone Leaflet HTML export.

## Installation

1. Download the `0.0.4` plugin ZIP from the GitHub release.
2. Open **QGIS → Plugins → Manage and Install Plugins**.
3. Choose **Install from ZIP**.
4. Select the ZIP and install it.
5. Enable **Bivariate QGIS Plugin**.

For manual installation, place the plugin folder in your QGIS profile's `python/plugins` directory and restart QGIS.

## Processing tools

The tools appear under **Processing Toolbox → Bivariate QGIS Plugin → Cartography**.

### Bivariate Choropleth Classification

Classifies two numeric vector attributes into a 3×3, 4×4 or 5×5 bivariate class field.

The vector classifier uses a fixed axis convention:

| Processing input | Axis | Class direction |
|---|---|---|
| **Variable 1** | **Y axis / vertical** | `1 → 3` for a 3×3 grid, from low to high |
| **Variable 2** | **X axis / horizontal** | `A → C` for a 3×3 grid, from low to high |

The output `Bi_Class` code is written as **Variable 2 letter first + Variable 1 number second**. For example, `C3` means the highest class of Variable 2 and the highest class of Variable 1.

### Example: Rainfall as Variable 1 and Temperature as Variable 2

Suppose you choose:

- **Variable 1 = Rainfall**
- **Variable 2 = Temperature**
- **Grid size = 3×3**

The plugin places **Rainfall on the Y axis** and **Temperature on the X axis**:

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

So the corner classes mean:

| Class | Meaning |
|---|---|
| `A1` | Low temperature + low rainfall |
| `C1` | High temperature + low rainfall |
| `A3` | Low temperature + high rainfall |
| `C3` | High temperature + high rainfall |

For larger grids the same rule is preserved: **Variable 1 remains vertical/Y** and **Variable 2 remains horizontal/X**. A 4×4 grid uses `1–4` vertically and `A–D` horizontally; a 5×5 grid uses `1–5` vertically and `A–E` horizontally.

#### Print Layout labels for this example

In the **Bivariate Box Legend** properties, the current label fields use **Variable A** for the horizontal/X label and **Variable B** for the vertical/Y label. Therefore, for this Rainfall/Temperature example enter:

- **Variable A = Temperature (°C)** — X axis
- **Variable B = Rainfall (mm)** — Y axis

If **Transpose axes (swap X ↔ Y)** is enabled in manual mode, the displayed axes are swapped.

### Apply Bivariate Color Scheme (Vector)

Applies one of the built-in or imported palettes to a categorized vector layer. The styled layer stores its bivariate dimension and palette metadata so Print Layout legends can identify it reliably.

### Bivariate Raster Generator

Combines two raster variables into a bivariate raster classification.

### Bivariate Style Generator (Raster)

Creates and optionally applies a paletted QML style. When auto-applied, the raster stores its bivariate dimension and palette metadata for Print Layout sensing.

### Bivariate Leaflet Exporter

Exports a classified vector layer to a standalone interactive Leaflet HTML map.

## Print Layout workflow

1. Add your styled bivariate raster or vector layer to the QGIS project.
2. Open a **Print Layout** and add a map item containing that layer.
3. Choose **Add Item → Bivariate Box Legend** or **Bivariate Diamond Legend**.
4. In **Item Properties → Print Layout layer sensing**, keep **Auto — detect from Print Layout map** or choose a specific source layer.
5. Use **Rescan layout** after changing the map's layer set or symbology.
6. If no valid bivariate renderer is detected, switch to **Manual** and choose the palette/grid size yourself.

The detector first checks the layers actually rendered by the Print Layout map through `QgsLayoutItemMap.layersToRender()`. If the layout has no resolvable map layers, it falls back to project raster/vector layers.

## Print Layout properties

- Source layer: Auto, Manual, or an explicit raster/vector layer.
- Palette: built-in palette or custom Staridas import.
- Grid size: 3×3, 4×4 or 5×5.
- Transpose axes.
- Cell size and gap.
- Fit and center grid inside item.
- Variable A / Variable B labels.
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
