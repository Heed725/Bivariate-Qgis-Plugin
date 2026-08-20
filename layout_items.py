"""Native QGIS Print Layout items for bivariate box/diamond legends."""
import json
import math
import re

from qgis.PyQt.QtCore import Qt, QRectF, QPointF, QCoreApplication
from qgis.PyQt.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPolygonF, QIcon, QPixmap, QPainterPath
from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, QLineEdit,
    QDoubleSpinBox, QCheckBox, QGroupBox, QColorDialog, QLabel, QPushButton,
    QGraphicsItem,
)
from qgis.core import (
    QgsApplication, QgsCategorizedSymbolRenderer, QgsLayoutItem,
    QgsLayoutItemAbstractMetadata, QgsLayoutItemMap, QgsLayoutItemRegistry,
    QgsLayoutSize, QgsPalettedRasterRenderer, QgsProject, QgsRasterLayer,
    QgsUnitTypes, QgsVectorLayer,
)
from qgis.gui import QgsLayoutItemAbstractGuiMetadata, QgsLayoutItemBaseWidget

from .palettes import PALETTES, class_codes, palette_colors, transpose_palette

PLUGIN_BASE = QgsLayoutItemRegistry.PluginItem
TYPE_BOX = PLUGIN_BASE + 1338
TYPE_DIAMOND = PLUGIN_BASE + 1339
PALETTE_NAMES = list(PALETTES.keys()) + ['Custom / Staridas import']
SOURCE_AUTO = '__AUTO__'
SOURCE_MANUAL = '__MANUAL__'


def _hex(color):
    try:
        return QColor(color).name().upper()
    except Exception:
        return None


def _plugin_style(layer):
    try:
        dim = int(layer.customProperty('bivariate_plugin/dimension', 0))
        colors = json.loads(str(layer.customProperty('bivariate_plugin/colors', '') or ''))
        if dim not in (3, 4, 5) or not isinstance(colors, list) or len(colors) != dim * dim:
            return None
        colors = [_hex(c) for c in colors]
        return (colors, dim) if all(colors) else None
    except Exception:
        return None


def _vector_style(layer):
    try:
        renderer = layer.renderer()
        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            return None
        found = {}
        for cat in renderer.categories():
            code = str(cat.value()).strip().upper()
            if not re.fullmatch(r'[A-E][1-5]', code) or cat.symbol() is None:
                continue
            color = _hex(cat.symbol().color())
            if color:
                found[code] = color
        if not found:
            return None
        dim = max(max(ord(c[0]) - 64 for c in found), max(int(c[1:]) for c in found))
        expected = class_codes(dim, vector=True) if dim in (3, 4, 5) else []
        return ([found[c] for c in expected], dim) if expected and all(c in found for c in expected) else None
    except Exception:
        return None


def _raster_style(layer):
    try:
        renderer = layer.renderer()
        if not isinstance(renderer, QgsPalettedRasterRenderer) and not hasattr(renderer, 'classes'):
            return None
        found = {}
        for entry in renderer.classes():
            try:
                code = str(int(round(float(entry.value))))
                color = _hex(entry.color)
            except Exception:
                continue
            if re.fullmatch(r'[1-5][1-5]', code) and color:
                found[code] = color
        if not found:
            return None
        dim = max(max(int(c[0]) for c in found), max(int(c[1]) for c in found))
        expected = class_codes(dim, vector=False) if dim in (3, 4, 5) else []
        return ([found[c] for c in expected], dim) if expected and all(c in found for c in expected) else None
    except Exception:
        return None


def _detect(layer):
    if layer is None:
        return None
    try:
        if not layer.isValid():
            return None
    except Exception:
        return None
    if isinstance(layer, QgsVectorLayer):
        return _vector_style(layer) or _plugin_style(layer)
    if isinstance(layer, QgsRasterLayer):
        return _raster_style(layer) or _plugin_style(layer)
    return None


def _layout_layers(layout):
    result, seen = [], set()

    def add(layer):
        try:
            if isinstance(layer, (QgsVectorLayer, QgsRasterLayer)) and layer.isValid() and layer.id() not in seen:
                seen.add(layer.id())
                result.append(layer)
        except Exception:
            pass

    if layout is not None:
        try:
            for item in layout.items():
                if not isinstance(item, QgsLayoutItemMap):
                    continue
                try:
                    layers = item.layersToRender()
                except Exception:
                    try:
                        layers = item.layers()
                    except Exception:
                        layers = []
                for layer in layers:
                    add(layer)
        except Exception:
            pass
    if not result:
        for layer in QgsProject.instance().mapLayers().values():
            add(layer)
    return result


def _source_layer(layout, source_id):
    if source_id == SOURCE_MANUAL:
        return None
    if source_id and source_id != SOURCE_AUTO:
        layer = QgsProject.instance().mapLayer(source_id)
        return layer if _detect(layer) else None
    for layer in _layout_layers(layout):
        if _detect(layer):
            return layer
    return None


def _resolve_manual(pal_idx, custom, dim, transposed):
    name = PALETTE_NAMES[pal_idx] if 0 <= pal_idx < len(PALETTE_NAMES) else PALETTE_NAMES[-1]
    try:
        colors = palette_colors(name, dim, custom)
    except Exception:
        colors = ['#CCCCCC'] * (dim * dim)
    return transpose_palette(colors, dim) if transposed else colors


def _text_color(color):
    c = QColor(color)
    return QColor('#111111') if (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000 > 155 else QColor('#F5F5F5')


def _icon(colors, diamond=False, size=24):
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    order = [6, 7, 8, 3, 4, 5, 0, 1, 2]
    cs = size / 3.5
    for i, ci in enumerate(order):
        col, row = i % 3, i // 3
        c = QColor(colors[ci])
        if diamond:
            cx = size / 2 + (col - 1) * cs * .82 - (row - 1) * cs * .82
            cy = size / 2 + (col - 1) * cs * .45 + (row - 1) * cs * .45 + cs * .25
            h = cs * .5
            p.setBrush(QBrush(c)); p.setPen(Qt.NoPen)
            p.drawPolygon(QPolygonF([QPointF(cx, cy-h), QPointF(cx+h, cy), QPointF(cx, cy+h), QPointF(cx-h, cy)]))
        else:
            x, y, w = col * (size / 3.1) + 1, row * (size / 3.1) + 1, size / 3.1 - 1.5
            p.fillRect(QRectF(x, y, w, w), QBrush(c))
    p.end()
    return QIcon(px)


class _BivariateBaseItem(QgsLayoutItem):
    def __init__(self, layout):
        super().__init__(layout)
        self.setCacheMode(QGraphicsItem.NoCache)
        self._pal_idx = 6
        self._custom = ''
        self._dim = 3
        self._cell_size = 18.0
        self._gap = 1.5
        # Keep internal A/B fields for project compatibility, but expose the
        # same convention as the map: Variable 2 = X, Variable 1 = Y.
        self._label_a = 'Variable 2'
        self._label_b = 'Variable 1'
        self._show_labels = False
        self._show_codes = False
        self._fit_to_item = True
        self._outline_hex = '#4A4A4A'
        self._outline_w = 0.3
        self._transposed = False
        self._linked_layer_id = SOURCE_AUTO
        try:
            self.attemptResize(QgsLayoutSize(80, 80, QgsUnitTypes.LayoutMillimeters))
        except Exception:
            pass

    def writePropertiesToElement(self, el, doc, ctx):
        attrs = {
            'palIdx': self._pal_idx, 'custom': self._custom, 'dimension': self._dim,
            'cellSize': self._cell_size, 'gap': self._gap, 'labelA': self._label_a,
            'labelB': self._label_b, 'showLabels': int(self._show_labels),
            'showCodes': int(self._show_codes), 'fitToItem': int(self._fit_to_item),
            'outlineHex': self._outline_hex, 'outlineW': self._outline_w,
            'transposed': int(self._transposed), 'linkedLayer': self._linked_layer_id,
        }
        for key, value in attrs.items():
            el.setAttribute(key, str(value))
        return True

    def readPropertiesFromElement(self, el, doc, ctx):
        self._pal_idx = int(el.attribute('palIdx', '6'))
        self._custom = el.attribute('custom', '')
        self._dim = int(el.attribute('dimension', '3'))
        self._cell_size = float(el.attribute('cellSize', '18'))
        self._gap = float(el.attribute('gap', '1.5'))
        self._label_a = el.attribute('labelA', 'Variable 2')
        self._label_b = el.attribute('labelB', 'Variable 1')
        self._show_labels = bool(int(el.attribute('showLabels', '0')))
        self._show_codes = bool(int(el.attribute('showCodes', '0')))
        self._fit_to_item = bool(int(el.attribute('fitToItem', '1')))
        self._outline_hex = el.attribute('outlineHex', '#4A4A4A')
        self._outline_w = float(el.attribute('outlineW', '0.3'))
        self._transposed = bool(int(el.attribute('transposed', '0')))
        self._linked_layer_id = el.attribute('linkedLayer', SOURCE_MANUAL) if el.hasAttribute('linkedLayer') else SOURCE_MANUAL
        return True

    def _legend_data(self):
        if self._linked_layer_id != SOURCE_MANUAL:
            detected = _detect(_source_layer(self.layout(), self._linked_layer_id))
            if detected:
                return detected
        return _resolve_manual(self._pal_idx, self._custom, self._dim, self._transposed), self._dim

    def _pen(self):
        pen = QPen(QColor(self._outline_hex))
        pen.setWidthF(self._outline_w)
        return pen


class BivariateBoxLegendItem(_BivariateBaseItem):
    def type(self): return TYPE_BOX
    def displayName(self): return 'Bivariate Box Legend'
    def icon(self): return _icon(self._legend_data()[0], False)

    def draw(self, ctx):
        p = ctx.renderContext().painter(); p.save(); p.setRenderHint(QPainter.Antialiasing)
        scale = ctx.renderContext().scaleFactor()
        iw, ih = self.rect().width() * scale, self.rect().height() * scale
        colors, dim = self._legend_data()
        gap = self._gap * scale
        if self._fit_to_item:
            label_cells = .72 if self._show_labels else 0
            cs = max(1.0, (min(iw, ih) - (dim - 1) * gap) / (dim + label_cells))
        else:
            cs = self._cell_size * scale
        step = cs + gap
        grid = dim * cs + (dim - 1) * gap
        label_space = cs * .72 if self._show_labels else 0
        ml = max(0, (iw - grid - label_space) / 2) + label_space
        mt = max(0, (ih - grid - label_space) / 2)
        pen = self._pen()
        codes = class_codes(dim, vector=False)
        cf = QFont(); cf.setBold(True); cf.setPointSizeF(max(4, (cs / scale) * .22))
        for row in range(dim):
            for col in range(dim):
                code = f'{col+1}{dim-row}'
                idx = codes.index(code)
                x, y = ml + col * step, mt + row * step
                p.fillRect(QRectF(x, y, cs, cs), QBrush(QColor(colors[idx])))
                p.setPen(pen); p.drawRect(QRectF(x, y, cs, cs))
                if self._show_codes:
                    p.setFont(cf); p.setPen(QPen(_text_color(colors[idx])))
                    p.drawText(QRectF(x, y, cs, cs), Qt.AlignCenter, code); p.setPen(pen)
        if self._show_labels:
            af = QFont(); af.setPointSizeF(max(5, (cs / scale) * .28)); p.setFont(af); p.setPen(QPen(QColor('#555555')))
            x_label = self._label_b if self._transposed and self._linked_layer_id == SOURCE_MANUAL else self._label_a
            y_label = self._label_a if self._transposed and self._linked_layer_id == SOURCE_MANUAL else self._label_b
            p.drawText(QRectF(ml, mt + grid + gap * .5, grid, cs * .8), Qt.AlignCenter, f'{x_label}  →')
            p.save(); p.translate(ml-gap*.5, mt+grid/2); p.rotate(-90)
            p.drawText(QRectF(-grid/2, -cs*.8, grid, cs*.8), Qt.AlignCenter, f'↑  {y_label}'); p.restore()
        p.restore()


class BivariateDiamondLegendItem(_BivariateBaseItem):
    def type(self): return TYPE_DIAMOND
    def displayName(self): return 'Bivariate Diamond Legend'
    def icon(self): return _icon(self._legend_data()[0], True)

    def draw(self, ctx):
        p = ctx.renderContext().painter(); p.save(); p.setRenderHint(QPainter.Antialiasing)
        scale = ctx.renderContext().scaleFactor()
        iw, ih = self.rect().width() * scale, self.rect().height() * scale
        colors, dim = self._legend_data()
        cs, gap = self._cell_size * scale, self._gap * scale
        step = cs + gap; half = cs / 2 * math.sqrt(2); a45 = math.radians(45)
        def raw(row, col):
            return (col*step*math.cos(a45)-row*step*math.sin(a45), col*step*math.sin(a45)+row*step*math.cos(a45))
        pts = [raw(r, c) for r in range(dim) for c in range(dim)]
        min_x, max_x = min(x for x, _ in pts)-half, max(x for x, _ in pts)+half
        min_y, max_y = min(y for _, y in pts)-half, max(y for _, y in pts)+half
        ox, oy = -min_x + (iw-(max_x-min_x))/2, -min_y + (ih-(max_y-min_y))/2
        codes = class_codes(dim, vector=False); pen = self._pen()
        cf = QFont(); cf.setBold(True); cf.setPointSizeF(max(4, self._cell_size * .22))
        for row in range(dim):
            for col in range(dim):
                code = f'{col+1}{row+1}'; idx = codes.index(code); rx, ry = raw(row, col); cx, cy = rx+ox, ry+oy
                path = QPainterPath(); path.moveTo(cx, cy-half); path.lineTo(cx+half, cy); path.lineTo(cx, cy+half); path.lineTo(cx-half, cy); path.closeSubpath()
                p.fillPath(path, QBrush(QColor(colors[idx]))); p.setPen(pen); p.drawPath(path)
                if self._show_codes:
                    p.setFont(cf); p.setPen(QPen(_text_color(colors[idx])))
                    p.drawText(QRectF(cx-half*.6, cy-half*.4, half*1.2, half*.8), Qt.AlignCenter, code); p.setPen(pen)
        p.restore()


class BivariatePropertiesWidget(QgsLayoutItemBaseWidget):
    def __init__(self, parent, item):
        super().__init__(parent, item)
        self._item = item; self._building = False
        self._build_ui(); self._populate()

    def setNewItem(self, item):
        if item.type() not in (TYPE_BOX, TYPE_DIAMOND): return False
        self._item = item; self._populate(); return True

    def _build_ui(self):
        root = QVBoxLayout(self); root.setContentsMargins(6, 6, 6, 6); root.setSpacing(8)
        gs = QGroupBox('Print Layout layer sensing'); fs = QFormLayout(gs)
        self._source = QComboBox(); fs.addRow('Source layer:', self._source)
        row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(0,0,0,0); h.setSpacing(5)
        self._rescan = QPushButton('Rescan layout'); self._status = QLabel(''); self._status.setWordWrap(True)
        h.addWidget(self._rescan); h.addWidget(self._status, 1); fs.addRow('', row); root.addWidget(gs)

        g1 = QGroupBox('Palette'); f1 = QFormLayout(g1)
        self._pal = QComboBox(); self._pal.addItems(PALETTE_NAMES); f1.addRow('Palette:', self._pal)
        self._dim = QComboBox(); self._dim.addItems(['3×3','4×4','5×5']); f1.addRow('Grid size:', self._dim)
        self._custom = QLineEdit(); self._custom.setPlaceholderText('Paste Staridas labelled HEX, CSS, or JSON'); f1.addRow('Custom colors:', self._custom)
        self._transpose = QCheckBox('Transpose axes (swap X ↔ Y)'); f1.addRow('', self._transpose); root.addWidget(g1)

        g2 = QGroupBox('Dimensions (mm)'); f2 = QFormLayout(g2)
        self._cell = QDoubleSpinBox(); self._cell.setRange(4,120); self._cell.setSingleStep(1); f2.addRow('Cell size:', self._cell)
        self._gap = QDoubleSpinBox(); self._gap.setRange(0,20); self._gap.setSingleStep(.5); f2.addRow('Gap:', self._gap)
        self._fit = QCheckBox('Fit and center grid inside item'); f2.addRow('', self._fit); root.addWidget(g2)

        g3 = QGroupBox('Labels — same axes as map'); f3 = QFormLayout(g3)
        self._la = QLineEdit(); self._lb = QLineEdit(); f3.addRow('Variable 2 (X):', self._la); f3.addRow('Variable 1 (Y):', self._lb)
        self._show_labels = QCheckBox('Show axis labels (box only)'); self._show_codes = QCheckBox('Show class codes on cells')
        f3.addRow(self._show_labels); f3.addRow(self._show_codes); root.addWidget(g3)

        g4 = QGroupBox('Outline'); f4 = QFormLayout(g4)
        self._outline = QPushButton(); self._outline.setFixedHeight(24); f4.addRow('Color:', self._outline)
        self._outline_w = QDoubleSpinBox(); self._outline_w.setRange(0,5); self._outline_w.setSingleStep(.1); f4.addRow('Width (mm):', self._outline_w)
        root.addWidget(g4); root.addStretch()

        self._source.currentIndexChanged.connect(self._source_changed); self._rescan.clicked.connect(self._rescan_sources)
        for signal in (self._pal.currentIndexChanged, self._dim.currentIndexChanged, self._transpose.toggled,
                       self._cell.valueChanged, self._gap.valueChanged, self._fit.toggled,
                       self._show_labels.toggled, self._show_codes.toggled, self._outline_w.valueChanged):
            signal.connect(self._apply)
        self._custom.editingFinished.connect(self._apply); self._la.editingFinished.connect(self._apply); self._lb.editingFinished.connect(self._apply)
        self._outline.clicked.connect(self._pick_color)

    def _populate_sources(self):
        current = self._item._linked_layer_id
        self._source.blockSignals(True); self._source.clear()
        self._source.addItem('Auto — detect from Print Layout map', SOURCE_AUTO)
        self._source.addItem('Manual — use palette settings below', SOURCE_MANUAL)
        for layer in _layout_layers(self._item.layout()):
            kind = 'Raster' if isinstance(layer, QgsRasterLayer) else 'Vector'
            suffix = ' • bivariate detected' if _detect(layer) else ''
            self._source.addItem(f'{layer.name()} [{kind}]{suffix}', layer.id())
        idx = self._source.findData(current)
        self._source.setCurrentIndex(idx if idx >= 0 else (0 if current == SOURCE_AUTO else 1)); self._source.blockSignals(False)

    def _populate(self):
        self._building = True; it = self._item; self._populate_sources()
        self._pal.setCurrentIndex(it._pal_idx); self._dim.setCurrentIndex(it._dim-3); self._custom.setText(it._custom)
        self._transpose.setChecked(it._transposed); self._cell.setValue(it._cell_size); self._gap.setValue(it._gap); self._fit.setChecked(it._fit_to_item)
        self._la.setText(it._label_a); self._lb.setText(it._label_b); self._show_labels.setChecked(it._show_labels); self._show_codes.setChecked(it._show_codes)
        self._set_outline(it._outline_hex); self._outline_w.setValue(it._outline_w); self._building = False; self._update_status()

    def _update_status(self):
        sid = self._item._linked_layer_id
        if sid == SOURCE_MANUAL:
            self._status.setText('Manual palette • X = Variable 2, Y = Variable 1'); self._enable_palette(True); return
        layer = _source_layer(self._item.layout(), sid); detected = _detect(layer)
        if detected:
            _, dim = detected; kind = 'raster' if isinstance(layer, QgsRasterLayer) else 'vector'
            self._status.setText(f'Detected {dim}×{dim} {kind}: {layer.name()} • X = Variable 2, Y = Variable 1'); self._enable_palette(False)
        else:
            self._status.setText('No bivariate raster/vector style detected; manual palette is used.'); self._enable_palette(True)

    def _enable_palette(self, enabled):
        for w in (self._pal, self._dim, self._custom, self._transpose): w.setEnabled(enabled)

    def _rescan_sources(self):
        if self._building: return
        chosen = self._source.currentData() or SOURCE_AUTO; self._item._linked_layer_id = chosen
        self._populate_sources(); self._update_status(); self._item.refresh()

    def _source_changed(self):
        if self._building: return
        self._item._linked_layer_id = self._source.currentData() or SOURCE_AUTO; self._update_status(); self._item.refresh()

    def _set_outline(self, color):
        self._outline.setStyleSheet(f'background:{color};border:1px solid #888;border-radius:3px'); self._outline.setText(color)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._item._outline_hex), self)
        if c.isValid(): self._item._outline_hex = c.name(); self._set_outline(c.name()); self._item.refresh()

    def _apply(self):
        if self._building: return
        it = self._item
        it._pal_idx = self._pal.currentIndex(); it._dim = self._dim.currentIndex()+3; it._custom = self._custom.text(); it._transposed = self._transpose.isChecked()
        it._cell_size = self._cell.value(); it._gap = self._gap.value(); it._fit_to_item = self._fit.isChecked(); it._label_a = self._la.text(); it._label_b = self._lb.text()
        it._show_labels = self._show_labels.isChecked(); it._show_codes = self._show_codes.isChecked(); it._outline_w = self._outline_w.value(); it.refresh()


class BivariateBoxLegendMetadata(QgsLayoutItemAbstractMetadata):
    def __init__(self): super().__init__(TYPE_BOX, QCoreApplication.translate('BivariatePlugin', 'Bivariate Box Legend'))
    def createItem(self, layout): return BivariateBoxLegendItem(layout)


class BivariateDiamondLegendMetadata(QgsLayoutItemAbstractMetadata):
    def __init__(self): super().__init__(TYPE_DIAMOND, QCoreApplication.translate('BivariatePlugin', 'Bivariate Diamond Legend'))
    def createItem(self, layout): return BivariateDiamondLegendItem(layout)


class BivariateBoxLegendGuiMetadata(QgsLayoutItemAbstractGuiMetadata):
    def __init__(self): super().__init__(TYPE_BOX, QCoreApplication.translate('BivariatePlugin', 'Bivariate Box Legend'))
    def creationIcon(self): return _icon(list(PALETTES.values())[6], False, 24)
    def createItemWidget(self, item): return BivariatePropertiesWidget(None, item)


class BivariateDiamondLegendGuiMetadata(QgsLayoutItemAbstractGuiMetadata):
    def __init__(self): super().__init__(TYPE_DIAMOND, QCoreApplication.translate('BivariatePlugin', 'Bivariate Diamond Legend'))
    def creationIcon(self): return _icon(list(PALETTES.values())[6], True, 24)
    def createItemWidget(self, item): return BivariatePropertiesWidget(None, item)