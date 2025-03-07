import logging
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt import QtWidgets

# Help text for the dialog
HTEXT_OUTPUT_PATH = "The output path where the prediction will be saved."
HTEXT_INPUT_RSASTER = "The input raster layer in your QGIS project that will be used for training the model."
HTEXT_INPUT_POS_VEC = (
    "The input vector layer in your QGIS project for positive labels.\n"
    "Should be polygon or multi-polygons."
)
HTEXT_INPUT_NEG_VEC = (
    "The input vector layer in your QGIS project for negative labels.\n"
    "Should be polygon or multi-polygons."
)
HTEXT_FEATURE_TYPE = (
    "The feature type of the input vector layer. By default FLAIR.\n"
    "IDENTITY means use the original raster layer as the feature."
)
HTEXT_COMPUTE_MODE = "The mode of computation."
HTEXT_COMPUTE_MODE_NORMAL = (
    "Normal: read in all the data and perform the computation.\n"
    "Suitable for small datasets that fits in memory."
)
HTEXT_COMPUTE_MODE_PARALLEL = (
    "Parallel: read in data in chunks and perform the computation with several chunks together.\n"
    "Suitable for medium-sized datasets, where we assume several chunks can fit in memory."
)
HTEXT_COMPUTE_MODE_SAFE = (
    "Safe: read in data in chunks, perform the computation with one chunk at a time.\n"
    "Suitable for large datasets that do not fit in memory."
)
HTEXT_CHUNK_SIZE = (
    "The size of the chunk to be read in. Only used in Parallel and Safe mode."
)
HTEXT_OVERLAP_SIZE = (
    "The overlap between chunks when performing feature extraction. Only used in Parallel and Safe mode.\n"
    "Because of possible edge effects, a minimum overlap of 20 is recommended."
)


# Custom logging handler for QGIS
class QgisLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        msg = self.format(record)
        QgsMessageLog.logMessage(msg, "DroneML", Qgis.Info)

class DialogLoggerHandler(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)
