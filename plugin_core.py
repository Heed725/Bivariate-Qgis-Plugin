from qgis.core import QgsApplication
from qgis.gui  import QgsGui

from .bivariate_provider import BivariateProvider
from .layout_items import (
    TYPE_BOX, TYPE_DIAMOND, TYPE_BOX_RAMPS, TYPE_RAMPS,
    BivariateBoxLegendMetadata,
    BivariateDiamondLegendMetadata,
    BivariateBoxRampsLegendMetadata,
    BivariateRampsLegendMetadata,
    BivariateBoxLegendGuiMetadata,
    BivariateDiamondLegendGuiMetadata,
    BivariateBoxRampsLegendGuiMetadata,
    BivariateRampsLegendGuiMetadata,
)


class BivariatePlugin:

    def __init__(self, iface):
        self.iface    = iface
        self.provider = None
        self.box_item_metadata         = None
        self.diamond_item_metadata     = None
        self.box_ramps_item_metadata   = None
        self.ramps_item_metadata       = None
        self.box_item_gui_metadata     = None
        self.diamond_item_gui_metadata = None
        self.box_ramps_item_gui_metadata = None
        self.ramps_item_gui_metadata     = None

        # ── Core registry: guard against duplicate (plugin reload) ────────
        core_reg = QgsApplication.layoutItemRegistry()
        if core_reg.itemMetadata(TYPE_BOX) is None:
            self.box_item_metadata = BivariateBoxLegendMetadata()
            core_reg.addLayoutItemType(self.box_item_metadata)
        if core_reg.itemMetadata(TYPE_DIAMOND) is None:
            self.diamond_item_metadata = BivariateDiamondLegendMetadata()
            core_reg.addLayoutItemType(self.diamond_item_metadata)
        if core_reg.itemMetadata(TYPE_BOX_RAMPS) is None:
            self.box_ramps_item_metadata = BivariateBoxRampsLegendMetadata()
            core_reg.addLayoutItemType(self.box_ramps_item_metadata)
        if core_reg.itemMetadata(TYPE_RAMPS) is None:
            self.ramps_item_metadata = BivariateRampsLegendMetadata()
            core_reg.addLayoutItemType(self.ramps_item_metadata)

    def initProcessing(self):
        self.provider = BivariateProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

        # ── GUI registry: guard against duplicate (plugin reload) ─────────
        # QgsLayoutItemGuiRegistry has no itemGuiMetadata(type) lookup in
        # PyQGIS, so we use a module-level sentinel to detect duplicates.
        gui_reg = QgsGui.layoutItemGuiRegistry()

        if not _gui_registered(TYPE_BOX):
            self.box_item_gui_metadata = BivariateBoxLegendGuiMetadata()
            gui_reg.addLayoutItemGuiMetadata(self.box_item_gui_metadata)
            _mark_gui_registered(TYPE_BOX)

        if not _gui_registered(TYPE_DIAMOND):
            self.diamond_item_gui_metadata = BivariateDiamondLegendGuiMetadata()
            gui_reg.addLayoutItemGuiMetadata(self.diamond_item_gui_metadata)
            _mark_gui_registered(TYPE_DIAMOND)

        if not _gui_registered(TYPE_BOX_RAMPS):
            self.box_ramps_item_gui_metadata = BivariateBoxRampsLegendGuiMetadata()
            gui_reg.addLayoutItemGuiMetadata(self.box_ramps_item_gui_metadata)
            _mark_gui_registered(TYPE_BOX_RAMPS)

        if not _gui_registered(TYPE_RAMPS):
            self.ramps_item_gui_metadata = BivariateRampsLegendGuiMetadata()
            gui_reg.addLayoutItemGuiMetadata(self.ramps_item_gui_metadata)
            _mark_gui_registered(TYPE_RAMPS)

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        # Mark GUI slots as unregistered so next load re-registers cleanly.
        # (QgsLayoutItemGuiRegistry has no PyQGIS remove API — entries persist
        # until QGIS restarts, but the guard prevents accumulation.)
        _clear_gui_registered()


# ── Module-level set: tracks which TYPE_* ids we have registered this session.
# Survives plugin reload because Python module state persists in QGIS's process.
_GUI_REGISTERED: set = set()

def _gui_registered(type_id: int) -> bool:
    return type_id in _GUI_REGISTERED

def _mark_gui_registered(type_id: int):
    _GUI_REGISTERED.add(type_id)

def _clear_gui_registered():
    _GUI_REGISTERED.clear()
