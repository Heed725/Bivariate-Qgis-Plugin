# Bivariate QGIS Plugin

**Bivariate choropleth mapping for QGIS — 30 palettes, vector & raster classification, interactive Leaflet export, and native Print Layout legend items.**

[![QGIS](https://img.shields.io/badge/QGIS-3.16%2B-green?style=flat&logo=qgis&logoColor=white)](https://qgis.org)
[![Download ZIP](https://img.shields.io/badge/Download-ZIP-blue?style=flat&logo=github)](https://github.com/Heed725/Bivariate-Qgis-Plugin/releases/latest/download/bivariate_qgis_plugin.zip)
[![Version](https://img.shields.io/badge/version-0.0.1-orange?style=flat)](https://github.com/Heed725/Bivariate-Qgis-Plugin)
[![License: GPL v2](https://img.shields.io/badge/License-GPL%20v2-blue.svg)](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html)

> Made by [Hemed Lungo](https://github.com/Heed725) · Version 0.0.1 · QGIS ≥ 3.16

---

## What is a bivariate choropleth map?

A bivariate choropleth map encodes **two variables simultaneously** using a blended 3×3 colour grid. Each region receives one of nine colours representing a combination of both variables — for example, high population density *and* high poverty rate. This technique, popularised by [Joshua Stevens](https://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/), reveals spatial relationships that two separate maps cannot show together.

```
         Low A   Mid A   High A
High B  [ C1 ]  [ C2 ]  [ C3 ]
 Mid B  [ B1 ]  [ B2 ]  [ B3 ]
 Low B  [ A1 ]  [ A2 ]  [ A3 ]
```

---

## Features

- 30 built-in colour palettes across five style families
- 5 Processing tools for vector classification, raster processing, QML styling, and web export
- 2 native Print Layout legend items — drag-and-drop Box and Diamond legends onto your layout canvas
- Fully styled standalone Leaflet HTML export with interactive sidebar and hover highlighting
- No external dependencies beyond QGIS itself

---

## Installation

### From ZIP (recommended)

1. Download `bivariate_qgis_plugin.zip`
2. Open QGIS → **Plugins → Manage and Install Plugins → Install from ZIP**
3. Select the downloaded ZIP → **Install Plugin**
4. Enable **Bivariate QGIS Plugin** in the Installed tab

### Manual

Unzip into your QGIS plugins folder and restart QGIS:

| OS | Path |
|----|------|
| Windows | `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\` |
| macOS | `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/` |
| Linux | `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/` |

---

## Processing Tools

All tools appear under **Processing Toolbox → Bivariate QGIS Plugin → Cartography**.

### 1 · Bivariate Choropleth Classification

Classifies two numeric attribute fields into a 3×3 bivariate scheme.

| Parameter | Description |
|-----------|-------------|
| Input layer | Any polygon layer |
| Variable 1 | Numeric field → vertical axis (classes 1–3) |
| Variable 2 | Numeric field → horizontal axis (classes A–C) |
| Method | Quantile · Natural Breaks · Equal Interval |

Output adds three new fields to a copy of the layer:

| Field | Values | Meaning |
|-------|--------|---------|
| `Var1_Class` | 1 / 2 / 3 | Low / Mid / High for Variable 1 |
| `Var2_Class` | A / B / C | Low / Mid / High for Variable 2 |
| `Bi_Class` | A1 … C3 | Combined class used for styling |

---

### 2 · Apply Bivariate Color Scheme

Styles a layer that already has a `Bi_Class` field using any of the 30 built-in palettes or custom hex codes.

| Parameter | Description |
|-----------|-------------|
| Input layer | Layer with `Bi_Class` field |
| Color palette | Any of the 30 built-in palettes |
| Custom colors | 9 comma-separated hex codes — order: A1, A2, A3, B1, B2, B3, C1, C2, C3 |
| Outline color | Cell border colour |
| Outline width | Border width |

---

### 3 · Bivariate Raster Generator

Classifies two rasters into terciles (1/2/3) and combines them into a bivariate raster with pixel values 11–33.

| Parameter | Description |
|-----------|-------------|
| Raster A | First input raster (e.g. temperature) |
| Raster B | Second input raster (e.g. precipitation) |
| Reproject & align | Snap Raster B to Raster A extent and resolution |
| Divide Raster B | Optional divisor (e.g. `30` to convert monthly totals to daily averages) |

Outputs: `Raster A class (1–3)` · `Raster B class (1–3)` · `Bivariate raster (11–33)`

---

### 4 · Bivariate Style Generator

Generates a `.qml` colour style file for a bivariate raster (values 11–33) and optionally applies it directly.

| Parameter | Description |
|-----------|-------------|
| Input raster | Bivariate raster with pixel values 11–33 |
| Color palette | Any of the 30 palettes or custom |
| Auto-apply | Apply the QML directly to the input raster |
| Output QML | Destination path for the `.qml` file |

To apply manually: **Layer Properties → Symbology → Style → Load Style**

---

### 5 · Bivariate Leaflet Exporter

Exports a classified vector layer to a **standalone Leaflet HTML map**. No server required — single self-contained `.html` file.

| Parameter | Description |
|-----------|-------------|
| Input layer | Polygon layer with `Bi_Class` field |
| Class field | Field containing values A1–C3 |
| Label field | Field used for region names in tooltips |
| Color palette | Any of the 30 palettes or custom |
| Map title / subtitle | Displayed in the sidebar header |
| Variable A / B labels | Axis labels shown in the legend |
| Basemap | CartoDB Positron · CartoDB Dark Matter · OpenStreetMap · Stamen Toner Lite |
| Dark theme | Default sidebar to dark mode |

**Web map features:**
- Palette-matched fill and outline colours for every region
- Styled sidebar: title, bivariate legend grid, variable descriptions, class distribution chips
- Interactive legend — hover a cell to dim all non-matching regions; click to lock the filter
- Click-to-filter class chips showing region counts per class
- Hover tooltip and click popup showing all feature attributes
- Dark / light theme toggle
- Basemap switcher (4 options)
- Fullscreen button and scale bar

---

## Print Layout Items

Two custom legend items are available in the **Print Layout** under **Add Item**. They do not appear in the Processing Toolbox.

### Bivariate Box Legend

A 3×3 grid of square coloured cells with optional axis labels.

```
[ C1 ][ C2 ][ C3 ]   ← High B
[ B1 ][ B2 ][ B3 ]
[ A1 ][ A2 ][ A3 ]   ← Low B
  ↑               ↑
 Low A          High A
```

### Bivariate Diamond Legend

A 3×3 grid of diamond shapes in a 45°-rotated layout. Variable A increases along the bottom-right diagonal; Variable B increases along the bottom-left diagonal.

### Item Properties (both items)

Use the **Item Properties** panel after placing an item on the canvas:

| Property | Description |
|----------|-------------|
| Palette | Any of the 30 built-in palettes |
| Custom colors | 9 comma-separated hex codes (order: 11–33) |
| Cell size | Size of each cell in mm |
| Gap | Spacing between cells in mm |
| Variable A / B labels | Axis label text |
| Show axis labels | Toggle axis arrows and labels (box only) |
| Show class codes | Overlay class codes (A1…C3) on each cell |
| Outline color | Cell border colour (click to open colour picker) |
| Outline width | Border width in mm |

All property changes preview live on the layout canvas. Settings are saved with the QGIS project (`.qgs` / `.qpt`).

---

## The 30 Colour Palettes

| Group | Palettes |
|-------|---------|
| Classic | Bluegill · BlueGold · BlueOr · BlueYl · Brown · Brown2 |
| Dark | DkBlue · DkBlue2 · DkCyan · DkCyan2 · DkViolet · DkViolet2 |
| Warm | GrPink · GrPink2 · PinkGrn · PurpleGrn · PurpleOr · PinkGrn2 |
| Vivid | BlueRed · GrenYellow · GreenPurple · BlueYellowBlack |
| Pale | PaleRedBlue · GreenPinkPurple · BlueGreenPurple · BlueYellow · BlueOrange · PaleblueRed · PurpleGreen2 |

Every palette defines 9 hex colours in code order `11, 12, 13, 21, 22, 23, 31, 32, 33` (Low-Low → High-High). The same order applies when supplying custom colours to any tool.

---

## Typical Workflows

### Vector → print map

```
Polygon layer (two numeric fields)
  │
  ├─ [1] Bivariate Choropleth Classification  →  adds Bi_Class field
  │
  ├─ [2] Apply Bivariate Color Scheme         →  styles the layer
  │
  └─ Print Layout → Add Item
       → Bivariate Box Legend
       → Bivariate Diamond Legend
```

### Vector → web map

```
Polygon layer (two numeric fields)
  │
  ├─ [1] Bivariate Choropleth Classification  →  adds Bi_Class field
  │
  └─ [5] Bivariate Leaflet Exporter           →  standalone HTML map
```

### Raster → styled map

```
Raster A  +  Raster B
  │
  ├─ [3] Bivariate Raster Generator           →  bivariate raster (11–33)
  │
  └─ [4] Bivariate Style Generator            →  QML applied to raster
```

---

## Repository Structure

```
bivariate_plugin/
├── __init__.py                            QGIS plugin entry point
├── plugin_core.py                         Plugin class — registers provider & layout items
├── metadata.txt                           Plugin metadata (name, version, author)
├── palettes.py                            All 30 colour palettes
├── bivariate_provider.py                  Processing provider
├── bivariate_choropleth.py                Tool 1: Choropleth Classification
├── apply_bivariate_colors.py              Tool 2: Apply Color Scheme
├── bivariate_raster_generator.py          Tool 3: Raster Generator
├── bivariate_style_generator.py           Tool 4: Style Generator (QML)
├── bivariate_export_leaflet.py            Tool 5: Leaflet Exporter
├── layout_items.py                        Print Layout items (Box + Diamond)
├── bivariate_legend_box_generator.py      Box legend shapefile (layout use)
├── bivariate_legend_diamond_generator.py  Diamond legend shapefile (layout use)
└── icon.png                               Plugin icon
```

---

## Requirements

- QGIS 3.16 or later
- Python 3.9+
- GDAL / OGR (bundled with QGIS)
- NumPy (bundled with QGIS)

The exported Leaflet map loads tile layers and the Leaflet JS library from a CDN, so an internet connection is required in the browser to display the basemap. All other map content (features, colours, popups) is embedded in the HTML file.

---

## Known Issues

- **Duplicate layout item icons** — If you reload the plugin using Plugin Reloader or disable/re-enable it without restarting QGIS, the Box and Diamond legend icons may appear multiple times in the Add Item toolbar. This is a QGIS PyQGIS limitation: the GUI layout item registry has no remove API, so old entries persist in the session. A fresh QGIS restart resolves this and the guard in `plugin_core.py` prevents further accumulation.
- **Diamond axis labels** — The rotated diamond grid does not display axis label arrows. Use the Box Legend if labelled axes are required for your map layout.

---

## Credits

- Bivariate methodology: [Joshua Stevens](https://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/)
- Web export inspired by [qgis2web](https://github.com/tomchadwin/qgis2web)
- Print Layout item pattern adapted from [DataPlotly](https://github.com/ghtmtt/DataPlotly)
- Colour palettes from the bivariate cartography community

---

## License

GNU General Public License v2.0 or later.

---

*Bivariate QGIS Plugin · v0.0.1 · Hemed Lungo*
