"""
QGIS Processing Script: Bivariate Style Generator
Creates a QML style file for bivariate rasters (values 11-33).
Supports all 30 built-in palettes or custom 9-color hex input.
"""
import os as _os, sys as _sys, json as _json
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, class_codes, code_label, palette_colors, transpose_palette


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
)
import processing, sys, os

PALETTE_NAMES = list(PALETTES.keys()) + ['Custom / Staridas import']


def write_qml(path, colors, dim):
    codes = class_codes(dim, vector=False)
    entries = '\n'.join(
        f'        <paletteEntry alpha="255" label="{code_label(codes[i], dim)}" '
        f'color="{colors[i]}" value="{codes[i]}"/>'
        for i in range(dim * dim))
    xml = (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        '<qgis version="3.22.0" styleCategories="LayerConfiguration|Symbology" '
        'maxScale="0" minScale="1e+08" hasScaleBasedVisibilityFlag="0">\n'
        '  <pipe>\n'
        '    <rasterrenderer opacity="1" band="1" type="paletted" alphaBand="-1">\n'
        '      <colorPalette>\n'
        f'{entries}\n'
        '      </colorPalette>\n'
        '    </rasterrenderer>\n'
        '  </pipe>\n'
        '</qgis>\n')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(xml)
    return path


class BivariateStyleGenerator(QgsProcessingAlgorithm):
    INPUT_RASTER  = 'INPUT_RASTER'
    PALETTE_CHOICE = 'PALETTE_CHOICE'
    CUSTOM_COLORS  = 'CUSTOM_COLORS'
    GRID_SIZE = 'GRID_SIZE'
    TRANSPOSE      = 'TRANSPOSE'
    AUTO_APPLY     = 'AUTO_APPLY'
    OUT_QML        = 'OUT_QML'

    def tr(self, t): return QCoreApplication.translate('BivariateStyleGenerator', t)
    def createInstance(self): return BivariateStyleGenerator()
    def name(self):        return 'bivariate_style_generator'
    def displayName(self): return self.tr('Bivariate Style Generator (Raster)')
    def group(self):       return self.tr('Cartography')
    def groupId(self):     return 'cartography'
    def shortHelpString(self):
        return self.tr(
            'Creates a QML color style file for bivariate rasters (values 11–33).\n\n'
            'Choose from 30 built-in palettes or supply custom hex codes.\n'
            'Can auto-apply the style to your input raster layer.')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.INPUT_RASTER, self.tr('Input bivariate raster (values 11-33)'), optional=True))
        self.addParameter(QgsProcessingParameterEnum(
            self.PALETTE_CHOICE, self.tr('Color palette'),
            options=PALETTE_NAMES, defaultValue=6))
        self.addParameter(QgsProcessingParameterEnum(
            self.GRID_SIZE, self.tr('Grid size'), options=['3×3', '4×4', '5×5'], defaultValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.CUSTOM_COLORS,
            self.tr('Staridas/Custom palette — paste labelled HEX, CSS, or JSON'),
            defaultValue='#e8e8e8,#dfb0d6,#be64ac,#ace4e4,#a5add3,#8c62aa,#5ac8c8,#5698b9,#3b4994',
            optional=True, multiLine=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.TRANSPOSE,
            self.tr('Transpose axes (swap X ↔ Y)'),
            defaultValue=False))
        self.addParameter(QgsProcessingParameterBoolean(
            self.AUTO_APPLY, self.tr('Auto-apply style to input raster?'), defaultValue=True))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUT_QML, self.tr('Output QML style file'), 'QML files (*.qml)'))

    def processAlgorithm(self, parameters, context, feedback):
        raster     = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        pal_idx    = self.parameterAsInt(parameters, self.PALETTE_CHOICE, context)
        custom     = self.parameterAsString(parameters, self.CUSTOM_COLORS, context)
        dim        = self.parameterAsEnum(parameters, self.GRID_SIZE, context) + 3
        transpose  = self.parameterAsBoolean(parameters, self.TRANSPOSE, context)
        auto_apply = self.parameterAsBoolean(parameters, self.AUTO_APPLY, context)
        out_qml    = self.parameterAsFileOutput(parameters, self.OUT_QML, context)

        if auto_apply and (not raster or not raster.isValid()):
            raise QgsProcessingException('Input raster required when auto-apply is enabled.')

        pal_name = PALETTE_NAMES[pal_idx]
        try:
            colors = palette_colors(pal_name, dim, custom)
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        feedback.pushInfo(f'Palette: {pal_name} ({dim}×{dim})')

        if transpose:
            colors = transpose_palette(colors, dim)
            feedback.pushInfo('Palette axes transposed (X ↔ Y).')

        qml = write_qml(out_qml, colors, dim)
        feedback.pushInfo(f'QML written: {qml}')

        if auto_apply and raster:
            try:
                processing.run('qgis:setstyleforrasterlayer',
                               {'INPUT': raster, 'STYLE': qml},
                               context=context, feedback=feedback)
                # Persist style metadata for Print Layout auto-detection.
                raster.setCustomProperty('bivariate_plugin/dimension', dim)
                raster.setCustomProperty('bivariate_plugin/colors', _json.dumps(colors))
                raster.setCustomProperty('bivariate_plugin/kind', 'raster')
                feedback.pushInfo('Style applied to raster and linked for Print Layout sensing.')
            except Exception as e:
                feedback.pushWarning(f'Auto-apply failed: {e}')

        return {self.OUT_QML: qml}
