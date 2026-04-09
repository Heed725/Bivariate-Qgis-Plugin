"""
QGIS Processing Script: Bivariate Raster Generator
Classifies two rasters into terciles (1/2/3) and combines into bivariate codes 11-33.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from palettes import PALETTES, CODE_LABELS


from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterCrs,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsRasterLayer, QgsProcessingException,
)
import processing
from osgeo import gdal
import numpy as np
import os, tempfile


def _calc_gdal(expr, layer_A, layer_B, out_path):
    return processing.run('gdal:rastercalculator', {
        'INPUT_A': layer_A, 'BAND_A': 1,
        'INPUT_B': layer_B, 'BAND_B': 1,
        'FORMULA': expr, 'NO_DATA': None, 'RTYPE': 6,
        'OPTIONS': '', 'EXTRA': '', 'OUTPUT': out_path})


def _calc_qgis(expr, layers, out_path):
    from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
    entries, layer_dict = [], {}
    for idx, lp in enumerate(layers):
        ref = chr(65 + idx)
        lyr = QgsRasterLayer(lp, f'layer_{ref}') if isinstance(lp, str) else lp
        if not lyr.isValid():
            raise QgsProcessingException(f'Invalid layer: {lp}')
        e = QgsRasterCalculatorEntry()
        e.ref = f'{ref}@1'; e.raster = lyr; e.bandNumber = 1
        entries.append(e); layer_dict[ref] = lyr
    calc = QgsRasterCalculator(expr, out_path, 'GTiff',
        layer_dict['A'].extent(), layer_dict['A'].width(), layer_dict['A'].height(), entries)
    if calc.processCalculation() != 0:
        raise QgsProcessingException('QGIS raster calc failed')
    return {'OUTPUT': out_path}


def _calc(qexpr, gexpr, layers, out_path, feedback):
    try:
        return _calc_gdal(gexpr, layers[0], layers[1] if len(layers)>1 else layers[0], out_path)
    except Exception as e1:
        feedback.pushWarning(f'GDAL failed: {e1}')
        return _calc_qgis(qexpr, layers, out_path)


class BivariateRasterGenerator(QgsProcessingAlgorithm):
    RASTER_A = 'RASTER_A'; RASTER_B = 'RASTER_B'
    DO_REPROJECT_ALIGN = 'DO_REPROJECT_ALIGN'; TARGET_CRS = 'TARGET_CRS'
    APPLY_DIVISOR_B = 'APPLY_DIVISOR_B'; DIVISOR_B = 'DIVISOR_B'
    OUT_A_CLASS = 'OUT_A_CLASS'; OUT_B_CLASS = 'OUT_B_CLASS'; OUT_BIVAR = 'OUT_BIVAR'

    def tr(self, t): return QCoreApplication.translate('BivariateRasterGenerator', t)
    def createInstance(self): return BivariateRasterGenerator()
    def name(self):        return 'bivariate_raster_generator'
    def displayName(self): return self.tr('Bivariate Raster Generator')
    def group(self):       return self.tr('Cartography')
    def groupId(self):     return 'cartography'
    def shortHelpString(self):
        return self.tr(
            'Classifies two rasters into terciles (1/2/3) using quantile breaks, '
            'then combines them into a bivariate raster with values 11–33.\n\n'
            'Apply color style with the Bivariate Style Generator tool.')

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_A, self.tr('Raster A')))
        self.addParameter(QgsProcessingParameterRasterLayer(self.RASTER_B, self.tr('Raster B')))
        self.addParameter(QgsProcessingParameterBoolean(
            self.DO_REPROJECT_ALIGN, self.tr('Reproject & align to Raster A grid?'), defaultValue=True))
        self.addParameter(QgsProcessingParameterCrs(
            self.TARGET_CRS, self.tr('Target CRS (optional)'), optional=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.APPLY_DIVISOR_B, self.tr('Divide Raster B by factor?'), defaultValue=False))
        self.addParameter(QgsProcessingParameterNumber(
            self.DIVISOR_B, self.tr('Division factor for Raster B'),
            type=QgsProcessingParameterNumber.Double, defaultValue=30.0, minValue=1e-6))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT_A_CLASS, self.tr('Output: Raster A class (1-3)')))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT_B_CLASS, self.tr('Output: Raster B class (1-3)')))
        self.addParameter(QgsProcessingParameterRasterDestination(self.OUT_BIVAR,   self.tr('Output: Bivariate code (11-33)')))

    def processAlgorithm(self, parameters, context, feedback):
        ra = self.parameterAsRasterLayer(parameters, self.RASTER_A, context)
        rb = self.parameterAsRasterLayer(parameters, self.RASTER_B, context)
        if not ra or not ra.isValid(): raise QgsProcessingException('Raster A invalid')
        if not rb or not rb.isValid(): raise QgsProcessingException('Raster B invalid')

        do_align   = self.parameterAsBoolean(parameters, self.DO_REPROJECT_ALIGN, context)
        target_crs = self.parameterAsCrs(parameters, self.TARGET_CRS, context)
        apply_div  = self.parameterAsBoolean(parameters, self.APPLY_DIVISOR_B, context)
        divisor    = self.parameterAsDouble(parameters, self.DIVISOR_B, context)
        out_a      = self.parameterAsOutputLayer(parameters, self.OUT_A_CLASS, context)
        out_b      = self.parameterAsOutputLayer(parameters, self.OUT_B_CLASS, context)
        out_bv     = self.parameterAsOutputLayer(parameters, self.OUT_BIVAR, context)

        tmpdir = tempfile.mkdtemp(prefix='bivar_')
        pa, pb = ra.source(), rb.source()
        final_crs = target_crs if target_crs.isValid() else ra.crs()

        def warp(src, dst, ref):
            ds = gdal.Open(ref)
            gt = ds.GetGeoTransform()
            px = abs(gt[1]); py = abs(gt[5])
            minx, maxy = gt[0], gt[3]
            maxx = minx + ds.RasterXSize*px; miny = maxy - ds.RasterYSize*py
            processing.run('gdal:warpreproject', {
                'INPUT': src, 'SOURCE_CRS': None, 'TARGET_CRS': final_crs,
                'RESAMPLING': 1, 'NODATA': None,
                'TARGET_EXTENT': f'{minx},{maxx},{miny},{maxy}',
                'TARGET_EXTENT_CRS': final_crs, 'TARGET_RESOLUTION': px,
                'OPTIONS': '', 'DATA_TYPE': 6, 'MULTITHREADING': True, 'OUTPUT': dst},
                context=context, feedback=feedback)

        if do_align:
            a_al = os.path.join(tmpdir,'A_al.tif'); b_al = os.path.join(tmpdir,'B_al.tif')
            warp(pa, a_al, pa); warp(pb, b_al, a_al)
        else:
            a_al, b_al = pa, pb

        b_in = b_al
        if apply_div:
            b_sc = os.path.join(tmpdir,'B_sc.tif')
            _calc(f'"B@1"/{divisor}', f'B/{divisor}', [b_al], b_sc, feedback)
            b_in = b_sc

        def quantiles(path):
            ds = gdal.Open(path)
            band = ds.GetRasterBand(1)
            arr = band.ReadAsArray().astype('float64')
            nd = band.GetNoDataValue()
            if nd is not None: arr[arr == nd] = np.nan
            vals = arr[~np.isnan(arr)]
            return np.percentile(vals, [33.333, 66.667])

        aq1, aq2 = quantiles(a_al)
        bq1, bq2 = quantiles(b_in)

        _calc(f'("A@1"<={aq1})*1+(("A@1">{aq1})*("A@1"<={aq2}))*2+("A@1">{aq2})*3',
              f'(A<={aq1})*1+((A>{aq1})*(A<={aq2}))*2+(A>{aq2})*3', [a_al], out_a, feedback)
        _calc(f'("B@1"<={bq1})*1+(("B@1">{bq1})*("B@1"<={bq2}))*2+("B@1">{bq2})*3',
              f'(B<={bq1})*1+((B>{bq1})*(B<={bq2}))*2+(B>{bq2})*3', [b_in], out_b, feedback)
        _calc('"A@1"*10+"B@1"', '(A*10)+B', [out_a, out_b], out_bv, feedback)

        feedback.pushInfo(f'A terciles: {aq1:.4f}, {aq2:.4f}')
        feedback.pushInfo(f'B terciles: {bq1:.4f}, {bq2:.4f}')
        return {self.OUT_A_CLASS: out_a, self.OUT_B_CLASS: out_b, self.OUT_BIVAR: out_bv}
