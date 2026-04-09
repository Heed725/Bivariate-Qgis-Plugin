"""
QGIS Processing Script: Bivariate Legend Diamond Generator (3×3 Rotated Grid)
Generates a 3×3 grid of diamond (rhombus) polygons in a 45°-rotated layout.
Variable A increases along the bottom-right diagonal.
Variable B increases along the bottom-left diagonal.

LAYOUT ICON FEATURE:
  Same as the Box Generator — categorized renderer on 'code' field.
  Each diamond class appears as a colored diamond icon in Print Layout Legend.
  Double-click any color swatch in Layer Properties > Symbology to recolor.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, CODE_LABELS


from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.PyQt.QtGui import QColor, QFont
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
    QgsProject,
    QgsTextFormat,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
)
import math, sys, os

PALETTE_NAMES = list(PALETTES.keys()) + ['Custom (enter hex codes below)']
CODES = ['11','12','13','21','22','23','31','32','33']


class BivariateLegendDiamondGenerator(QgsProcessingAlgorithm):
    PALETTE_CHOICE = 'PALETTE_CHOICE'
    CUSTOM_COLORS  = 'CUSTOM_COLORS'
    DIAMOND_SIZE   = 'DIAMOND_SIZE'
    SPACING        = 'SPACING'
    ADD_LABELS     = 'ADD_LABELS'
    OUTPUT         = 'OUTPUT'

    def tr(self, t):
        return QCoreApplication.translate('BivariateLegendDiamondGenerator', t)


    def flags(self):
        # Hidden from Processing Toolbox — accessible only via Print Layout
        return super().flags() | QgsProcessingAlgorithm.FlagHideFromToolbox
    def createInstance(self):
        return BivariateLegendDiamondGenerator()

    def name(self):        return 'bivariate_legend_diamond_generator'
    def displayName(self): return self.tr('Bivariate Legend Diamond Generator (3×3)')
    def group(self):       return self.tr('Cartography')
    def groupId(self):     return 'cartography'

    def shortHelpString(self):
        return self.tr(
            'Generates a 3×3 grid of diamond (rhombus) polygons in a 45°-rotated layout.\n\n'
            'Variable A increases along the bottom-right diagonal axis.\n'
            'Variable B increases along the bottom-left diagonal axis.\n\n'
            'LAYOUT ICON SUPPORT:\n'
            '  Uses a Categorized renderer on "code" — each diamond appears\n'
            '  as a colored icon in Print Layout Legend.\n'
            '  Double-click any color swatch in Symbology to recolor interactively.\n\n'
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
            self.DIAMOND_SIZE, self.tr('Diamond side length (map units)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=1.0, minValue=0.1))

        self.addParameter(QgsProcessingParameterNumber(
            self.SPACING, self.tr('Gap between diamonds (map units)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.08, minValue=0.0))

        self.addParameter(QgsProcessingParameterBoolean(
            self.ADD_LABELS,
            self.tr('Add class code labels to diamonds?'),
            defaultValue=False))

        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT, self.tr('Output legend diamonds'),
            type=QgsProcessing.TypeVectorPolygon))

    # ------------------------------------------------------------------ helpers
    def _diamond(self, cx, cy, size):
        """Return a diamond (rhombus) geometry centred at (cx, cy)."""
        h = (size * math.sqrt(2)) / 2.0
        pts = [
            QgsPointXY(cx,     cy + h),   # top
            QgsPointXY(cx + h, cy),       # right
            QgsPointXY(cx,     cy - h),   # bottom
            QgsPointXY(cx - h, cy),       # left
            QgsPointXY(cx,     cy + h),   # close
        ]
        return QgsGeometry.fromPolygonXY([pts])

    def _pos(self, row, col, size, spacing):
        """
        Rotated-grid position.
        col (A axis) moves right-up; row (B axis) moves left-up.
        """
        step = size + spacing
        angle = math.radians(45)
        x =  col * step * math.cos(angle) - row * step * math.sin(angle)
        y =  col * step * math.sin(angle) + row * step * math.cos(angle)
        return x, y

    # ------------------------------------------------------------------ main
    def processAlgorithm(self, parameters, context, feedback):
        pal_idx    = self.parameterAsInt(parameters, self.PALETTE_CHOICE, context)
        custom     = self.parameterAsString(parameters, self.CUSTOM_COLORS, context)
        dsize      = self.parameterAsDouble(parameters, self.DIAMOND_SIZE, context)
        spacing    = self.parameterAsDouble(parameters, self.SPACING, context)
        add_labels = self.parameterAsBoolean(parameters, self.ADD_LABELS, context)
        out_path   = self.parameterAsOutputLayer(parameters, self.OUTPUT, context)

        if pal_idx == len(PALETTE_NAMES) - 1:
            colors = [c.strip() for c in custom.split(',')]
            if len(colors) != 9:
                raise QgsProcessingException(f'Expected 9 hex codes, got {len(colors)}')
            pal_name = 'Custom'
        else:
            pal_name = PALETTE_NAMES[pal_idx]
            colors   = PALETTES[pal_name]
            feedback.pushInfo(f'Palette: {pal_name}')

        palette = {CODES[i]: colors[i] for i in range(9)}

        fields = QgsFields()
        for fname, ftype in [
            ('code',    QVariant.String),
            ('label',   QVariant.String),
            ('color',   QVariant.String),
            ('a_class', QVariant.String),
            ('b_class', QVariant.String),
            ('row',     QVariant.Int),
            ('col',     QVariant.Int),
        ]:
            fields.append(QgsField(fname, ftype))

        crs    = QgsCoordinateReferenceSystem('EPSG:4326')
        driver = 'GPKG' if out_path.lower().endswith('.gpkg') else 'ESRI Shapefile'
        writer = QgsVectorFileWriter(out_path, 'UTF-8', fields,
                                     QgsWkbTypes.Polygon, crs, driver)
        if writer.hasError() != QgsVectorFileWriter.NoError:
            raise QgsProcessingException(f'Writer error: {writer.errorMessage()}')

        a_lvl = ['Low', 'Mid', 'High']
        b_lvl = ['Low', 'Mid', 'High']

        for row in range(3):
            for col in range(3):
                code      = f'{col + 1}{row + 1}'
                hex_color = palette[code]
                cx, cy    = self._pos(row, col, dsize, spacing)
                geom      = self._diamond(cx, cy, dsize)

                feat = QgsFeature(fields)
                feat.setGeometry(geom)
                feat.setAttribute('code',    code)
                feat.setAttribute('label',   CODE_LABELS[code])
                feat.setAttribute('color',   hex_color)
                feat.setAttribute('a_class', a_lvl[col])
                feat.setAttribute('b_class', b_lvl[row])
                feat.setAttribute('row',     row)
                feat.setAttribute('col',     col)
                writer.addFeature(feat)

        del writer
        feedback.pushInfo(f'Written 9 diamond shapes to: {out_path}')

        # --- Auto-load & style ---
        try:
            layer = QgsVectorLayer(out_path, f'Bivariate Legend Diamonds [{pal_name}]', 'ogr')
            if not layer.isValid():
                return {self.OUTPUT: out_path}

            categories = []
            for code, hex_color in palette.items():
                sym = QgsFillSymbol.createSimple({
                    'color':         hex_color,
                    'outline_color': '#4a4a4a',
                    'outline_width': '0.15',
                    'outline_style': 'solid',
                })
                cat = QgsRendererCategory(code, sym, f'{code} · {CODE_LABELS[code]}')
                categories.append(cat)

            layer.setRenderer(QgsCategorizedSymbolRenderer('code', categories))

            if add_labels:
                tf = QgsTextFormat()
                tf.setFont(QFont('Arial', 7))
                tf.setSize(7)
                tf.setColor(QColor('#333333'))
                lbl = QgsPalLayerSettings()
                lbl.fieldName = 'code'
                lbl.enabled   = True
                lbl.placement = QgsPalLayerSettings.OverPoint
                lbl.setFormat(tf)
                layer.setLabeling(QgsVectorLayerSimpleLabeling(lbl))
                layer.setLabelsEnabled(True)

            QgsProject.instance().addMapLayer(layer)
            feedback.pushInfo(
                f'Layer "{layer.name()}" added to project.\n'
                'TIP: Print Layout → Add Legend → diamond icons appear per class.\n'
                'TIP: Layer Properties > Symbology → double-click color to recolor.'
            )
        except Exception as e:
            feedback.pushWarning(f'Auto-style skipped: {e}')

        return {self.OUTPUT: out_path}
