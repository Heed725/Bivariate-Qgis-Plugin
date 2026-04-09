"""
QGIS Processing Script: Bivariate Legend Box Generator (3×3 Grid)
Generates a 3×3 grid of square polygons for a bivariate legend.
Each box has a 'color' attribute that allows styling directly in QGIS
Print Layout via the 'Rule-based' or 'Categorized' renderer.

LAYOUT ICON FEATURE:
  After generating, the layer is added with a categorized renderer.
  In Print Layout > Add Item > Add Map — the legend boxes appear as
  colored squares. You can also use "Add Item > Add Picture" to reference
  the layer's SVG export, or use the layer in a Layout Legend item.

  To interactively recolor boxes in Layout:
  1. Open Layer Properties > Symbology
  2. Use 'Categorized' renderer on 'code' field
  3. Double-click any category color swatch to change it
  4. Refresh the Layout map item to see changes live
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, CODE_LABELS


from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPixmap, QPainter
from qgis.PyQt.QtCore import Qt, QSize
from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterString,
    QgsProcessingParameterBoolean,
    QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsField,
    QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsFields,
    QgsFillSymbol, QgsRendererCategory, QgsCategorizedSymbolRenderer,
    QgsWkbTypes, QgsProcessingException,
    QgsSingleSymbolRenderer, QgsSymbol,
    QgsSimpleFillSymbolLayer,
    QgsLayerDefinition,
    QgsMapLayer,
    QgsProject,
    QgsTextFormat,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
)

PALETTE_NAMES = list(PALETTES.keys()) + ['Custom (enter hex codes below)']
CODES = ['11','12','13','21','22','23','31','32','33']


class BivariateLegendBoxGenerator(QgsProcessingAlgorithm):
    PALETTE_CHOICE  = 'PALETTE_CHOICE'
    CUSTOM_COLORS   = 'CUSTOM_COLORS'
    BOX_SIZE        = 'BOX_SIZE'
    SPACING         = 'SPACING'
    ADD_LABELS      = 'ADD_LABELS'
    OUTPUT          = 'OUTPUT'

    def tr(self, t):
        return QCoreApplication.translate('BivariateLegendBoxGenerator', t)


    def flags(self):
        # Hidden from Processing Toolbox — accessible only via Print Layout
        return super().flags() | QgsProcessingAlgorithm.FlagHideFromToolbox
    def createInstance(self):
        return BivariateLegendBoxGenerator()

    def name(self):
        return 'bivariate_legend_box_generator'

    def displayName(self):
        return self.tr('Bivariate Legend Box Generator (3×3)')

    def group(self):
        return self.tr('Cartography')

    def groupId(self):
        return 'cartography'

    def shortHelpString(self):
        return self.tr(
            'Generates a 3×3 grid of square polygons as a shapefile/GeoPackage for a bivariate legend.\n\n'
            'LAYOUT ICON SUPPORT:\n'
            '  The output layer uses a Categorized renderer on the "code" field.\n'
            '  Each class (11-33) has its own color swatch — you can double-click\n'
            '  any category in Layer Properties > Symbology to recolor it interactively.\n\n'
            '  In Print Layout:\n'
            '  • Add Map item → the 9 colored squares appear as your legend\n'
            '  • Add Legend item → each square class appears as a colored icon\n'
            '  • Right-click a Legend item entry to change its icon color\n\n'
            'RECOLORING:\n'
            '  Layer Properties > Symbology > Categorized > double-click any color swatch\n\n'
            'Custom Colors order: 11, 12, 13, 21, 22, 23, 31, 32, 33'
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterEnum(
            self.PALETTE_CHOICE, self.tr('Color palette'),
            options=PALETTE_NAMES, defaultValue=6))

        self.addParameter(QgsProcessingParameterString(
            self.CUSTOM_COLORS,
            self.tr('Custom colors — 9 hex codes comma-separated (order: 11–33)'),
            defaultValue='#e8e8e8,#dfb0d6,#be64ac,#ace4e4,#a5add3,#8c62aa,#5ac8c8,#5698b9,#3b4994',
            optional=True, multiLine=False))

        self.addParameter(QgsProcessingParameterNumber(
            self.BOX_SIZE, self.tr('Box size (map units)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.0, minValue=0.1))

        self.addParameter(QgsProcessingParameterNumber(
            self.SPACING, self.tr('Spacing between boxes (map units)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.05, minValue=0.0))

        self.addParameter(QgsProcessingParameterBoolean(
            self.ADD_LABELS,
            self.tr('Add class code labels (e.g. "11", "33") to boxes?'),
            defaultValue=False))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT, self.tr('Output legend boxes'),
            type=QgsProcessing.TypeVectorPolygon))

    def processAlgorithm(self, parameters, context, feedback):
        pal_idx    = self.parameterAsInt(parameters, self.PALETTE_CHOICE, context)
        custom     = self.parameterAsString(parameters, self.CUSTOM_COLORS, context)
        box_size   = self.parameterAsDouble(parameters, self.BOX_SIZE, context)
        spacing    = self.parameterAsDouble(parameters, self.SPACING, context)
        add_labels = self.parameterAsBoolean(parameters, self.ADD_LABELS, context)
        out_path   = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        # --- Resolve palette ---
        if pal_idx == len(PALETTE_NAMES) - 1:
            colors = [c.strip() for c in custom.split(',')]
            if len(colors) != 9:
                raise QgsProcessingException(f'Expected 9 hex codes, got {len(colors)}')
            pal_name = 'Custom'
        else:
            pal_name = PALETTE_NAMES[pal_idx]
            colors = PALETTES[pal_name]
            feedback.pushInfo(f'Palette: {pal_name}')

        palette = {CODES[i]: colors[i] for i in range(9)}

        # --- Fields ---
        fields = QgsFields()
        fields.append(QgsField('code',    QVariant.String))
        fields.append(QgsField('label',   QVariant.String))
        fields.append(QgsField('color',   QVariant.String))
        fields.append(QgsField('a_class', QVariant.String))
        fields.append(QgsField('b_class', QVariant.String))
        fields.append(QgsField('row',     QVariant.Int))
        fields.append(QgsField('col',     QVariant.Int))

        crs    = QgsCoordinateReferenceSystem('EPSG:4326')
        driver = 'GPKG' if out_path.lower().endswith('.gpkg') else 'ESRI Shapefile'
        writer = QgsVectorFileWriter(out_path, 'UTF-8', fields,
                                     QgsWkbTypes.Polygon, crs, driver)
        if writer.hasError() != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f'Writer error: {writer.errorMessage()}')

        step    = box_size + spacing
        a_lvl   = ['Low', 'Mid', 'High']
        b_lvl   = ['Low', 'Mid', 'High']

        # Row 0 = bottom (Low B), Row 2 = top (High B)
        for row in range(3):
            for col in range(3):
                code = f'{col + 1}{row + 1}'
                hex_color = palette[code]
                xmin = col * step
                ymin = row * step
                xmax = xmin + box_size
                ymax = ymin + box_size

                pts = [
                    QgsPointXY(xmin, ymin), QgsPointXY(xmax, ymin),
                    QgsPointXY(xmax, ymax), QgsPointXY(xmin, ymax),
                    QgsPointXY(xmin, ymin)
                ]
                feat = QgsFeature(fields)
                feat.setGeometry(QgsGeometry.fromPolygonXY([pts]))
                feat.setAttribute('code',    code)
                feat.setAttribute('label',   CODE_LABELS[code])
                feat.setAttribute('color',   hex_color)
                feat.setAttribute('a_class', a_lvl[col])
                feat.setAttribute('b_class', b_lvl[row])
                feat.setAttribute('row',     row)
                feat.setAttribute('col',     col)
                writer.addFeature(feat)

        del writer
        feedback.pushInfo(f'Written {9} boxes to: {out_path}')

        # --- Load, style, and register the layer ---
        try:
            layer = QgsVectorLayer(out_path, f'Bivariate Legend [{pal_name}]', 'ogr')
            if not layer.isValid():
                feedback.pushWarning('Layer failed to load for styling.')
                return {self.OUTPUT: out_path}

            # Build categorized renderer — each code gets its own colored square icon
            categories = []
            for code, hex_color in palette.items():
                sym = QgsFillSymbol.createSimple({
                    'color':         hex_color,
                    'outline_color': '#4a4a4a',
                    'outline_width': '0.15',
                    'outline_style': 'solid',
                })
                label_text = f'{code} · {CODE_LABELS[code]}'
                cat = QgsRendererCategory(code, sym, label_text)
                categories.append(cat)

            renderer = QgsCategorizedSymbolRenderer('code', categories)
            layer.setRenderer(renderer)

            # Optional: add code labels
            if add_labels:
                tf = QgsTextFormat()
                tf.setFont(QFont('Arial', 7))
                tf.setSize(7)
                tf.setColor(QColor('#333333'))

                lbl = QgsPalLayerSettings()
                lbl.fieldName    = 'code'
                lbl.enabled      = True
                lbl.placement    = QgsPalLayerSettings.OverPoint
                lbl.setFormat(tf)
                layer.setLabeling(QgsVectorLayerSimpleLabeling(lbl))
                layer.setLabelsEnabled(True)

            QgsProject.instance().addMapLayer(layer)
            feedback.pushInfo(
                f'Layer "{layer.name()}" added to project.\n'
                'TIP: In Print Layout → Add Legend — each class appears as a colored square icon.\n'
                'TIP: Layer Properties > Symbology — double-click any color swatch to recolor interactively.'
            )

        except Exception as e:
            feedback.pushWarning(f'Auto-style skipped: {e}')

        return {self.OUTPUT: out_path}
