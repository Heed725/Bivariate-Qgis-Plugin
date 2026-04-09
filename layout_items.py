"""
layout_items.py — Bivariate Legend Layout Items
Modelled exactly on DataPlotly's approach (DataPlotly-4_4_1).

Two separate classes/registrations required:
  1. PlotLayoutItemMetadata       → QgsLayoutItemAbstractMetadata
     registered via: QgsApplication.layoutItemRegistry().addLayoutItemType(...)

  2. PlotLayoutItemGuiMetadata    → QgsLayoutItemAbstractGuiMetadata
     registered via: QgsGui.layoutItemGuiRegistry().addLayoutItemGuiMetadata(...)

Both metadata objects must be stored on the plugin instance (not module-level)
so Python's GC cannot destroy them while QGIS holds them.
"""

import os, sys, math
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from .palettes import PALETTES, CODE_LABELS

from qgis.PyQt.QtCore    import Qt, QRectF, QPointF, QCoreApplication
from qgis.PyQt.QtGui     import (QPainter, QColor, QFont, QPen, QBrush,
                                  QPolygonF, QIcon, QPixmap, QPainterPath)
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QFormLayout,
                                  QComboBox, QLineEdit, QDoubleSpinBox,
                                  QCheckBox, QGroupBox, QColorDialog,
                                  QPushButton, QGraphicsItem)
from qgis.core import (
    QgsLayoutItem,
    QgsLayoutItemRegistry,
    QgsLayoutItemAbstractMetadata,
    QgsApplication,
    QgsLayoutSize, QgsUnitTypes,
    QgsReadWriteContext,
)
from qgis.gui import (
    QgsGui,
    QgsLayoutItemBaseWidget,
    QgsLayoutItemAbstractGuiMetadata,   # ← correct class (not QgsLayoutItemGuiMetadata)
)

# ── Type IDs — must be unique integers > QgsLayoutItemRegistry.PluginItem ─────
# DataPlotly uses PluginItem + 1337; we use PluginItem + 1338 / 1339
PLUGIN_BASE  = QgsLayoutItemRegistry.PluginItem
TYPE_BOX     = PLUGIN_BASE + 1338
TYPE_DIAMOND = PLUGIN_BASE + 1339

PALETTE_NAMES = list(PALETTES.keys()) + ['Custom']
CODES_ORDER   = ['11','12','13','21','22','23','31','32','33']


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _text_color(hex_c):
    h = hex_c.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return QColor('#111111') if (r*299+g*587+b*114)/1000 > 155 else QColor('#f5f5f5')


def _resolve_colors(pal_idx, custom_str):
    if pal_idx >= len(PALETTES):
        parts = [c.strip() for c in custom_str.split(',')]
        return parts if len(parts) == 9 else ['#cccccc'] * 9
    return list(PALETTES.values())[pal_idx]


def _make_icon(colors, diamond=False, size=24):
    """Tiny 3×3 preview for the Add-Item toolbar button."""
    px = QPixmap(size, size)
    px.fill(Qt.transparent)
    p  = QPainter(px)
    p.setRenderHint(QPainter.Antialiasing)
    # display order top-left → bottom-right: [6,7,8,3,4,5,0,1,2]
    order = [6, 7, 8, 3, 4, 5, 0, 1, 2]
    cs = size / 3.5
    for i, ci in enumerate(order):
        col_i = i % 3
        row_i = i // 3
        c = QColor(colors[ci])
        if diamond:
            cx = size/2 + (col_i-1)*cs*0.82 - (row_i-1)*cs*0.82
            cy = size/2 + (col_i-1)*cs*0.45 + (row_i-1)*cs*0.45 + cs*0.25
            h  = cs * 0.5
            pts = QPolygonF([QPointF(cx, cy-h), QPointF(cx+h, cy),
                             QPointF(cx, cy+h), QPointF(cx-h, cy)])
            p.setBrush(QBrush(c)); p.setPen(Qt.NoPen); p.drawPolygon(pts)
        else:
            x = col_i*(size/3.1)+1; y = row_i*(size/3.1)+1; w = size/3.1-1.5
            p.fillRect(QRectF(x, y, w, w), QBrush(c))
    p.end()
    return QIcon(px)


# ─────────────────────────────────────────────────────────────────────────────
# Base item — shared state + XML round-trip
# ─────────────────────────────────────────────────────────────────────────────

class _BivariateBaseItem(QgsLayoutItem):

    def __init__(self, layout):
        super().__init__(layout)
        self.setCacheMode(QGraphicsItem.NoCache)
        self._pal_idx     = 6
        self._custom      = ''
        self._cell_size   = 18.0
        self._gap         = 1.5
        self._label_a     = 'Variable A'
        self._label_b     = 'Variable B'
        self._show_labels = False
        self._show_codes  = False
        self._outline_hex = '#4a4a4a'
        self._outline_w   = 0.3
        try:
            self.attemptResize(
                QgsLayoutSize(80, 80, QgsUnitTypes.LayoutMillimeters))
        except Exception:
            pass

    def writePropertiesToElement(self, el, doc, ctx):
        el.setAttribute('palIdx',     str(self._pal_idx))
        el.setAttribute('custom',     self._custom)
        el.setAttribute('cellSize',   str(self._cell_size))
        el.setAttribute('gap',        str(self._gap))
        el.setAttribute('labelA',     self._label_a)
        el.setAttribute('labelB',     self._label_b)
        el.setAttribute('showLabels', str(int(self._show_labels)))
        el.setAttribute('showCodes',  str(int(self._show_codes)))
        el.setAttribute('outlineHex', self._outline_hex)
        el.setAttribute('outlineW',   str(self._outline_w))
        return True

    def readPropertiesFromElement(self, el, doc, ctx):
        self._pal_idx     = int(el.attribute('palIdx',     '6'))
        self._custom      = el.attribute('custom',     '')
        self._cell_size   = float(el.attribute('cellSize',   '18'))
        self._gap         = float(el.attribute('gap',        '1.5'))
        self._label_a     = el.attribute('labelA',     'Variable A')
        self._label_b     = el.attribute('labelB',     'Variable B')
        self._show_labels = bool(int(el.attribute('showLabels', '1')))
        self._show_codes  = bool(int(el.attribute('showCodes',  '0')))
        self._outline_hex = el.attribute('outlineHex', '#4a4a4a')
        self._outline_w   = float(el.attribute('outlineW',   '0.3'))
        return True

    def _colors(self):
        return _resolve_colors(self._pal_idx, self._custom)

    def _pen(self):
        pen = QPen(QColor(self._outline_hex))
        pen.setWidthF(self._outline_w)
        return pen


# ─────────────────────────────────────────────────────────────────────────────
# Box Legend Item
# ─────────────────────────────────────────────────────────────────────────────

class BivariateBoxLegendItem(_BivariateBaseItem):

    def type(self):
        return TYPE_BOX

    def displayName(self):
        return 'Bivariate Box Legend'

    def icon(self):
        return _make_icon(self._colors(), diamond=False)

    def draw(self, ctx):
        painter = ctx.renderContext().painter()
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        scale = ctx.renderContext().scaleFactor()   # px per mm
        cs    = self._cell_size * scale
        gap   = self._gap * scale
        step  = cs + gap

        ml = cs * 0.9 if self._show_labels else gap
        mb = cs * 0.9 if self._show_labels else gap

        pen    = self._pen()
        colors = self._colors()

        af = QFont(); af.setPointSizeF(max(5, self._cell_size * 0.28))
        cf = QFont(); cf.setPointSizeF(max(4, self._cell_size * 0.22)); cf.setBold(True)

        for row in range(3):        # row 0 = top = High B
            for col in range(3):    # col 0 = left = Low A
                b_val = 2 - row
                a_val = col
                code  = f'{a_val+1}{b_val+1}'
                idx   = CODES_ORDER.index(code)
                color = QColor(colors[idx])
                x = ml + col * step
                y = mb + row * step
                painter.fillRect(QRectF(x, y, cs, cs), QBrush(color))
                painter.setPen(pen)
                painter.drawRect(QRectF(x, y, cs, cs))
                if self._show_codes:
                    painter.setFont(cf)
                    painter.setPen(QPen(_text_color(colors[idx])))
                    painter.drawText(QRectF(x, y, cs, cs), Qt.AlignCenter, code)
                    painter.setPen(pen)

        if self._show_labels:
            painter.setFont(af)
            painter.setPen(QPen(QColor('#555555')))
            grid_w = 3*cs + 2*gap
            grid_h = 3*cs + 2*gap
            painter.drawText(
                QRectF(ml, mb + grid_h + gap*0.5, grid_w, cs*0.8),
                Qt.AlignCenter, f'{self._label_a}  →')
            painter.save()
            painter.translate(ml - gap*0.5, mb + grid_h/2)
            painter.rotate(-90)
            painter.drawText(QRectF(-grid_h/2, -cs*0.8, grid_h, cs*0.8),
                             Qt.AlignCenter, f'↑  {self._label_b}')
            painter.restore()

        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# Diamond Legend Item
# ─────────────────────────────────────────────────────────────────────────────

class BivariateDiamondLegendItem(_BivariateBaseItem):

    def type(self):
        return TYPE_DIAMOND

    def displayName(self):
        return 'Bivariate Diamond Legend'

    def icon(self):
        return _make_icon(self._colors(), diamond=True)

    def draw(self, ctx):
        painter = ctx.renderContext().painter()
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        # The painter coordinate system is already in px at scaleFactor px/mm,
        # origin (0,0) = top-left of the item rect.
        # self.rect() is in layout mm — multiply by scaleFactor to get px.
        scale = ctx.renderContext().scaleFactor()   # px per mm
        iw    = self.rect().width()  * scale        # item width  in px
        ih    = self.rect().height() * scale        # item height in px

        cs   = self._cell_size * scale
        gap  = self._gap       * scale
        step = cs + gap
        half = (cs / 2.0) * math.sqrt(2)   # half-diagonal of one diamond
        a45  = math.radians(45)

        # ── Raw centres (origin = col0/row0, no offset) ───────────────────
        def raw(row, col):
            x = col * step * math.cos(a45) - row * step * math.sin(a45)
            y = col * step * math.sin(a45) + row * step * math.cos(a45)
            return x, y

        # ── Bounding box of the 9 diamond shapes ──────────────────────────
        pts   = [raw(r, c) for r in range(3) for c in range(3)]
        min_x = min(p[0] for p in pts) - half
        max_x = max(p[0] for p in pts) + half
        min_y = min(p[1] for p in pts) - half
        max_y = max(p[1] for p in pts) + half
        gw    = max_x - min_x
        gh    = max_y - min_y

        # ── Centre grid in item rect ───────────────────────────────────────
        # Same logic as the box: subtract the raw bbox origin, then pad evenly.
        ox = -min_x + (iw - gw) / 2.0
        oy = -min_y + (ih - gh) / 2.0

        def centre(row, col):
            rx, ry = raw(row, col)
            return rx + ox, ry + oy

        # ── Draw diamonds ─────────────────────────────────────────────────
        colors = self._colors()
        pen    = self._pen()
        cf = QFont(); cf.setPointSizeF(max(4, self._cell_size * 0.22)); cf.setBold(True)
        af = QFont(); af.setPointSizeF(max(5, self._cell_size * 0.28))

        for row in range(3):      # row 0 = Low B (bottom), row 2 = High B (top)
            for col in range(3):  # col 0 = Low A (left),   col 2 = High A (right)
                code  = f'{col+1}{row+1}'
                idx   = CODES_ORDER.index(code)
                color = QColor(colors[idx])
                cx, cy = centre(row, col)

                path = QPainterPath()
                path.moveTo(cx,        cy - half)
                path.lineTo(cx + half, cy)
                path.lineTo(cx,        cy + half)
                path.lineTo(cx - half, cy)
                path.closeSubpath()

                painter.fillPath(path, QBrush(color))
                painter.setPen(pen)
                painter.drawPath(path)

                if self._show_codes:
                    painter.setFont(cf)
                    painter.setPen(QPen(_text_color(colors[idx])))
                    painter.drawText(
                        QRectF(cx - half * 0.6, cy - half * 0.4,
                               half * 1.2,      half * 0.8),
                        Qt.AlignCenter, code)
                    painter.setPen(pen)

        painter.restore()


# ─────────────────────────────────────────────────────────────────────────────
# Item Properties Widget
# ─────────────────────────────────────────────────────────────────────────────

class BivariatePropertiesWidget(QgsLayoutItemBaseWidget):

    def __init__(self, parent, item):
        super().__init__(parent, item)
        self._item     = item
        self._building = False
        self._build_ui()
        self._populate()

    def setNewItem(self, item):
        if item.type() not in (TYPE_BOX, TYPE_DIAMOND):
            return False
        self._item = item
        self._populate()
        return True

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6); root.setSpacing(8)

        g1 = QGroupBox('Palette'); f1 = QFormLayout(g1)
        self._pal_combo = QComboBox(); self._pal_combo.addItems(PALETTE_NAMES)
        f1.addRow('Palette:', self._pal_combo)
        self._custom_edit = QLineEdit()
        self._custom_edit.setPlaceholderText('#hex1,… 9 codes (order 11–33)')
        f1.addRow('Custom colors:', self._custom_edit)
        root.addWidget(g1)

        g2 = QGroupBox('Dimensions (mm)'); f2 = QFormLayout(g2)
        self._cell_spin = QDoubleSpinBox()
        self._cell_spin.setRange(4, 120); self._cell_spin.setSingleStep(1)
        f2.addRow('Cell size:', self._cell_spin)
        self._gap_spin = QDoubleSpinBox()
        self._gap_spin.setRange(0, 20); self._gap_spin.setSingleStep(0.5)
        f2.addRow('Gap:', self._gap_spin)
        root.addWidget(g2)

        g3 = QGroupBox('Labels'); f3 = QFormLayout(g3)
        self._la = QLineEdit(); self._lb = QLineEdit()
        f3.addRow('Variable A:', self._la); f3.addRow('Variable B:', self._lb)
        self._show_lbl_chk = QCheckBox('Show axis labels (box only)')
        self._show_cod_chk = QCheckBox('Show class codes on cells')
        f3.addRow(self._show_lbl_chk); f3.addRow(self._show_cod_chk)
        root.addWidget(g3)

        g4 = QGroupBox('Outline'); f4 = QFormLayout(g4)
        self._out_btn = QPushButton(); self._out_btn.setFixedHeight(24)
        f4.addRow('Color:', self._out_btn)
        self._out_w = QDoubleSpinBox()
        self._out_w.setRange(0, 5); self._out_w.setSingleStep(0.1)
        f4.addRow('Width (mm):', self._out_w)
        root.addWidget(g4)
        root.addStretch()

        self._pal_combo.currentIndexChanged.connect(self._apply)
        self._custom_edit.editingFinished.connect(self._apply)
        self._cell_spin.valueChanged.connect(self._apply)
        self._gap_spin.valueChanged.connect(self._apply)
        self._la.editingFinished.connect(self._apply)
        self._lb.editingFinished.connect(self._apply)
        self._show_lbl_chk.toggled.connect(self._apply)
        self._show_cod_chk.toggled.connect(self._apply)
        self._out_btn.clicked.connect(self._pick_color)
        self._out_w.valueChanged.connect(self._apply)

    def _populate(self):
        self._building = True
        it = self._item
        self._pal_combo.setCurrentIndex(it._pal_idx)
        self._custom_edit.setText(it._custom)
        self._cell_spin.setValue(it._cell_size)
        self._gap_spin.setValue(it._gap)
        self._la.setText(it._label_a); self._lb.setText(it._label_b)
        self._show_lbl_chk.setChecked(it._show_labels)
        self._show_cod_chk.setChecked(it._show_codes)
        self._set_btn_color(it._outline_hex)
        self._out_w.setValue(it._outline_w)
        self._building = False

    def _set_btn_color(self, hex_c):
        self._out_btn.setStyleSheet(
            f'background:{hex_c};border:1px solid #888;border-radius:3px')
        self._out_btn.setText(hex_c)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._item._outline_hex), self)
        if c.isValid():
            self._item._outline_hex = c.name()
            self._set_btn_color(c.name())
            self._item.refresh()

    def _apply(self):
        if self._building:
            return
        it = self._item
        it._pal_idx     = self._pal_combo.currentIndex()
        it._custom      = self._custom_edit.text()
        it._cell_size   = self._cell_spin.value()
        it._gap         = self._gap_spin.value()
        it._label_a     = self._la.text()
        it._label_b     = self._lb.text()
        it._show_labels = self._show_lbl_chk.isChecked()
        it._show_codes  = self._show_cod_chk.isChecked()
        it._outline_w   = self._out_w.value()
        it.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# Core Metadata  (QgsLayoutItemAbstractMetadata)
# Registered via: QgsApplication.layoutItemRegistry().addLayoutItemType(...)
# ─────────────────────────────────────────────────────────────────────────────

class BivariateBoxLegendMetadata(QgsLayoutItemAbstractMetadata):
    def __init__(self):
        super().__init__(TYPE_BOX,
                         QCoreApplication.translate('BivariatePlugin', 'Bivariate Box Legend'))
    def createItem(self, layout):
        return BivariateBoxLegendItem(layout)


class BivariateDiamondLegendMetadata(QgsLayoutItemAbstractMetadata):
    def __init__(self):
        super().__init__(TYPE_DIAMOND,
                         QCoreApplication.translate('BivariatePlugin', 'Bivariate Diamond Legend'))
    def createItem(self, layout):
        return BivariateDiamondLegendItem(layout)


# ─────────────────────────────────────────────────────────────────────────────
# GUI Metadata  (QgsLayoutItemAbstractGuiMetadata)   ← KEY CLASS
# Registered via: QgsGui.layoutItemGuiRegistry().addLayoutItemGuiMetadata(...)
# This is what makes the icon appear in the Add-Item toolbar/menu.
# ─────────────────────────────────────────────────────────────────────────────

class BivariateBoxLegendGuiMetadata(QgsLayoutItemAbstractGuiMetadata):
    def __init__(self):
        super().__init__(TYPE_BOX,
                         QCoreApplication.translate('BivariatePlugin', 'Bivariate Box Legend'))

    def creationIcon(self):             # ← must be creationIcon, NOT icon
        colors = list(PALETTES.values())[6]
        return _make_icon(colors, diamond=False, size=24)

    def createItemWidget(self, item):
        return BivariatePropertiesWidget(None, item)


class BivariateDiamondLegendGuiMetadata(QgsLayoutItemAbstractGuiMetadata):
    def __init__(self):
        super().__init__(TYPE_DIAMOND,
                         QCoreApplication.translate('BivariatePlugin', 'Bivariate Diamond Legend'))

    def creationIcon(self):             # ← must be creationIcon, NOT icon
        colors = list(PALETTES.values())[6]
        return _make_icon(colors, diamond=True, size=24)

    def createItemWidget(self, item):
        return BivariatePropertiesWidget(None, item)
