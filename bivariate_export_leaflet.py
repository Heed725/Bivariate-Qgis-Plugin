"""
QGIS Processing Script: Bivariate Leaflet Exporter (qgis2web-inspired)
Exports a bivariate-classified vector layer to a fully-styled standalone Leaflet HTML map.
- Full palette-matched styling (no grey placeholders)
- Styled sidebar with legend, variable descriptions, and data insights
- Hover highlight + click popup with all attributes
- Bivariate 3×3 legend with axis labels and hover-to-highlight interaction
- 4 basemap options
- Dark/light theme switch
- Search bar, fullscreen, zoom controls
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, CODE_LABELS


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
)
import json, sys, os

PALETTE_NAMES   = list(PALETTES.keys()) + ['Custom (enter hex codes below)']
VECTOR_CLASSES  = ['A1','A2','A3','B1','B2','B3','C1','C2','C3']
BASEMAPS = [
    ('CartoDB Positron (Light)',
     'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
     '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>'),
    ('CartoDB Dark Matter',
     'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
     '&copy; OpenStreetMap &copy; CARTO'),
    ('OpenStreetMap',
     'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
     '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'),
    ('Stamen Toner Lite',
     'https://stamen-tiles-{s}.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}.png',
     'Map tiles by <a href="http://stamen.com">Stamen Design</a>'),
]


def _is_light(hex_color):
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return (r*299 + g*587 + b*114) / 1000 > 155


class BivariateLeafletExporter(QgsProcessingAlgorithm):
    INPUT         = 'INPUT'
    CLASS_FIELD   = 'CLASS_FIELD'
    LABEL_FIELD   = 'LABEL_FIELD'
    EXTRA_FIELDS  = 'EXTRA_FIELDS'
    PALETTE       = 'PALETTE'
    CUSTOM_COLORS = 'CUSTOM_COLORS'
    MAP_TITLE     = 'MAP_TITLE'
    MAP_SUBTITLE  = 'MAP_SUBTITLE'
    VAR_A_LABEL   = 'VAR_A_LABEL'
    VAR_B_LABEL   = 'VAR_B_LABEL'
    BASEMAP       = 'BASEMAP'
    DARK_THEME    = 'DARK_THEME'
    OUTPUT        = 'OUTPUT'

    def tr(self, t): return QCoreApplication.translate('BivariateLeafletExporter', t)
    def createInstance(self): return BivariateLeafletExporter()
    def name(self):        return 'bivariate_leaflet_exporter'
    def displayName(self): return self.tr('Bivariate Leaflet Exporter')
    def group(self):       return self.tr('Cartography')
    def groupId(self):     return 'cartography'
    def shortHelpString(self):
        return self.tr(
            'Exports a bivariate-classified layer to a fully styled standalone Leaflet HTML map.\n\n'
            'Features:\n'
            '• Full palette-matched fill and outline colors (no grey)\n'
            '• Styled sidebar: title, subtitle, bivariate legend, variable descriptions\n'
            '• Hover highlight + click popups with all attribute values\n'
            '• Interactive legend: hover a cell to highlight matching regions\n'
            '• Dark/light theme switch button\n'
            '• Basemap switcher (4 options)\n'
            '• Zoom, scale bar, attribution controls\n\n'
            'Requires a layer with Bi_Class field (A1–C3) from Bivariate Choropleth Classification tool.')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, self.tr('Input bivariate layer'),
            [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterField(
            self.CLASS_FIELD, self.tr('Bivariate class field'),
            parentLayerParameterName=self.INPUT, defaultValue='Bi_Class'))
        self.addParameter(QgsProcessingParameterField(
            self.LABEL_FIELD, self.tr('Region name / label field'),
            parentLayerParameterName=self.INPUT, optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.EXTRA_FIELDS,
            self.tr('Extra popup fields (comma-separated field names, leave blank for all)'),
            optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.PALETTE, self.tr('Color palette'),
            options=PALETTE_NAMES, defaultValue=6))
        self.addParameter(QgsProcessingParameterString(
            self.CUSTOM_COLORS,
            self.tr('Custom colors — 9 hex codes, order A1,A2,A3,B1,B2,B3,C1,C2,C3'),
            optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.MAP_TITLE, self.tr('Map title'),
            defaultValue='Bivariate Choropleth Map'))
        self.addParameter(QgsProcessingParameterString(
            self.MAP_SUBTITLE, self.tr('Map subtitle / description'),
            defaultValue='Bivariate classification of two variables across regions.',
            optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.VAR_A_LABEL, self.tr('Variable A label (horizontal axis)'),
            defaultValue='Variable A'))
        self.addParameter(QgsProcessingParameterString(
            self.VAR_B_LABEL, self.tr('Variable B label (vertical axis)'),
            defaultValue='Variable B'))
        self.addParameter(QgsProcessingParameterEnum(
            self.BASEMAP, self.tr('Default basemap'),
            options=[b[0] for b in BASEMAPS], defaultValue=0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.DARK_THEME, self.tr('Default to dark sidebar theme?'),
            defaultValue=False))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUTPUT, self.tr('Output HTML file'), 'HTML files (*.html)'))

    def processAlgorithm(self, parameters, context, feedback):
        layer      = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        cls_field  = self.parameterAsString(parameters, self.CLASS_FIELD, context)
        lbl_field  = self.parameterAsString(parameters, self.LABEL_FIELD, context)
        extra_str  = self.parameterAsString(parameters, self.EXTRA_FIELDS, context)
        pal_idx    = self.parameterAsInt(parameters, self.PALETTE, context)
        custom     = self.parameterAsString(parameters, self.CUSTOM_COLORS, context)
        title      = self.parameterAsString(parameters, self.MAP_TITLE, context)
        subtitle   = self.parameterAsString(parameters, self.MAP_SUBTITLE, context)
        var_a      = self.parameterAsString(parameters, self.VAR_A_LABEL, context)
        var_b      = self.parameterAsString(parameters, self.VAR_B_LABEL, context)
        bm_idx     = self.parameterAsInt(parameters, self.BASEMAP, context)
        dark_def   = self.parameterAsBoolean(parameters, self.DARK_THEME, context)
        out_html   = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        if not layer or not layer.isValid():
            raise QgsProcessingException('Invalid input layer')

        # Resolve palette
        if pal_idx == len(PALETTE_NAMES) - 1:
            colors = [c.strip() for c in custom.split(',')]
            if len(colors) != 9: raise QgsProcessingException('Need 9 hex codes')
        else:
            colors = PALETTES[PALETTE_NAMES[pal_idx]]

        color_map = dict(zip(VECTOR_CLASSES, colors))

        # Outline colors: slightly darker version of fill
        def darken(hex_c, factor=0.65):
            h = hex_c.lstrip('#')
            r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
            return '#{:02x}{:02x}{:02x}'.format(int(r*factor),int(g*factor),int(b*factor))

        outline_map = {cls: darken(col) for cls, col in color_map.items()}

        # Extra popup fields
        extra_fields = [f.strip() for f in extra_str.split(',') if f.strip()] if extra_str else []

        # Reproject to WGS84
        wgs84 = QgsCoordinateReferenceSystem('EPSG:4326')
        xform = QgsCoordinateTransform(layer.crs(), wgs84, QgsProject.instance())

        all_layer_fields = [f.name() for f in layer.fields()]
        popup_fields = extra_fields if extra_fields else all_layer_fields

        features = []
        class_counts = {c: 0 for c in VECTOR_CLASSES}
        total = layer.featureCount()

        for i, feat in enumerate(layer.getFeatures()):
            if feedback.isCanceled(): break
            geom = feat.geometry()
            geom.transform(xform)
            cls   = str(feat[cls_field]) if feat[cls_field] else 'NoData'
            label = str(feat[lbl_field]) if lbl_field and feat[lbl_field] else ''
            if cls in class_counts: class_counts[cls] += 1

            props = {'_cls': cls, '_label': label,
                     '_fill': color_map.get(cls, '#aaaaaa'),
                     '_stroke': outline_map.get(cls, '#888888')}
            for fname in popup_fields:
                if fname in all_layer_fields:
                    val = feat[fname]
                    props[fname] = '' if val is None else str(val)

            try:
                geoj = json.loads(geom.asJson())
            except Exception:
                continue
            features.append({'type':'Feature','properties':props,'geometry':geoj})
            feedback.setProgress(int(i * 85 / total))

        geojson_str = json.dumps({'type':'FeatureCollection','features':features})

        # Build legend grid HTML
        # Row order top→bottom in HTML = C (High B) → B (Mid B) → A (Low B)
        # Column order left→right = 1 (Low A) → 2 (Mid A) → 3 (High A)
        # So grid reads: A1 A2 A3 (bottom), B1 B2 B3 (middle), C1 C2 C3 (top)
        grid_order = [
            ('C1',6),('C2',7),('C3',8),
            ('B1',3),('B2',4),('B3',5),
            ('A1',0),('A2',1),('A3',2),
        ]
        legend_cells_html = ''
        for cls, idx in grid_order:
            c = colors[idx]
            legend_cells_html += (
                f'<div class="lc" data-cls="{cls}" '
                f'style="background:{c}" '
                f'title="{cls}"></div>\n'
            )

        # Basemap tile URLs as JS array
        basemaps_js = json.dumps([{'name':b[0],'url':b[1],'attr':b[2]} for b in BASEMAPS])
        default_dark = 'true' if dark_def else 'false'
        pal_name_safe = PALETTE_NAMES[pal_idx] if pal_idx < len(PALETTES) else 'Custom'

        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet-fullscreen@1.0.2/dist/leaflet.fullscreen.css"/>
<style>
/* ── Reset ── */
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{height:100%;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,sans-serif}}

/* ── Layout ── */
.app{{display:flex;height:100vh;overflow:hidden}}
.sidebar{{width:280px;flex-shrink:0;display:flex;flex-direction:column;
  overflow-y:auto;transition:background .3s,color .3s;z-index:500;
  box-shadow:2px 0 12px rgba(0,0,0,.15)}}
.sidebar.light{{background:#fafaf8;color:#1a1a1a}}
.sidebar.dark{{background:#1c1c1e;color:#f0f0ee}}
#map{{flex:1;min-width:0}}

/* ── Sidebar sections ── */
.sb-header{{padding:18px 18px 14px;border-bottom:1px solid rgba(128,128,128,.15)}}
.sb-title{{font-size:17px;font-weight:700;line-height:1.3;margin-bottom:5px}}
.sb-subtitle{{font-size:11.5px;opacity:.65;line-height:1.55}}
.sb-section{{padding:14px 18px;border-bottom:1px solid rgba(128,128,128,.12)}}
.sb-section-title{{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;opacity:.5;margin-bottom:10px}}

/* ── Legend grid ── */
.legend-wrap{{display:flex;gap:10px;align-items:flex-start;margin-top:4px}}
.legend-axes-y{{display:flex;flex-direction:column;align-items:center;
  justify-content:space-between;padding-right:6px;padding-top:2px}}
.ax-label-y{{font-size:9px;font-weight:700;opacity:.6;letter-spacing:.05em;
  text-transform:uppercase;white-space:nowrap}}
.ax-arrow-y{{font-size:11px;opacity:.45;line-height:1;margin:4px 0;
  writing-mode:vertical-rl;transform:rotate(180deg);
  font-weight:600;letter-spacing:.04em;opacity:.5}}
.legend-right{{display:flex;flex-direction:column;gap:0}}
.legend-grid{{display:grid;grid-template-columns:repeat(3,34px);
  grid-template-rows:repeat(3,34px);gap:3px}}
.lc{{border-radius:4px;cursor:pointer;transition:transform .12s,box-shadow .12s;
  border:1.5px solid rgba(0,0,0,.1)}}
.lc:hover{{transform:scale(1.15);box-shadow:0 2px 8px rgba(0,0,0,.25);z-index:2;position:relative}}
.lc.dimmed{{opacity:.18}}
.lc.highlighted{{transform:scale(1.1);box-shadow:0 0 0 2.5px rgba(0,0,0,.55)}}
.legend-axes-x{{display:flex;justify-content:space-between;align-items:center;
  margin-top:5px;width:108px}}
.ax-x-label{{font-size:9px;font-weight:700;opacity:.6;letter-spacing:.04em;
  text-transform:uppercase}}
.ax-x-arrow{{font-size:10px;opacity:.4;font-weight:600}}

/* ── Class stats ── */
.class-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:4px}}
.class-chip{{border-radius:4px;padding:4px 5px;text-align:center;font-size:10px;
  font-weight:700;cursor:pointer;transition:opacity .15s,transform .15s;
  border:1px solid rgba(0,0,0,.1)}}
.class-chip:hover{{transform:scale(1.05)}}

/* ── Color key ── */
.color-key{{display:flex;flex-wrap:wrap;gap:5px}}
.ck-item{{display:flex;align-items:center;gap:5px;font-size:10.5px}}
.ck-swatch{{width:12px;height:12px;border-radius:2px;flex-shrink:0;
  border:1px solid rgba(0,0,0,.1)}}

/* ── Controls ── */
.ctrl-row{{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}}
.ctrl-btn{{padding:5px 10px;border-radius:5px;border:1px solid rgba(128,128,128,.3);
  background:transparent;font-size:11px;cursor:pointer;font-weight:500;
  transition:background .15s;color:inherit}}
.ctrl-btn:hover{{background:rgba(128,128,128,.15)}}
.ctrl-btn.active{{background:rgba(128,128,128,.25)}}

/* ── Popup ── */
.bv-popup{{min-width:200px;max-width:260px;font-size:12px}}
.bv-popup .region-name{{font-size:14px;font-weight:700;margin-bottom:6px;
  display:flex;align-items:center;gap:8px}}
.bv-popup .cls-badge{{display:inline-block;padding:2px 8px;border-radius:4px;
  font-size:11px;font-weight:700}}
.bv-popup table{{width:100%;border-collapse:collapse;margin-top:6px}}
.bv-popup td{{padding:3px 0;font-size:11px;border-bottom:1px solid rgba(128,128,128,.1)}}
.bv-popup td:first-child{{color:#888;width:45%;font-weight:500}}
.bv-popup td:last-child{{font-weight:500;text-align:right}}

/* ── Tooltip ── */
.bv-tooltip{{background:rgba(255,255,255,.96);color:#1a1a1a;
  padding:5px 10px;border-radius:4px;font-size:12px;font-weight:600;
  box-shadow:0 2px 8px rgba(0,0,0,.2);pointer-events:none;
  border-left:4px solid #555}}

/* ── No-data ── */
.nodata-swatch{{display:inline-block;width:14px;height:14px;
  background:#cccccc;border-radius:2px;vertical-align:middle;margin-right:4px;
  border:1px solid #aaa}}

/* ── Dark mode adjustments ── */
.sidebar.dark .ctrl-btn{{border-color:rgba(255,255,255,.2)}}
.sidebar.dark .bv-popup td:first-child{{color:#aaa}}

/* ── Leaflet overrides ── */
.leaflet-container{{font-family:inherit}}
.leaflet-control-attribution{{font-size:10px}}
</style>
</head>
<body>
<div class="app">

<!-- ════════════════ SIDEBAR ════════════════ -->
<div class="sidebar light" id="sidebar">

  <div class="sb-header">
    <div class="sb-title" id="sb-title">{title}</div>
    <div class="sb-subtitle" id="sb-subtitle">{subtitle}</div>
  </div>

  <!-- Legend -->
  <div class="sb-section">
    <div class="sb-section-title">Legend</div>
    <div class="legend-wrap">

      <!-- Y axis: variable B label rotated -->
      <div class="legend-axes-y" style="height:108px">
        <div class="ax-label-y" style="writing-mode:vertical-rl;transform:rotate(180deg)">High</div>
        <div class="ax-x-arrow" style="writing-mode:vertical-rl;transform:rotate(180deg)">↑</div>
        <div class="ax-label-y" style="writing-mode:vertical-rl;transform:rotate(180deg)">Low</div>
      </div>

      <!-- Grid + X axis -->
      <div class="legend-right">
        <div class="legend-grid" id="legend-grid">
          {legend_cells_html}
        </div>
        <!-- X axis labels: spaced across full grid width -->
        <div class="legend-axes-x">
          <span class="ax-x-label">Low</span>
          <span class="ax-x-arrow">→</span>
          <span class="ax-x-label">High</span>
        </div>
        <!-- X axis variable name centred below -->
        <div style="font-size:9px;font-weight:700;opacity:.5;text-align:center;
          margin-top:3px;letter-spacing:.04em;text-transform:uppercase">{var_a}</div>
      </div>

    </div>

    <!-- Y axis variable name below the whole block -->
    <div style="font-size:9px;font-weight:700;opacity:.5;margin-top:6px;
      letter-spacing:.04em;text-transform:uppercase">{var_b}</div>

    <div style="margin-top:6px;font-size:10.5px;opacity:.5">
      Hover a cell to highlight regions on the map
    </div>
  </div>

  <!-- Variable descriptions -->
  <div class="sb-section">
    <div class="sb-section-title">Variables</div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;align-items:center;gap:8px">
        <div style="width:18px;height:18px;border-radius:3px;
          background:linear-gradient(135deg,{colors[0]},{colors[6]});
          border:1px solid rgba(0,0,0,.1);flex-shrink:0"></div>
        <div>
          <div style="font-size:12px;font-weight:600">{var_a}</div>
          <div style="font-size:10.5px;opacity:.55">Horizontal axis</div>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:8px">
        <div style="width:18px;height:18px;border-radius:3px;
          background:linear-gradient(135deg,{colors[0]},{colors[2]});
          border:1px solid rgba(0,0,0,.1);flex-shrink:0"></div>
        <div>
          <div style="font-size:12px;font-weight:600">{var_b}</div>
          <div style="font-size:10.5px;opacity:.55">Vertical axis</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Class distribution -->
  <div class="sb-section">
    <div class="sb-section-title">Class distribution</div>
    <div class="class-grid" id="class-grid"></div>
    <div style="margin-top:8px;font-size:10px;opacity:.45">
      <span class="nodata-swatch"></span>No data / unclassified
    </div>
  </div>

  <!-- Palette info -->
  <div class="sb-section">
    <div class="sb-section-title">Palette · {pal_name_safe}</div>
    <div class="color-key" id="color-key"></div>
  </div>

  <!-- Controls -->
  <div class="sb-section">
    <div class="sb-section-title">Controls</div>
    <div class="ctrl-row">
      <button class="ctrl-btn" id="theme-btn" onclick="toggleTheme()">☾ Dark mode</button>
      <button class="ctrl-btn" id="reset-btn" onclick="resetHighlight()">Reset highlight</button>
    </div>
    <div class="ctrl-row" style="margin-top:8px">
      <select id="bm-select" onchange="switchBasemap(this.value)"
        style="padding:5px 8px;border-radius:5px;border:1px solid rgba(128,128,128,.3);
          background:transparent;font-size:11px;cursor:pointer;color:inherit">
      </select>
    </div>
  </div>

</div><!-- /sidebar -->

<!-- ════════════════ MAP ════════════════ -->
<div id="map"></div>

</div><!-- /app -->

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet-fullscreen@1.0.2/dist/Leaflet.fullscreen.min.js"></script>
<script>
// ── Data ──────────────────────────────────────────────
const GEOJSON    = {geojson_str};
const COLOR_MAP  = {json.dumps(color_map)};
const OUTLINE_MAP= {json.dumps(outline_map)};
const BASEMAPS   = {basemaps_js};
const VAR_A      = {json.dumps(var_a)};
const VAR_B      = {json.dumps(var_b)};
const CLASS_COUNTS = {json.dumps(class_counts)};
const PALETTE_COLORS = {json.dumps(colors)};
const VECTOR_CLASSES = {json.dumps(VECTOR_CLASSES)};
const CODE_LABELS = {json.dumps({VECTOR_CLASSES[i]: CODE_LABELS[['11','12','13','21','22','23','31','32','33'][i]] for i in range(9)})};

// ── Map init ──────────────────────────────────────────
const map = L.map('map', {{zoomControl: true}});
L.control.scale({{position:'bottomright', metric:true, imperial:false}}).addTo(map);

let currentTile = null;
function switchBasemap(idx) {{
  const bm = BASEMAPS[parseInt(idx)];
  if (currentTile) map.removeLayer(currentTile);
  currentTile = L.tileLayer(bm.url, {{attribution: bm.attr, maxZoom:19}}).addTo(map);
  document.getElementById('bm-select').value = idx;
}}

// Populate basemap selector
const bmSel = document.getElementById('bm-select');
BASEMAPS.forEach((bm,i) => {{
  const opt = document.createElement('option');
  opt.value = i; opt.textContent = bm.name;
  bmSel.appendChild(opt);
}});
switchBasemap({bm_idx});

// Fullscreen
new L.Control.Fullscreen({{position:'topright'}}).addTo(map);

// ── GeoJSON layer ─────────────────────────────────────
let activeLayer = null;
let highlightedClass = null;

function getStyle(feat) {{
  const p = feat.properties;
  return {{
    fillColor:   p._fill   || '#aaaaaa',
    fillOpacity: 0.82,
    color:       p._stroke || '#888888',
    weight:      0.6,
  }};
}}

function highlightStyle(feat) {{
  const p = feat.properties;
  return {{
    fillColor:   p._fill   || '#aaaaaa',
    fillOpacity: 0.95,
    color:       '#111',
    weight:      2,
  }};
}}

const tooltip = L.tooltip({{
  sticky: true, opacity: 1, className: 'bv-tooltip'
}});

const geoLayer = L.geoJSON(GEOJSON, {{
  style: getStyle,
  onEachFeature: (feat, layer) => {{
    const p = feat.properties;
    const fill = p._fill || '#aaa';
    const textColor = isLight(fill) ? '#111' : '#fff';

    // Popup content
    const rows = Object.entries(p)
      .filter(([k]) => !k.startsWith('_'))
      .map(([k,v]) => `<tr><td>${{k}}</td><td>${{v}}</td></tr>`)
      .join('');
    const name = p._label || '';
    const popupHtml = `
      <div class="bv-popup">
        ${{name ? `<div class="region-name">${{name}}
          <span class="cls-badge" style="background:${{fill}};color:${{textColor}}">${{p._cls}}</span>
          </div>` : `<div class="region-name">
          <span class="cls-badge" style="background:${{fill}};color:${{textColor}}">${{p._cls}}</span>
          </div>`}}
        ${{rows ? `<table>${{rows}}</table>` : ''}}
      </div>`;
    layer.bindPopup(popupHtml, {{maxWidth:280}});

    // Tooltip
    layer.on('mouseover', e => {{
      if (!highlightedClass) {{
        layer.setStyle(highlightStyle(feat));
        layer.bringToFront();
      }}
      const tt = name || p._cls;
      tooltip.setContent(`<strong>${{tt}}</strong>`);
      layer.bindTooltip(tooltip).openTooltip(e.latlng);
    }});
    layer.on('mousemove', e => tooltip.setLatLng(e.latlng));
    layer.on('mouseout',  () => {{
      if (!highlightedClass) geoLayer.resetStyle(layer);
      layer.closeTooltip();
    }});
  }}
}}).addTo(map);

if (GEOJSON.features.length > 0) {{
  try {{ map.fitBounds(geoLayer.getBounds(), {{padding:[20,20]}}); }}
  catch(e) {{ map.setView([0,20],3); }}
}}

// ── Legend cell interaction ────────────────────────────
document.querySelectorAll('.lc').forEach(cell => {{
  cell.addEventListener('mouseenter', () => {{
    const cls = cell.dataset.cls;
    highlightClass(cls, false);
  }});
  cell.addEventListener('click', () => {{
    const cls = cell.dataset.cls;
    if (highlightedClass === cls) {{
      resetHighlight();
    }} else {{
      highlightClass(cls, true);
    }}
  }});
  cell.addEventListener('mouseleave', () => {{
    if (!highlightedClass) resetHighlight();
  }});
}});

function highlightClass(cls, lock) {{
  if (lock) highlightedClass = cls;
  geoLayer.eachLayer(layer => {{
    const p = layer.feature.properties;
    if (p._cls === cls) {{
      layer.setStyle(highlightStyle(layer.feature));
      layer.bringToFront();
    }} else {{
      layer.setStyle({{
        fillColor: p._fill || '#aaa',
        fillOpacity: 0.18,
        color: p._stroke || '#888',
        weight: 0.3,
      }});
    }}
  }});
  document.querySelectorAll('.lc').forEach(c => {{
    c.classList.toggle('dimmed', c.dataset.cls !== cls);
    c.classList.toggle('highlighted', c.dataset.cls === cls);
  }});
}}

function resetHighlight() {{
  highlightedClass = null;
  geoLayer.eachLayer(layer => geoLayer.resetStyle(layer));
  document.querySelectorAll('.lc').forEach(c => {{
    c.classList.remove('dimmed','highlighted');
  }});
}}
document.getElementById('reset-btn').addEventListener('click', resetHighlight);

// ── Class distribution chips ───────────────────────────
const cgrid = document.getElementById('class-grid');
VECTOR_CLASSES.forEach((cls, i) => {{
  const c   = COLOR_MAP[cls] || '#ccc';
  const tc  = isLight(c) ? '#111' : '#fff';
  const cnt = CLASS_COUNTS[cls] || 0;
  const chip = document.createElement('div');
  chip.className = 'class-chip';
  chip.style.background = c;
  chip.style.color = tc;
  chip.innerHTML = `<div>${{cls}}</div><div style="font-size:9px;opacity:.8">${{cnt}}</div>`;
  chip.title = CODE_LABELS[cls] || cls;
  chip.addEventListener('click', () => {{
    if (highlightedClass === cls) resetHighlight();
    else highlightClass(cls, true);
  }});
  cgrid.appendChild(chip);
}});

// ── Color key ─────────────────────────────────────────
const ckey = document.getElementById('color-key');
VECTOR_CLASSES.forEach((cls, i) => {{
  const c = COLOR_MAP[cls];
  const el = document.createElement('div');
  el.className = 'ck-item';
  el.innerHTML = `<div class="ck-swatch" style="background:${{c}}"></div><span>${{cls}}</span>`;
  ckey.appendChild(el);
}});

// ── Theme toggle ──────────────────────────────────────
let isDark = {default_dark};
function toggleTheme() {{
  isDark = !isDark;
  const sb  = document.getElementById('sidebar');
  const btn = document.getElementById('theme-btn');
  sb.classList.toggle('dark',  isDark);
  sb.classList.toggle('light', !isDark);
  btn.textContent = isDark ? '☀ Light mode' : '☾ Dark mode';
}}
if (isDark) toggleTheme();

// ── Utility ───────────────────────────────────────────
function isLight(hex) {{
  const h = hex.replace('#','');
  const r=parseInt(h.slice(0,2),16),g=parseInt(h.slice(2,4),16),b=parseInt(h.slice(4,6),16);
  return (r*299+g*587+b*114)/1000 > 155;
}}
</script>
</body>
</html>'''

        with open(out_html, 'w', encoding='utf-8') as f:
            f.write(html)
        feedback.setProgress(100)
        feedback.pushInfo(f'Leaflet map exported: {out_html}')
        return {self.OUTPUT: out_html}
