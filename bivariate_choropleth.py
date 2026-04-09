"""
QGIS Processing Script: Bivariate Choropleth Map Generator
Creates bivariate choropleth classification based on two numeric fields.
Methodology: Joshua Stevens (https://www.joshuastevens.net/cartography/make-a-bivariate-choropleth-map/)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, CODE_LABELS


from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingException,
    QgsField, QgsFeature, QgsFeatureSink,
)
from qgis.PyQt.QtCore import QVariant


class BivariateChoroplethAlgorithm(QgsProcessingAlgorithm):
    INPUT = 'INPUT'
    VAR1_FIELD = 'VAR1_FIELD'
    VAR2_FIELD = 'VAR2_FIELD'
    CLASSIFICATION_METHOD = 'CLASSIFICATION_METHOD'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, 'Input layer', [QgsProcessing.TypeVectorPolygon]))
        self.addParameter(QgsProcessingParameterField(
            self.VAR1_FIELD, 'Variable 1 (vertical axis 1-3)',
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterField(
            self.VAR2_FIELD, 'Variable 2 (horizontal axis A-C)',
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric))
        self.addParameter(QgsProcessingParameterEnum(
            self.CLASSIFICATION_METHOD, 'Classification method',
            options=['Quantile (Equal Count)', 'Natural Breaks (Jenks)', 'Equal Interval'],
            defaultValue=0))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 'Output layer with bivariate classes'))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        var1_field = self.parameterAsString(parameters, self.VAR1_FIELD, context)
        var2_field = self.parameterAsString(parameters, self.VAR2_FIELD, context)
        method = self.parameterAsEnum(parameters, self.CLASSIFICATION_METHOD, context)

        if source is None:
            raise QgsProcessingException('Invalid input layer')

        var1_values, var2_values = [], []
        for feature in source.getFeatures():
            for key, lst in [(var1_field, var1_values), (var2_field, var2_values)]:
                val = feature[key]
                if val is not None:
                    try:
                        lst.append(float(val))
                    except (ValueError, TypeError):
                        pass

        if not var1_values or not var2_values:
            raise QgsProcessingException('No valid values found')

        var1_breaks = self._breaks(var1_values, method)
        var2_breaks = self._breaks(var2_values, method)

        feedback.pushInfo(f'Variable 1 breaks: {var1_breaks}')
        feedback.pushInfo(f'Variable 2 breaks: {var2_breaks}')

        fields = source.fields()
        fields.append(QgsField('Var1_Class', QVariant.Int))
        fields.append(QgsField('Var2_Class', QVariant.String))
        fields.append(QgsField('Bi_Class', QVariant.String))

        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            fields, source.wkbType(), source.sourceCrs())

        if sink is None:
            raise QgsProcessingException('Could not create output layer')

        total = source.featureCount()
        for current, feature in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            v1 = float(feature[var1_field]) if feature[var1_field] is not None else float('-inf')
            v2 = float(feature[var2_field]) if feature[var2_field] is not None else float('-inf')

            c1 = 3 if v1 > var1_breaks[1] else (2 if v1 > var1_breaks[0] else 1)
            c2 = 'C' if v2 > var2_breaks[1] else ('B' if v2 > var2_breaks[0] else 'A')

            out = QgsFeature(fields)
            out.setGeometry(feature.geometry())
            for f in source.fields():
                out.setAttribute(f.name(), feature[f.name()])
            out.setAttribute('Var1_Class', c1)
            out.setAttribute('Var2_Class', c2)
            out.setAttribute('Bi_Class', f'{c2}{c1}')
            sink.addFeature(out, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(current * 100 / total))

        return {self.OUTPUT: dest_id}

    def _breaks(self, values, method):
        s = sorted(values)
        n = len(s)
        if method == 0:  # Quantile
            return [s[n // 3], s[(2 * n) // 3]]
        elif method == 1:  # Jenks approx
            return [s[int(n * 0.33)], s[int(n * 0.67)]]
        else:  # Equal interval
            mn, mx = min(values), max(values)
            iv = (mx - mn) / 3
            return [mn + iv, mn + 2 * iv]

    def name(self):          return 'bivariatechoropleth'
    def displayName(self):   return 'Bivariate Choropleth Classification'
    def group(self):         return 'Cartography'
    def groupId(self):       return 'cartography'
    def createInstance(self):return BivariateChoroplethAlgorithm()
    def shortHelpString(self):
        return (
            'Classifies two numeric fields into a 3×3 bivariate scheme (A1–C3).\n\n'
            'Output adds: Var1_Class (1-3), Var2_Class (A-C), Bi_Class (e.g. B2).\n'
            'Use Bi_Class with the Apply Bivariate Color Scheme tool to style the layer.'
        )
