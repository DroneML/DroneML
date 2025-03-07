import logging
from pathlib import Path
import os
import inspect
from qgis.PyQt import QtWidgets, QtCore, QtGui
from qgis.PyQt.QtCore import QThread, pyqtSignal, QMutex
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
from segmentmytif.main import read_input_and_labels_and_save_predictions
from segmentmytif.features import FeatureType
from .utils import (
    HTEXT_OUTPUT_PATH,
    HTEXT_INPUT_RSASTER,
    HTEXT_INPUT_POS_VEC,
    HTEXT_INPUT_NEG_VEC,
    HTEXT_FEATURE_TYPE,
    HTEXT_COMPUTE_MODE,
    HTEXT_COMPUTE_MODE_NORMAL,
    HTEXT_COMPUTE_MODE_PARALLEL,
    HTEXT_COMPUTE_MODE_SAFE,
    HTEXT_CHUNK_SIZE,
    HTEXT_OVERLAP_SIZE,
    QgisLogHandler,
    DialogLoggerHandler,
)

# Constants
FONTSIZE = 16  # Font size for the labels
LABEL_HEIGHT = 20  # Height of the labels
WIDGET_WIDTH = 600  # Width of all the widgets
WIDGET_HEIGHT = 20  # Height of all non-label widgets
HELP_ICON_SIZE = 12  # Size of the help icon

# Get current folder
cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]


class DroneMLDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(DroneMLDialog, self).__init__(parent)

        # Set up the dialog window properties
        self.setWindowTitle("DroneML Plugin")
        self.resize(800, 700)

        # Get Qgis Layers
        self.qgis_layers = QgsProject.instance().mapLayers().values()
        self.qgis_layers = _sort_layers(self.qgis_layers)

        # Create a layout to organize widgets in the dialog
        self.layout = QtWidgets.QVBoxLayout()

        # Add input for output path of the prediction
        # Horizontal layout for output path and button
        output_label_layout, self.output_path_line_edit, browse_button = (
            self._get_output_path_input_elements(HTEXT_OUTPUT_PATH)
        )

        self.layout.addLayout(output_label_layout)
        self.output_path_layout = QtWidgets.QHBoxLayout()
        self.output_path_layout.addWidget(self.output_path_line_edit)
        self.output_path_layout.addWidget(browse_button)
        self.output_path_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.layout.addLayout(self.output_path_layout)

        # Add a separator
        self._add_separator()

        # Add raster layer combo box
        raster_label_layout, self.raster_combo = self._get_combo_box(
            "Raster layer for training:",
            HTEXT_INPUT_RSASTER,
            self._populate_raster_combo,
        )
        self.layout.addLayout(raster_label_layout)
        self.layout.addWidget(self.raster_combo)

        # Add positive label vector layer combo box
        pos_label_layout, self.vec_positive_combo = self._get_combo_box(
            "Vector layer for positive labels:",
            HTEXT_INPUT_POS_VEC,
            self._populate_vector_combo,
        )
        self.layout.addLayout(pos_label_layout)
        self.layout.addWidget(self.vec_positive_combo)

        # Add negative label vector layer combo box
        neg_label_layout, self.vec_negative_combo = self._get_combo_box(
            "Vector layer for negative labels:",
            HTEXT_INPUT_NEG_VEC,
            self._populate_vector_combo,
        )
        self.layout.addLayout(neg_label_layout)
        self.layout.addWidget(self.vec_negative_combo)

        # Add radio buttons for feature type
        feature_label_layout, self.feature_type_group, self.feature_type_layout = (
            self._get_radio_buttons(
                "Feature type:", HTEXT_FEATURE_TYPE, ["FLAIR", "IDENTITY"], "FLAIR"
            )
        )
        self.layout.addLayout(feature_label_layout)
        self.layout.addLayout(self.feature_type_layout)

        # Add radio buttons for compute mode
        compute_label_layout, self.compute_mode_group, self.compute_mode_layout = (
            self._get_radio_buttons_with_helptext(
                "Compute mode:",
                HTEXT_COMPUTE_MODE,
                ["Normal", "Parallel", "Safe"],
                [
                    HTEXT_COMPUTE_MODE_NORMAL,
                    HTEXT_COMPUTE_MODE_PARALLEL,
                    HTEXT_COMPUTE_MODE_SAFE,
                ],
                "Normal",
            )
        )
        self.layout.addLayout(compute_label_layout)
        self.layout.addLayout(self.compute_mode_layout)

        # Add a separator
        self._add_separator()

        # Add advanced options
        self._add_advanced_options()

        # Add run button
        button_layout = QtWidgets.QHBoxLayout()
        run_button = QtWidgets.QPushButton("run")
        run_button.clicked.connect(self.start_classification)
        run_button.setFixedSize(64, 32)
        button_layout.addWidget(run_button)

        # Add the button layout to the main layout
        self.layout.addLayout(button_layout)

        # Add a separator
        self._add_separator()

        # Add log window
        self.log_window_handler = DialogLoggerHandler(self)
        self.log_window_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        self.layout.addWidget(self.log_window_handler.widget)

        # Set the layout to the dialog
        self.layout.setSpacing(5)
        self.setLayout(self.layout)

        # Initialize the job thread
        self.job = None

    def _add_separator(self):
        """Add a separator to the layout."""
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        self.layout.addWidget(separator)

    def _browse_output_path(self):
        """Browse for the output path of the prediction."""
        output_path = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Prediction", "", "TIFF Files (*.tif)"
        )
        if output_path[0]:
            self.output_path_line_edit.setText(output_path[0])

    def _get_output_path_input_elements(self, help_text):
        """Elements for the output path input."""
        # Label
        output_label = QtWidgets.QLabel("Output path for prediction:")
        output_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        output_label.setFixedHeight(LABEL_HEIGHT)
        help_icon = _get_help_icon(help_text)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(output_label)
        label_layout.addWidget(help_icon)
        label_layout.setAlignment(QtCore.Qt.AlignLeft)

        # Get output path
        # Default output path is the parent directory of the raster layer
        output_path_line_edit = QtWidgets.QLineEdit()
        output_path_line_edit.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)
        output_path = Path()
        for layer in self.qgis_layers:
            if isinstance(layer, QgsRasterLayer):
                output_path = Path(layer.source()).parent / "prediction.tif"
        output_path_line_edit.setText(output_path.as_posix())

        # Add a button to browse for the output path
        browse_button = QtWidgets.QPushButton("...")
        browse_button.clicked.connect(self._browse_output_path)
        browse_button.setFixedSize(32, WIDGET_HEIGHT)

        return label_layout, output_path_line_edit, browse_button

    def _get_combo_box(self, label_text, help_text, populate_function):
        """Add a combo box with a label to the layout."""
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        label.setFixedHeight(LABEL_HEIGHT)
        help_icon = _get_help_icon(help_text)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(label)
        label_layout.addWidget(help_icon)
        label_layout.setAlignment(QtCore.Qt.AlignLeft)

        combo_box = QtWidgets.QComboBox()
        combo_box.setFixedSize(WIDGET_WIDTH, WIDGET_HEIGHT)
        populate_function(combo_box)

        return label_layout, combo_box

    def _get_radio_buttons(
        self, label_text, help_text, options, default_option, option_texts=None
    ):
        """Add a set of radio buttons with a label to the layout."""
        # Label text and help icon next to it
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        label.setFixedHeight(LABEL_HEIGHT)
        help_icon = _get_help_icon(help_text)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(label)
        label_layout.addWidget(help_icon)
        label_layout.setAlignment(QtCore.Qt.AlignLeft)
        button_group = QtWidgets.QButtonGroup(self)
        layout = QtWidgets.QHBoxLayout()
        for option in options:
            radio_button = QtWidgets.QRadioButton(option)
            if option == default_option:
                radio_button.setChecked(True)
            button_group.addButton(radio_button)
            layout.addWidget(radio_button)
        return label_layout, button_group, layout

    def _get_radio_buttons_with_helptext(
        self, label_text, help_text, options, option_texts, default_option
    ):
        """Add a set of radio buttons with a label to the layout, and help text for each option."""
        # Label text and help icon next to it
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        label.setFixedHeight(LABEL_HEIGHT)
        help_icon = _get_help_icon(help_text)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        label_layout = QtWidgets.QHBoxLayout()
        label_layout.addWidget(label)
        label_layout.addWidget(help_icon)
        label_layout.setAlignment(QtCore.Qt.AlignLeft)
        button_group = QtWidgets.QButtonGroup(self)
        layout = QtWidgets.QHBoxLayout()
        for option, op_help_text in zip(options, option_texts):
            radio_button_with_help = RadioButtonWithHelp(option, op_help_text)
            if option == default_option:
                radio_button_with_help.radio_button.setChecked(True)
            button_group.addButton(radio_button_with_help.radio_button)
            layout.addWidget(radio_button_with_help)
        return label_layout, button_group, layout

    def _add_advanced_options(self):
        """Add advanced options section to the layout."""
        self.advanced_group_box = QtWidgets.QGroupBox("Advanced Options")
        self.advanced_group_box.setCheckable(True)
        self.advanced_group_box.setChecked(False)
        self.advanced_group_box.setMaximumHeight(150)
        self.advanced_layout = QtWidgets.QVBoxLayout()

        # Chunk size
        chunk_size_label = QtWidgets.QLabel("Chunk size:")
        chunk_size_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        chunk_size_label.setFixedHeight(LABEL_HEIGHT)
        help_icon = _get_help_icon(HTEXT_CHUNK_SIZE)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        chunk_size_label_layout = QtWidgets.QHBoxLayout()
        chunk_size_label_layout.addWidget(chunk_size_label)
        chunk_size_label_layout.addWidget(help_icon)
        chunk_size_label_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.chunk_size_spinbox = QtWidgets.QSpinBox()
        self.chunk_size_spinbox.setRange(500, 10000)
        self.chunk_size_spinbox.setValue(100)
        self.advanced_layout.addLayout(chunk_size_label_layout)
        self.advanced_layout.addWidget(self.chunk_size_spinbox)

        # Overlap size
        overlap_size_label = QtWidgets.QLabel("Overlap size:")
        overlap_size_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        overlap_size_label.setFixedHeight(LABEL_HEIGHT)
        help_icon = _get_help_icon(HTEXT_OVERLAP_SIZE)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        overlap_size_label_layout = QtWidgets.QHBoxLayout()
        overlap_size_label_layout.addWidget(overlap_size_label)
        overlap_size_label_layout.addWidget(help_icon)
        overlap_size_label_layout.setAlignment(QtCore.Qt.AlignLeft)
        self.overlap_size_spinbox = QtWidgets.QSpinBox()
        self.overlap_size_spinbox.setRange(0, 1000)
        self.overlap_size_spinbox.setValue(25)
        self.advanced_layout.addLayout(overlap_size_label_layout)
        self.advanced_layout.addWidget(self.overlap_size_spinbox)

        self.advanced_group_box.setLayout(self.advanced_layout)
        self.layout.addWidget(self.advanced_group_box)

    def run_classification(self):
        """Run the classification algorithm."""

        # Configure logger
        logger = self._get_logger()

        # Get the output path
        output_path = Path(self.output_path_line_edit.text())

        # Get file paths of the selected layers
        raster_path = Path(
            QgsProject.instance()
            .mapLayersByName(self.raster_combo.currentText())[0]
            .source()
        )
        pos_labels_path = Path(
            QgsProject.instance()
            .mapLayersByName(self.vec_positive_combo.currentText())[0]
            .source()
        )
        neg_labels_path = Path(
            QgsProject.instance()
            .mapLayersByName(self.vec_negative_combo.currentText())[0]
            .source()
        )
        logger.info(f"Raster Layer: {raster_path}")
        logger.info(f"Positive Vector Layer: {pos_labels_path}")
        logger.info(f"Negative Vector Layer: {neg_labels_path}")

        # Get Feature Type
        feature_type = (
            FeatureType.FLAIR
            if self.feature_type_group.buttons()[0].isChecked()
            else FeatureType.IDENTITY
        )
        logger.info(f"Feature Type: {feature_type}")

        # Get Compute Mode
        if self.compute_mode_group.buttons()[0].isChecked():
            compute_mode = "normal"
        elif self.compute_mode_group.buttons()[1].isChecked():
            compute_mode = "parallel"
        else:
            compute_mode = "safe"
        logger.info(f"Compute Mode: {compute_mode}")

        # Get chunk size and overlap size
        if self.advanced_group_box.isChecked():
            chunk_size = self.chunk_size_spinbox.value()
            overlap_size = self.overlap_size_spinbox.value()
            logger.info(f"Chunk Size: {chunk_size}")
            logger.info(f"Overlap Size: {overlap_size}")
        else:
            chunk_size = None
            overlap_size = None

        prediction_tif = read_input_and_labels_and_save_predictions(
            raster_path,
            pos_labels_path,
            neg_labels_path,
            output_path=output_path,
            feature_type=feature_type,
            compute_mode=compute_mode,
            chunks=chunk_size,
            chunk_overlap=overlap_size,
            logger_root=logger,
        )

        # Add the new raster layer to QGIS
        new_raster_layer = QgsRasterLayer(prediction_tif.as_posix(), "prediction")
        if not new_raster_layer.isValid():
            logger.error("Failed to load the raster layer!")
        else:
            QgsProject.instance().addMapLayer(new_raster_layer)

    def _get_logger(self):
        # Configure logger
        logger = logging.getLogger(__name__)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        # QGIS log handler
        qgis_handler = QgisLogHandler()
        qgis_handler.setLevel(logging.INFO)
        qgis_handler.setFormatter(formatter)

        # Get the output path
        output_path = Path(self.output_path_line_edit.text())

        # File handler INFO
        file_handler_info = logging.FileHandler(
            f"{output_path.with_suffix('.info.log')}"
        )
        file_handler_info.setLevel(logging.INFO)
        file_handler_info.setFormatter(formatter)

        # File handler DEBUG
        file_handler_debug = logging.FileHandler(
            f"{output_path.with_suffix('.debug.log')}"
        )
        file_handler_debug.setLevel(logging.DEBUG)
        file_handler_debug.setFormatter(formatter)

        # Add the handlers to the logger
        logger.addHandler(qgis_handler)
        logger.addHandler(file_handler_info)
        logger.addHandler(file_handler_debug)
        logger.addHandler(self.log_window_handler)

        return logger

    def start_classification(self):
        """Start the classification process in a separate thread."""
        self.job = ClassificationJob(self)
        self.job.log_signal.connect(self.log_message)
        self.job.start()

    def closeEvent(self, event):
        """Handle the dialog close event."""
        if self.job and self.job.isRunning():
            self.job.terminate()
            self.job.wait()
        event.accept()

    def log_message(self, message):
        """Log a message to the log window."""
        self.log_window_handler.widget.appendPlainText(message)

    def _populate_raster_combo(self, combo_box):
        """Populate the raster combo box with the loaded raster layers."""
        for layer in self.qgis_layers:
            if isinstance(layer, QgsRasterLayer):
                combo_box.addItem(layer.name())

    def _populate_vector_combo(self, combo_box):
        """Populate the vector combo box with the loaded vector layers."""
        for layer in self.qgis_layers:
            if isinstance(layer, QgsVectorLayer):
                combo_box.addItem(layer.name())


def _get_help_icon(text: str):
    """Create a help button with the given text."""
    help_icon = QtWidgets.QLabel()
    pixmap = QtGui.QPixmap(os.path.join(cmd_folder, "help_icon.svg"))
    scaled_pixmap = pixmap.scaled(
        HELP_ICON_SIZE,
        HELP_ICON_SIZE,
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )
    help_icon.setPixmap(scaled_pixmap)
    help_icon.setToolTip(text)
    return help_icon


def _sort_layers(layers):
    """Get all layers sorted by active layers first."""
    layer_tree_root = QgsProject.instance().layerTreeRoot()

    # Separate active and inactive layers
    active_layers = []
    inactive_layers = []
    for layer in layers:
        if layer_tree_root.findLayer(layer.id()).isVisible():
            active_layers.append(layer)
        else:
            inactive_layers.append(layer)

    # Combine active layers first, then inactive layers
    sorted_layers = active_layers + inactive_layers
    return sorted_layers


class RadioButtonWithHelp(QtWidgets.QWidget):
    """A widget that contains a radio button and a help icon."""

    def __init__(self, text, help_text, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        self.radio_button = QtWidgets.QRadioButton(text)
        help_icon = _get_help_icon(help_text)
        help_icon.setFixedSize(HELP_ICON_SIZE, HELP_ICON_SIZE)
        layout.addWidget(self.radio_button)
        layout.addWidget(help_icon)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(QtCore.Qt.AlignLeft)
        self.setLayout(layout)
        self.setFixedHeight(LABEL_HEIGHT)


class ClassificationJob(QThread):
    log_signal = pyqtSignal(str)

    def __init__(self, dialog):
        super().__init__()
        self.dialog = dialog
        self.mutex = QMutex()

    def run(self):
        try:
            self.dialog.run_classification()
        except Exception as e:
            self.log_signal.emit(f"Error: {str(e)}")