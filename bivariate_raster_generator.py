## Bivariate Raster Generator (Quantile-based Classification)
## QGIS 3.40 compatible version
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
import os, tempfile

# In QGIS 3.40, gdal:rastercalculator RTYPE enum is:
#   0=Byte, 1=Int16, 2=UInt16, 3=UInt32, 4=Int32, 5=Float32, 6=Float64
# Same enum is used for gdal:warpreproject DATA_TYPE (with extra leading "Use input layer data type" = 0,
# shifting others by 1: 1=Byte, 2=Int16, ..., 6=Float32, 7=Float64). We pin Float32 explicitly.
GDAL_RTYPE_FLOAT32 = 5
GDAL_WARP_DTYPE_FLOAT32 = 6  # warpreproject has "Use Input Layer Data Type" as enum 0

# ---------- Raster calculator helpers ----------
def _calc_gdal(expr, layer_A, layer_B, out_path, rtype=GDAL_RTYPE_FLOAT32):
    """GDAL raster calculator using variables A,B. Float32 by default."""
    params = {
        'INPUT_A': layer_A, 'BAND_A': 1,
        'INPUT_B': layer_B, 'BAND_B': 1,
        'FORMULA': expr,
        'NO_DATA': None,
        'RTYPE': rtype,
        'OPTIONS': '',
        'EXTRA': '',
        'OUTPUT': out_path
    }
    return processing.run('gdal:rastercalculator', params)

def _calc_qgis(expr, layers, out_path):
    """QGIS native raster calculator using layer references A@1, B@1, ..."""
    from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry

    entries = []
    layer_dict = {}

    for idx, layer_path in enumerate(layers):
        ref_name = chr(65 + idx)  # A, B, C, ...
        if isinstance(layer_path, str):
            layer = QgsRasterLayer(layer_path, f'layer_{ref_name}')
        else:
            layer = layer_path

        if not layer.isValid():
            raise QgsProcessingException(f"Invalid layer: {layer_path}")

        entry = QgsRasterCalculatorEntry()
        entry.ref = f'{ref_name}@1'
        entry.raster = layer
        entry.bandNumber = 1
        entries.append(entry)
        layer_dict[ref_name] = layer

    ref_layer = layer_dict['A']

    # Use the modern (3.8+) constructor signature with explicit CRS and transform context.
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
            f"Raster calculation failed (code {result}). {err}"
        )

    return {'OUTPUT': out_path}

def _runcalc_dual(qgis_expr, gdal_expr, layers, out_path, feedback):
    """Try GDAL calc first (more reliable); fall back to QGIS native calc."""
    A = layers[0]
    B = layers[1] if len(layers) > 1 else layers[0]

    try:
        feedback.pushInfo(f"GDAL calc: {gdal_expr}")
        return _calc_gdal(gdal_expr, A, B, out_path)
    except Exception as e_gdal:
        feedback.pushWarning(f"GDAL calculator failed: {e_gdal}")
        try:
            feedback.pushInfo(f"Falling back to QGIS calc: {qgis_expr}")
            return _calc_qgis(qgis_expr, layers, out_path)
        except Exception as e_qgis:
            raise QgsProcessingException(
                "Raster calculator failed in both GDAL and QGIS.\n"
                f"GDAL error: {e_gdal}\nQGIS error: {e_qgis}"
            )


# ---------- Processing Algorithm ----------
class BivariateRasterGenerator(QgsProcessingAlgorithm):
    # Params
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
            'This tool performs the raster processing only. Use the "Bivariate Style '
            'Generator" tool to create and apply color styles to the output.\n\n'
            'Options:\n'
            '- Optionally reproject & align both rasters to Raster A grid\n'
            '- Optionally divide Raster B by a factor (useful for unit conversion)\n'
            '- Outputs: Individual class rasters and combined bivariate raster'
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.RASTER_A, self.tr('Raster A (e.g. Temperature)')))
        self.addParameter(QgsProcessingParameterRasterLayer(
            self.RASTER_B, self.tr('Raster B (e.g. Precipitation)')))
        self.addParameter(QgsProcessingParameterEnum(
            self.GRID_SIZE, self.tr('Grid size'), options=['3×3', '4×4', '5×5'], defaultValue=0))

        self.addParameter(QgsProcessingParameterBoolean(
            self.DO_REPROJECT_ALIGN, self.tr('Reproject & align to Raster A grid?'),
            defaultValue=True))

        self.addParameter(QgsProcessingParameterCrs(
            self.TARGET_CRS, self.tr('Target CRS (optional, e.g. EPSG:21037)'),
            optional=True))

        self.addParameter(QgsProcessingParameterBoolean(
            self.APPLY_DIVISOR_B, self.tr('Divide Raster B by factor before processing?'),
            defaultValue=False))
        self.addParameter(QgsProcessingParameterNumber(
            self.DIVISOR_B, self.tr('Division factor for Raster B (e.g. 30)'),
            type=QgsProcessingParameterNumber.Double, defaultValue=30.0, minValue=1e-6))

        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUT_A_CLASS, self.tr('Output: Raster A class')))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUT_B_CLASS, self.tr('Output: Raster B class')))
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUT_BIVAR, self.tr('Output: Bivariate code')))

    def processAlgorithm(self, parameters, context, feedback):
        try:
            raster_a = self.parameterAsRasterLayer(parameters, self.RASTER_A, context)
            raster_b = self.parameterAsRasterLayer(parameters, self.RASTER_B, context)

            if not raster_a or not raster_a.isValid():
                raise QgsProcessingException("Raster A is invalid")
            if not raster_b or not raster_b.isValid():
                raise QgsProcessingException("Raster B is invalid")

            do_align = self.parameterAsBoolean(parameters, self.DO_REPROJECT_ALIGN, context)
            target_crs = self.parameterAsCrs(parameters, self.TARGET_CRS, context)
            apply_div_b = self.parameterAsBoolean(parameters, self.APPLY_DIVISOR_B, context)
            divisor_b = self.parameterAsDouble(parameters, self.DIVISOR_B, context)
            dim = self.parameterAsEnum(parameters, self.GRID_SIZE, context) + 3

            out_a_class = self.parameterAsOutputLayer(parameters, self.OUT_A_CLASS, context)
            out_b_class = self.parameterAsOutputLayer(parameters, self.OUT_B_CLASS, context)
            out_bivar = self.parameterAsOutputLayer(parameters, self.OUT_BIVAR, context)

            tmpdir = tempfile.mkdtemp(prefix='bivar_')
            feedback.pushInfo(f"Working directory: {tmpdir}")

            # ---------- Reproject & Align helper ----------
            def warp_to_match(src, dst, ref, t_srs, feedback):
                feedback.pushInfo(f"Warping {os.path.basename(src)} to match reference grid")
                ref_ds = gdal.Open(ref)
                if ref_ds is None:
                    raise QgsProcessingException(f"Cannot open reference raster: {ref}")

                gt = ref_ds.GetGeoTransform()
                px, py = abs(gt[1]), abs(gt[5])
                minx, maxy = gt[0], gt[3]
                cols, rows = ref_ds.RasterXSize, ref_ds.RasterYSize
                maxx, miny = minx + cols * px, maxy - rows * py
                ref_ds = None

                target_extent_str = f"{minx},{maxx},{miny},{maxy}"

                args = {
                    'INPUT': src,
                    'SOURCE_CRS': None,
                    'TARGET_CRS': t_srs,
                    'RESAMPLING': 1,  # 1 = Bilinear
                    'NODATA': None,
                    'TARGET_EXTENT': target_extent_str,
                    'TARGET_EXTENT_CRS': t_srs,
                    'TARGET_RESOLUTION': px,
                    'OPTIONS': '',
                    'DATA_TYPE': GDAL_WARP_DTYPE_FLOAT32,  # Float32 in warpreproject enum
                    'MULTITHREADING': True,
                    'OUTPUT': dst
                }

                return processing.run('gdal:warpreproject', args,
                                      context=context, feedback=feedback)

            path_a = raster_a.source()
            path_b = raster_b.source()
            final_crs = target_crs if target_crs.isValid() else raster_a.crs()

            if do_align:
                feedback.pushInfo("Aligning rasters...")
                # Reproject A to its target CRS first to set the canonical grid
                a_al = os.path.join(tmpdir, 'A_aligned.tif')
                warp_to_match(path_a, a_al, path_a, final_crs, feedback)
                # Then snap B to the A_aligned grid
                b_al = os.path.join(tmpdir, 'B_aligned.tif')
                warp_to_match(path_b, b_al, a_al, final_crs, feedback)
            else:
                a_al, b_al = path_a, path_b

            # ---------- Optional divide Raster B ----------
            b_input = b_al
            if apply_div_b:
                feedback.pushInfo(f"Dividing Raster B by {divisor_b}")
                b_scaled = os.path.join(tmpdir, 'B_scaled.tif')
                _runcalc_dual(
                    f'"B@1"/{divisor_b}',
                    f'B/{divisor_b}',
                    [b_al], b_scaled, feedback
                )
                b_input = b_scaled

            # ---------- Compute quantile breaks ----------
            def quantiles(path, feedback):
                feedback.pushInfo(f"Computing {dim}-class quantiles for {os.path.basename(path)}")
                ds = gdal.Open(path)
                if ds is None:
                    raise QgsProcessingException(f"Cannot open raster: {path}")

                band = ds.GetRasterBand(1)
                arr = band.ReadAsArray().astype('float64')
                nd = band.GetNoDataValue()
                ds = None

                if nd is not None:
                    arr[arr == nd] = np.nan

                vals = arr[np.isfinite(arr)]

                if vals.size == 0:
                    raise QgsProcessingException(
                        f"No valid pixels in {os.path.basename(path)} to compute quantiles"
                    )

                breaks = np.percentile(vals, [100.0 * i / dim for i in range(1, dim)])
                feedback.pushInfo('  Breaks: ' + ', '.join(f'{v:.4f}' for v in breaks))
                return [float(v) for v in breaks]

            a_breaks = quantiles(a_al, feedback)
            b_breaks = quantiles(b_input, feedback)

            def class_expr(breaks, quoted):
                token = '"A@1"' if quoted else 'A'
                return '1 + ' + ' + '.join(f'({token}>{value})' for value in breaks)

            feedback.pushInfo(f"Reclassifying Raster A to {dim} quantile classes...")
            qgis_expr_A = class_expr(a_breaks, True)
            gdal_expr_A = class_expr(a_breaks, False)
            _runcalc_dual(qgis_expr_A, gdal_expr_A, [a_al], out_a_class, feedback)

            feedback.pushInfo(f"Reclassifying Raster B to {dim} quantile classes...")
            qgis_expr_B = class_expr(b_breaks, True)
            gdal_expr_B = class_expr(b_breaks, False)
            # Note: pass b_input as the only layer, so it becomes A@1 / A in expressions
            _runcalc_dual(qgis_expr_B, gdal_expr_B, [b_input], out_b_class, feedback)

            feedback.pushInfo("Combining into bivariate codes...")
            _runcalc_dual(
                '"A@1"*10 + "B@1"',
                '(A*10)+B',
                [out_a_class, out_b_class],
                out_bivar, feedback
            )

            feedback.pushInfo('=' * 50)
            feedback.pushInfo('Raster A breaks: ' + ', '.join(f'{v:.4f}' for v in a_breaks))
            feedback.pushInfo('Raster B breaks: ' + ', '.join(f'{v:.4f}' for v in b_breaks))
            feedback.pushInfo('=' * 50)
            feedback.pushInfo('Bivariate raster generated successfully.')
            feedback.pushInfo('Use "Bivariate Style Generator" to apply colors.')

            return {
                self.OUT_A_CLASS: out_a_class,
                self.OUT_B_CLASS: out_b_class,
                self.OUT_BIVAR: out_bivar
            }

        except QgsProcessingException:
            raise
        except Exception as e:
            feedback.reportError(f"Error: {e}", True)
            raise QgsProcessingException(str(e))
