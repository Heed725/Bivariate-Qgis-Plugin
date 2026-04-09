"""
QGIS Processing Script: Bivariate Style Generator
Creates a QML style file for bivariate rasters (values 11-33).
Supports all 30 built-in palettes or custom 9-color hex input.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, CODE_LABELS


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

PALETTE_NAMES = list(PALETTES.keys()) + ['Custom (enter hex codes below)']
CODES = ['11','12','13','21','22','23','31','32','33']


def write_qml(path, colors):
    entries = '\n'.join(
        f'        <paletteEntry alpha="255" label="{CODE_LABELS[CODES[i]]}" '
        f'color="{colors[i]}" value="{CODES[i]}"/>'
        for i in range(9))
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
    AUTO_APPLY     = 'AUTO_APPLY'
    OUT_QML        = 'OUT_QML'

    def tr(self, t): return QCoreApplication.translate('BivariateStyleGenerator', t)
    def createInstance(self): return BivariateStyleGenerator()
    def name(self):        return 'bivariate_style_generator'
    def displayName(self): return self.tr('Bivariate Style Generator')
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
        self.addParameter(QgsProcessingParameterString(
            self.CUSTOM_COLORS,
            self.tr('Custom colors — 9 hex codes (order: 11–33)'),
            defaultValue='#e8e8e8,#dfb0d6,#be64ac,#ace4e4,#a5add3,#8c62aa,#5ac8c8,#5698b9,#3b4994',
            optional=True, multiLine=False))
        self.addParameter(QgsProcessingParameterBoolean(
            self.AUTO_APPLY, self.tr('Auto-apply style to input raster?'), defaultValue=True))
        self.addParameter(QgsProcessingParameterFileDestination(
            self.OUT_QML, self.tr('Output QML style file'), 'QML files (*.qml)'))

    def processAlgorithm(self, parameters, context, feedback):
        raster     = self.parameterAsRasterLayer(parameters, self.INPUT_RASTER, context)
        pal_idx    = self.parameterAsInt(parameters, self.PALETTE_CHOICE, context)
        custom     = self.parameterAsString(parameters, self.CUSTOM_COLORS, context)
        auto_apply = self.parameterAsBoolean(parameters, self.AUTO_APPLY, context)
        out_qml    = self.parameterAsFileOutput(parameters, self.OUT_QML, context)

        if auto_apply and (not raster or not raster.isValid()):
            raise QgsProcessingException('Input raster required when auto-apply is enabled.')

        if pal_idx == len(PALETTE_NAMES) - 1:
            colors = [c.strip() for c in custom.split(',')]
            if len(colors) != 9:
                raise QgsProcessingException(f'Need 9 hex codes, got {len(colors)}')
        else:
            pal_name = PALETTE_NAMES[pal_idx]
            colors = PALETTES[pal_name]
            feedback.pushInfo(f'Palette: {pal_name}')

        qml = write_qml(out_qml, colors)
        feedback.pushInfo(f'QML written: {qml}')

        if auto_apply and raster:
            try:
                processing.run('qgis:setstyleforrasterlayer',
                               {'INPUT': raster, 'STYLE': qml},
                               context=context, feedback=feedback)
                feedback.pushInfo('Style applied to raster.')
            except Exception as e:
                feedback.pushWarning(f'Auto-apply failed: {e}')

        return {self.OUT_QML: qml}
