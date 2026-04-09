import os, sys
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from bivariate_choropleth    import BivariateChoroplethAlgorithm
from apply_bivariate_colors  import ApplyBivariateColorsAlgorithm
from bivariate_raster_generator import BivariateRasterGenerator
from bivariate_style_generator  import BivariateStyleGenerator
from bivariate_export_leaflet   import BivariateLeafletExporter
# Legend box/diamond generators are NOT registered here —
# they are only available as Print Layout items.


class BivariateProvider(QgsProcessingProvider):

    def loadAlgorithms(self):
        for cls in [
            BivariateChoroplethAlgorithm,
            ApplyBivariateColorsAlgorithm,
            BivariateRasterGenerator,
            BivariateStyleGenerator,
            BivariateLeafletExporter,
        ]:
            self.addAlgorithm(cls())

    def id(self):       return 'bivariate_qgis_plugin'
    def name(self):     return 'Bivariate QGIS Plugin'
    def longName(self): return 'Bivariate QGIS Plugin — Ultimate Palette Studio'

    def icon(self):
        ico = os.path.join(os.path.dirname(__file__), 'icon.png')
        return QIcon(ico) if os.path.exists(ico) else super().icon()
