## Bivariate Raster Generator (Quantile-based Classification)
## QGIS 3.40 compatible version
##
## Axis convention used everywhere in the plugin:
##   Variable 1 / Raster A = Y axis (vertical)
##   Variable 2 / Raster B = X axis (horizontal)
## Combined raster code = X class first, Y class second.
## Example: 13 = low Variable 2 / X + high Variable 1 / Y.

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingParameterRasterLayer,
    QgsProcessingParameterBoolean, QgsProcessingParameterCrs,
    QgsProcessingParameterNumber, QgsProcessingParameterRasterDestination,
    QgsProcessingParameterEnum, QgsRasterLayer, QgsProcessingException, QgsProject
)
import processing
from osgeo import gdal
import numpy as np
import os
import tempfile

GDAL_RTYPE_FLOAT32 = 5
GDAL_WARP_DTYPE_FLOAT32 = 6


def _calc_gdal(expr, layer_a, layer_b, out_path, rtype=GDAL_RTYPE_FLOAT32):
    params = {
        'INPUT_A': layer_a, 'BAND_A': 1,
        'INPUT_B': layer_b, 'BAND_B': 1,
        'FORMULA': expr,
        'NO_DATA': None,
        'RTYPE': rtype,
        'OPTIONS': '',
        'EXTRA': '',
        'OUTPUT': out_path
    }
    return processing.run('gdal:rastercalculator', params)


def _calc_qgis(expr, layers, out_path):
    from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

    entries = []
    layer_dict = {}
    for idx, layer_path in enumerate(layers):
        ref_name = chr(65 + idx)
        if isinstance(layer_path, str):
            layer = QgsRasterLayer(layer_path, f'layer_{ref_name}')
        else:
            layer = layer_path

        if not layer.isValid():
            raise QgsProcessingException(f'Invalid layer: {layer_path}')

        entry = QgsRasterCalculatorEntry()
        entry.ref = f'{ref_name}@1'
        entry.raster = layer
        entry.bandNumber = 1
        entries.append(entry)
        layer_dict[ref_name] = layer

    ref_layer = layer_dict['A']
    calc = QgsRasterCalculator(
        expr,
        out_path,
        'GTiff',
        ref_layer.extent(),
        ref_layer.crs(),
        ref_layer.width(),
        ref_layer.height(),
        entries,
        QgsProject.instance().transformContext()
    )

    result = calc.processCalculation()
    if result != QgsRasterCalculator.Success:
        err = ''
        try:
            err = calc.lastError()
        except Exception:
            pass
        raise QgsProcessingException(
            f'Raster calculation failed (code {result}). {err}'
        )

    return {'OUTPUT': out_path}


def _runcalc_dual(qgis_expr, gdal_expr, layers, out_path, feedback):
    layer_a = layers[0]
    layer_b = layers[1] if len(layers) > 1 else layers[0]

    try:
        feedback.pushInfo(f'GDAL calc: {gdal_expr}')
        return _calc_gdal(gdal_expr, layer_a, layer_b, out_path)
    except Exception as e_gdal:
        feedback.pushWarning(f'GDAL calculator failed: {e_gdal}')
        try:
            feedback.pushInfo(f'Falling back to QGIS calc: {qgis_expr}')
            return _calc_qgis(qgis_expr, layers, out_path)
        except Exception as e_qgis:
            raise QgsProcessingException(
                'Raster calculator failed in both GDAL and QGIS.\n'
                f'GDAL error: {e_gdal}\nQGIS error: {e_qgis}'
            )


class BivariateRasterGenerator(QgsProcessingAlgorithm):
    RASTER_A, RASTER_B = 'RASTER_A', 'RASTER_B'
    TARGET_CRS, DO_REPROJECT_ALIGN = 'TARGET_CRS', 'DO_REPROJECT_ALIGN'
    APPLY_DIVISOR_B, DIVISOR_B = 'APPLY_DIVISOR_B', 'DIVISOR_B'
    GRID_SIZE = 'GRID_SIZE'
    OUT_A_CLASS, OUT_B_CLASS, OUT_BIVAR = 'OUT_A_CLASS', 'OUT_B_CLASS', 'OUT_BIVAR'

    def tr(self, text):
        return QCoreApplication.translate('BivariateRasterGenerator', text)

    def createInstance(self):
        return BivariateRasterGenerator()

    def name(self):
        return 'bivariate_raster_generator'

    def displayName(self):
        return self.tr('Bivariate Raster Generator (Raster)')

    def group(self):
        return self.tr('Raster - Bivariate')

    def groupId(self):
        return 'raster_bivariate'

    def shortHelpString(self):
        return self.tr(
            'Generates 3, 4, or 5 quantile classes for two rasters and combines '
            'them into bivariate codes.\n\n'
            'Axis convention:\n'
            '- Raster A = Variable 1 = Y axis / vertical\n'
            '- Raster B = Variable 2 = X axis / horizontal\n'
            '- Combined code stores X first, Y second, matching the Print Layout legend.\n\n'
            'Example: Raster A = rainfall and Raster B = temperature gives rainfall '
            'on Y and temperature on X.\n\n'
            'This tool performs raster processing only. Use the "Bivariate Style '
            'Generator" tool to create and apply colors to the output.'
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.RASTER_A,
            self.tr('Raster A — Variable 1 / Y axis (e.g. Rainfall)')
        ))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.RASTER_B,
            self.tr('Raster B — Variable 2 / X axis (e.g. Temperature)')
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.GRID_SIZE,
            self.tr('Grid size'),
            options=['3×3', '4×4', '5×5'],
            defaultValue=0
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.DO_REPROJECT_ALIGN,
            self.tr('Reproject & align to Raster A grid?'),
            defaultValue=True
        ))

        self.addParameter(QgsProcessingParameterCrs(
            self.TARGET_CRS,
            self.tr('Target CRS (optional, e.g. EPSG:21037)'),
            optional=True
        ))

        self.addParameter(QgsProcessingParameterBoolean(
            self.APPLY_DIVISOR_B,
            self.tr('Divide Raster B by factor before processing?'),
            defaultValue=False
        ))
        self.addParameter(QgsProcessingParameterNumber(
            self.DIVISOR_B,
            self.tr('Division factor for Raster B (e.g. 30)'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=30.0,
            minValue=1e-6
        ))

        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUT_A_CLASS,
            self.tr('Output: Raster A / Variable 1 class (Y)')
        ))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUT_B_CLASS,
            self.tr('Output: Raster B / Variable 2 class (X)')
        ))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUT_BIVAR,
            self.tr('Output: Bivariate code (X first, Y second)')
        ))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            raster_a = self.parameterAsRasterLayer(parameters, self.RASTER_A, context)
            raster_b = self.parameterAsRasterLayer(parameters, self.RASTER_B, context)

            if not raster_a or not raster_a.isValid():
                raise QgsProcessingException('Raster A is invalid')
            if not raster_b or not raster_b.isValid():
                raise QgsProcessingException('Raster B is invalid')

            do_align = self.parameterAsBoolean(
                parameters, self.DO_REPROJECT_ALIGN, context
            )
            target_crs = self.parameterAsCrs(
                parameters, self.TARGET_CRS, context
            )
            apply_div_b = self.parameterAsBoolean(
                parameters, self.APPLY_DIVISOR_B, context
            )
            divisor_b = self.parameterAsDouble(
                parameters, self.DIVISOR_B, context
            )
            dim = self.parameterAsEnum(parameters, self.GRID_SIZE, context) + 3

            out_a_class = self.parameterAsOutputLayer(
                parameters, self.OUT_A_CLASS, context
            )
            out_b_class = self.parameterAsOutputLayer(
                parameters, self.OUT_B_CLASS, context
            )
            out_bivar = self.parameterAsOutputLayer(
                parameters, self.OUT_BIVAR, context
            )

            tmpdir = tempfile.mkdtemp(prefix='bivar_')
            feedback.pushInfo(f'Working directory: {tmpdir}')

            def warp_to_match(src, dst, ref, t_srs):
                feedback.pushInfo(
                    f'Warping {os.path.basename(src)} to match reference grid'
                )
                ref_ds = gdal.Open(ref)
                if ref_ds is None:
                    raise QgsProcessingException(
                        f'Cannot open reference raster: {ref}'
                    )

                gt = ref_ds.GetGeoTransform()
                px, py = abs(gt[1]), abs(gt[5])
                minx, maxy = gt[0], gt[3]
                cols, rows = ref_ds.RasterXSize, ref_ds.RasterYSize
                maxx, miny = minx + cols * px, maxy - rows * py
                ref_ds = None

                args = {
                    'INPUT': src,
                    'SOURCE_CRS': None,
                    'TARGET_CRS': t_srs,
                    'RESAMPLING': 1,
                    'NODATA': None,
                    'TARGET_EXTENT': f'{minx},{maxx},{miny},{maxy}',
                    'TARGET_EXTENT_CRS': t_srs,
                    'TARGET_RESOLUTION': px,
                    'OPTIONS': '',
                    'DATA_TYPE': GDAL_WARP_DTYPE_FLOAT32,
                    'MULTITHREADING': True,
                    'OUTPUT': dst
                }
                return processing.run(
                    'gdal:warpreproject',
                    args,
                    context=context,
                    feedback=feedback
                )

            path_a = raster_a.source()
            path_b = raster_b.source()
            final_crs = (
                target_crs if target_crs.isValid() else raster_a.crs()
            )

            if do_align:
                feedback.pushInfo('Aligning rasters...')
                a_al = os.path.join(tmpdir, 'A_aligned.tif')
                warp_to_match(path_a, a_al, path_a, final_crs)
                b_al = os.path.join(tmpdir, 'B_aligned.tif')
                warp_to_match(path_b, b_al, a_al, final_crs)
            else:
                a_al, b_al = path_a, path_b

            b_input = b_al
            if apply_div_b:
                feedback.pushInfo(f'Dividing Raster B by {divisor_b}')
                b_scaled = os.path.join(tmpdir, 'B_scaled.tif')
                _runcalc_dual(
                    f'"A@1"/{divisor_b}',
                    f'A/{divisor_b}',
                    [b_al],
                    b_scaled,
                    feedback
                )
                b_input = b_scaled

            def quantiles(path):
                feedback.pushInfo(
                    f'Computing {dim}-class quantiles for {os.path.basename(path)}'
                )
                ds = gdal.Open(path)
                if ds is None:
                    raise QgsProcessingException(
                        f'Cannot open raster: {path}'
                    )

                band = ds.GetRasterBand(1)
                arr = band.ReadAsArray().astype('float64')
                nd = band.GetNoDataValue()
                ds = None

                if nd is not None:
                    arr[arr == nd] = np.nan

                vals = arr[np.isfinite(arr)]
                if vals.size == 0:
                    raise QgsProcessingException(
                        f'No valid pixels in {os.path.basename(path)} '
                        'to compute quantiles'
                    )

                breaks = np.percentile(
                    vals,
                    [100.0 * i / dim for i in range(1, dim)]
                )
                feedback.pushInfo(
                    '  Breaks: ' + ', '.join(f'{v:.4f}' for v in breaks)
                )
                return [float(v) for v in breaks]

            a_breaks = quantiles(a_al)
            b_breaks = quantiles(b_input)

            def class_expr(breaks, quoted):
                token = '"A@1"' if quoted else 'A'
                return '1 + ' + ' + '.join(
                    f'({token}>{value})' for value in breaks
                )

            feedback.pushInfo(
                f'Reclassifying Raster A / Variable 1 / Y to {dim} classes...'
            )
            _runcalc_dual(
                class_expr(a_breaks, True),
                class_expr(a_breaks, False),
                [a_al],
                out_a_class,
                feedback
            )

            feedback.pushInfo(
                f'Reclassifying Raster B / Variable 2 / X to {dim} classes...'
            )
            _runcalc_dual(
                class_expr(b_breaks, True),
                class_expr(b_breaks, False),
                [b_input],
                out_b_class,
                feedback
            )

            # Print Layout and palette code order use X first and Y second.
            # Raster B is Variable 2 / X; Raster A is Variable 1 / Y.
            # Therefore code = (Raster B class * 10) + Raster A class.
            feedback.pushInfo(
                'Combining codes as X first, Y second '
                '(Variable 2/Raster B first; Variable 1/Raster A second)...'
            )
            _runcalc_dual(
                '"A@1"*10 + "B@1"',
                '(A*10)+B',
                [out_b_class, out_a_class],
                out_bivar,
                feedback
            )

            feedback.pushInfo('=' * 50)
            feedback.pushInfo(
                'Raster A / Variable 1 / Y breaks: '
                + ', '.join(f'{v:.4f}' for v in a_breaks)
            )
            feedback.pushInfo(
                'Raster B / Variable 2 / X breaks: '
                + ', '.join(f'{v:.4f}' for v in b_breaks)
            )
            feedback.pushInfo(
                'Bivariate code convention: first digit = X / Variable 2; '
                'second digit = Y / Variable 1.'
            )
            feedback.pushInfo('=' * 50)
            feedback.pushInfo('Bivariate raster generated successfully.')
            feedback.pushInfo(
                'Use "Bivariate Style Generator" to apply colors.'
            )

            return {
                self.OUT_A_CLASS: out_a_class,
                self.OUT_B_CLASS: out_b_class,
                self.OUT_BIVAR: out_bivar
            }

        except QgsProcessingException:
            raise
        except Exception as e:
            feedback.reportError(f'Error: {e}', True)
            raise QgsProcessingException(str(e))
