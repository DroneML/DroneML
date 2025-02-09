from pathlib import Path
from qgis.PyQt import QtWidgets
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
from segmentmytif.main import read_input_and_labels_and_save_predictions
from segmentmytif.features import FeatureType
import logging

# Turn off the logger
logging.getLogger().setLevel(logging.CRITICAL)

FONTSIZE = 16


class DroneMLDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(DroneMLDialog, self).__init__(parent)

        # Set up the dialog window properties
        self.setWindowTitle("DroneML Plugin")
        self.resize(800, 600)

        # Get Qgis Layers
        self.qgis_layers = QgsProject.instance().mapLayers().values()
        self.qgis_layers = _sort_layers(self.qgis_layers)

        # Create a layout to organize widgets in the dialog
        self.layout = QtWidgets.QVBoxLayout()

        # Combo box for raster layers
        # Label
        self.raster_label = QtWidgets.QLabel("Raster layer for training:")
        self.raster_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        self.raster_label.setFixedSize(600, 15)
        self.layout.addWidget(self.raster_label)
        # Combo box
        self.raster_combo = QtWidgets.QComboBox()
        self.raster_combo.setFixedSize(600, 25)
        self._populate_raster_combo(self.raster_combo)
        self.layout.addWidget(self.raster_combo)

        # Combo box for positive label layers
        self.vec_positive_label = QtWidgets.QLabel("Vector layer for positive labels:")
        self.vec_positive_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        self.vec_positive_label.setFixedSize(600, 15)
        self.layout.addWidget(self.vec_positive_label)
        self.vec_positive_combo = QtWidgets.QComboBox()
        self.vec_positive_combo.setFixedSize(600, 25)
        self._populate_vector_combo(self.vec_positive_combo)
        self.layout.addWidget(self.vec_positive_combo)

        # Combo box for negative label layers
        self.vec_negative_label = QtWidgets.QLabel("Vector layer for negative labels:")
        self.vec_negative_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        self.vec_negative_label.setFixedSize(600, 15)
        self.layout.addWidget(self.vec_negative_label)
        self.vec_negative_combo = QtWidgets.QComboBox()
        self.vec_negative_combo.setFixedSize(600, 25)
        self._populate_vector_combo(self.vec_negative_combo)
        self.layout.addWidget(self.vec_negative_combo)

        # Radio buttons for feature type
        self.feature_type_label = QtWidgets.QLabel("Feature type:")
        self.feature_type_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        self.feature_type_label.setFixedSize(600, 15)
        self.layout.addWidget(self.feature_type_label)
        self.feature_type_group = QtWidgets.QButtonGroup(self)
        self.feature_type_layout = QtWidgets.QHBoxLayout()
        self.feature_type_flair = QtWidgets.QRadioButton("FLAIR")
        self.feature_type_flair.setChecked(True)
        self.feature_type_identical = QtWidgets.QRadioButton("IDENTITY")
        self.feature_type_group.addButton(self.feature_type_flair)
        self.feature_type_group.addButton(self.feature_type_identical)
        self.feature_type_layout.addWidget(self.feature_type_flair)
        self.feature_type_layout.addWidget(self.feature_type_identical)
        self.layout.addLayout(self.feature_type_layout)

        # Radio buttons for compute mode
        self.compute_mode_label = QtWidgets.QLabel("Compute mode:")
        self.compute_mode_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        self.compute_mode_label.setFixedSize(600, 15)
        self.layout.addWidget(self.compute_mode_label)
        self.compute_mode_group = QtWidgets.QButtonGroup(self)
        self.compute_mode_layout = QtWidgets.QHBoxLayout()
        self.compute_mode_normal = QtWidgets.QRadioButton("Normal")
        self.compute_mode_normal.setChecked(True)
        self.compute_mode_parallel = QtWidgets.QRadioButton("Parallel")
        self.compute_mode_safe = QtWidgets.QRadioButton("Safe")
        self.compute_mode_group.addButton(self.compute_mode_normal)
        self.compute_mode_group.addButton(self.compute_mode_parallel)
        self.compute_mode_group.addButton(self.compute_mode_safe)
        self.compute_mode_layout.addWidget(self.compute_mode_normal)
        self.compute_mode_layout.addWidget(self.compute_mode_parallel)
        self.compute_mode_layout.addWidget(self.compute_mode_safe)
        self.layout.addLayout(self.compute_mode_layout)

        # Advanced Options
        self.advanced_group_box = QtWidgets.QGroupBox("Advanced Options")
        self.advanced_group_box.setCheckable(True)
        self.advanced_group_box.setChecked(False)
        self.advanced_group_box.setMaximumHeight(200)
        self.advanced_layout = QtWidgets.QVBoxLayout()

        # Chunk size
        self.chunk_size_label = QtWidgets.QLabel("Chunk size:")
        self.chunk_size_spinbox = QtWidgets.QSpinBox()
        self.chunk_size_spinbox.setRange(250, 10000)
        self.chunk_size_spinbox.setValue(100)
        self.advanced_layout.addWidget(self.chunk_size_label)
        self.advanced_layout.addWidget(self.chunk_size_spinbox)

        # Overlap size
        self.overlap_size_label = QtWidgets.QLabel("Overlap size:")
        self.overlap_size_spinbox = QtWidgets.QSpinBox()
        self.overlap_size_spinbox.setRange(0, 1000)
        self.overlap_size_spinbox.setValue(25)
        self.advanced_layout.addWidget(self.overlap_size_label)
        self.advanced_layout.addWidget(self.overlap_size_spinbox)

        self.advanced_group_box.setLayout(self.advanced_layout)
        self.layout.addWidget(self.advanced_group_box)

        # Create a horizontal layout for buttons (zoom in/out and load raster)
        button_layout = QtWidgets.QHBoxLayout()

        # Add run button
        run_button = QtWidgets.QPushButton("run")
        run_button.clicked.connect(self.run_classification)
        run_button.setFixedSize(64, 32)
        button_layout.addWidget(run_button)

        # Add the button layout to the main layout
        self.layout.addLayout(button_layout)

        # Set the layout to the dialog
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

    def run_classification(self):
        """Run the classification algorithm."""

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
        print(f"Raster Layer: {raster_path}")
        print(f"Positive Vector Layer: {pos_labels_path}")
        print(f"Negative Vector Layer: {neg_labels_path}")

        # Get Feture Type
        feature_type = (
            FeatureType.FLAIR
            if self.feature_type_flair.isChecked()
            else FeatureType.IDENTITY
        )
        print(f"Feature Type: {feature_type}")

        # Get Compute Mode
        if self.compute_mode_normal.isChecked():
            compute_mode = "normal"
        elif self.compute_mode_parallel.isChecked():
            compute_mode = "parallel"
        else:
            compute_mode = "safe"
        print(f"Compute Mode: {compute_mode}")

        # Get chunk size and overlap size
        if self.advanced_group_box.isChecked():
            chunk_size = self.chunk_size_spinbox.value()
            overlap_size = self.overlap_size_spinbox.value()
            print(f"Chunk Size: {chunk_size}")
            print(f"Overlap Size: {overlap_size}")
        else:
            chunk_size = None
            overlap_size = None

        prediction_tif = read_input_and_labels_and_save_predictions(
            raster_path,
            pos_labels_path,
            neg_labels_path,
            output_path=raster_path.parent.parent / "prediction.tif",
            feature_type=feature_type,
            compute_mode=compute_mode,
            chunks=chunk_size,
            chunk_overlap=overlap_size,
        )

        # Add the new raster layer to QGIS

        new_raster_layer = QgsRasterLayer(prediction_tif.as_posix(), "prediction")
        if not new_raster_layer.isValid():
            print("Failed to load the raster layer!")
        else:
            QgsProject.instance().addMapLayer(new_raster_layer)

    def _populate_raster_combo(self, combo_box):
        """Populate the raster combo box with the loaded raster layers."""

        # Get the list of layers in the current QGIS project
        for layer in self.qgis_layers:
            if isinstance(layer, QgsRasterLayer):
                self.raster_combo.addItem(layer.name())

    def _populate_vector_combo(self, combo_box):
        """Poluate the vector combo box with the loaded vector layers."""

        # Get the list of layers in the current QGIS project
        for layer in self.qgis_layers:
            if isinstance(layer, QgsVectorLayer):
                combo_box.addItem(layer.name())


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
