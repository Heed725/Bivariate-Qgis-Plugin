"""
QGIS Processing Script: Apply Bivariate Color Scheme
Applies a bivariate color scheme to a layer that already has a Bi_Class field.
Supports all 30 built-in palettes or custom 9-color hex input.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, class_codes, palette_colors, transpose_palette


from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsProcessingParameterEnum,
    QgsProcessingParameterBoolean,
    QgsProcessingException,
    QgsCategorizedSymbolRenderer,
    QgsRendererCategory,
    QgsFillSymbol, QgsLineSymbol, QgsMarkerSymbol,
)


PALETTE_NAMES = list(PALETTES.keys()) + ['Custom / Staridas import']


class ApplyBivariateColorsAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    CLASS_FIELD = 'CLASS_FIELD'
    PALETTE_CHOICE = 'PALETTE_CHOICE'
    CUSTOM_COLORS = 'CUSTOM_COLORS'
    GRID_SIZE = 'GRID_SIZE'
    TRANSPOSE = 'TRANSPOSE'
    OUTLINE_COLOR = 'OUTLINE_COLOR'
    OUTLINE_WIDTH = 'OUTLINE_WIDTH'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, 'Input layer with bivariate classes',
            [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.CLASS_FIELD, 'Bivariate class field',
            parentLayerParameterName=self.INPUT,
            defaultValue='Bi_Class'))
        self.addParameter(QgsProcessingParameterEnum(
            self.PALETTE_CHOICE, 'Color palette',
            options=PALETTE_NAMES,
            defaultValue=6))  # DkBlue
        self.addParameter(QgsProcessingParameterEnum(
            self.GRID_SIZE, 'Grid size', options=['3×3', '4×4', '5×5'], defaultValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.CUSTOM_COLORS,
            'Staridas/Custom palette — paste labelled HEX, CSS, or JSON',
            defaultValue='#e8e8e8,#dfb0d6,#be64ac,#ace4e4,#a5add3,#8c62aa,#5ac8c8,#5698b9,#3b4994',
            optional=True, multiLine=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.TRANSPOSE,
            'Transpose axes (swap X ↔ Y)',
            defaultValue=False))
        self.addParameter(QgsProcessingParameterString(
            self.OUTLINE_COLOR, 'Outline color', defaultValue='#808080', optional=True))
        self.addParameter(QgsProcessingParameterString(
            self.OUTLINE_WIDTH, 'Outline width', defaultValue='0.26', optional=True))

    def processAlgorithm(self, parameters, context, feedback):
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        class_field = self.parameterAsString(parameters, self.CLASS_FIELD, context)
        pal_idx = self.parameterAsInt(parameters, self.PALETTE_CHOICE, context)
        custom = self.parameterAsString(parameters, self.CUSTOM_COLORS, context)
        dim = self.parameterAsEnum(parameters, self.GRID_SIZE, context) + 3
        transpose = self.parameterAsBoolean(parameters, self.TRANSPOSE, context)
        outline_color = self.parameterAsString(parameters, self.OUTLINE_COLOR, context)
        outline_width = self.parameterAsString(parameters, self.OUTLINE_WIDTH, context)

        if layer is None:
            raise QgsProcessingException('Invalid input layer')

        # Resolve palette
        pal_name = PALETTE_NAMES[pal_idx]
        try:
            colors = palette_colors(pal_name, dim, custom)
        except ValueError as exc:
            raise QgsProcessingException(str(exc))
        feedback.pushInfo(f'Using palette: {pal_name} ({dim}×{dim})')

        if transpose:
            colors = transpose_palette(colors, dim)
            feedback.pushInfo('Palette axes transposed (X ↔ Y).')

        color_map = dict(zip(class_codes(dim), colors))
        feedback.pushInfo('Color mapping: ' + str(color_map))

        geom_type = layer.geometryType()
        categories = []
        for cls, hex_color in color_map.items():
            if geom_type == 2:
                sym = QgsFillSymbol.createSimple({
                    'color': hex_color, 'outline_color': outline_color,
                    'outline_width': outline_width, 'outline_style': 'solid'})
            elif geom_type == 1:
                sym = QgsLineSymbol.createSimple({'color': hex_color, 'width': outline_width})
            else:
                sym = QgsMarkerSymbol.createSimple({
                    'color': hex_color, 'outline_color': outline_color,
                    'outline_width': outline_width, 'size': '3'})
            categories.append(QgsRendererCategory(cls, sym, cls))

        layer.setRenderer(QgsCategorizedSymbolRenderer(class_field, categories))
        layer.triggerRepaint()
        feedback.pushInfo(f'Style applied to "{layer.name()}" with palette index {pal_idx}')
        return {}

    def name(self):           return 'applybivariatecolors'
    def displayName(self):    return 'Apply Bivariate Color Scheme (Vector)'
    def group(self):          return 'Cartography'
    def groupId(self):        return 'cartography'
    def createInstance(self): return ApplyBivariateColorsAlgorithm()
    def shortHelpString(self):
        names = ', '.join(list(PALETTES.keys()))
        return (
            'Applies a 3×3, 4×4, or 5×5 bivariate color scheme.\n\n'
            f'Available palettes: {names}\n\n'
            'Choose Custom / Staridas import and paste labelled HEX, CSS, or JSON. '
            'The transpose option works for all supported grid sizes.'
        )
