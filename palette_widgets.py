"""Palette preview icons shared by Processing and Print Layout."""

from qgis.PyQt.QtCore import QSize, Qt, QRectF
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPixmap
from qgis.PyQt.QtWidgets import QComboBox
from qgis.core import QgsProcessingParameterEnum

from .palettes import PALETTES


CUSTOM_PALETTE_NAME = 'Custom / Staridas import'
CUSTOM_PREVIEW_COLORS = [
    '#E8E8E8', '#DFB0D6', '#BE64AC',
    '#ACE4E4', '#A5ADD3', '#8C62AA',
    '#5AC8C8', '#5698B9', '#3B4994',
]


def palette_preview_icon(colors, size=30):
    """Return a square 3x3 icon in the same orientation as the box legend."""
    colors = list(colors)
    if len(colors) != 9:
        colors = CUSTOM_PREVIEW_COLORS

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, False)

    margin = 1.0
    gap = 0.5
    cell = (size - 2 * margin - 2 * gap) / 3.0
    for row in range(3):
        for col in range(3):
            # PALETTES are X-major with Y increasing bottom-to-top.
            color_index = col * 3 + (2 - row)
            painter.fillRect(
                QRectF(
                    margin + col * (cell + gap),
                    margin + row * (cell + gap),
                    cell,
                    cell,
                ),
                QColor(colors[color_index]),
            )
    painter.end()
    return QIcon(pixmap)


def populate_palette_combo(combo, names, icon_size=30):
    """Populate ``combo`` with palette names and colour-grid thumbnails."""
    combo.clear()
    combo.setIconSize(QSize(icon_size, icon_size))
    combo.setMinimumContentsLength(18)
    for name in names:
        colors = PALETTES.get(name, CUSTOM_PREVIEW_COLORS)
        combo.addItem(palette_preview_icon(colors, icon_size), name)
        combo.setItemData(combo.count() - 1, name, Qt.ToolTipRole)
    return combo


def make_palette_parameter(name, description, options, defaultValue=0, optional=False):
    """Create a normal enum with QGIS-native per-option preview icons."""
    parameter = QgsProcessingParameterEnum(
        name,
        description,
        options=options,
        defaultValue=defaultValue,
        optional=optional,
    )
    icons = [
        palette_preview_icon(PALETTES.get(option, CUSTOM_PREVIEW_COLORS))
        for option in options
    ]
    parameter.setMetadata({
        'widget_wrapper': {'icons': icons}
    })
    return parameter
