from pathlib import Path
from qgis.PyQt import QtWidgets, QtCore
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

        # Add input for output path of the prediction
        # Horizontal layout for output path and button
        output_label, self.output_path_line_edit, browse_button = (
            self._get_output_path_input_elements()
        )
        self.layout.addWidget(output_label)
        self.output_path_layout = QtWidgets.QHBoxLayout()
        self.output_path_layout.addWidget(self.output_path_line_edit)
        self.output_path_layout.addWidget(browse_button)
        self.output_path_layout.setAlignment(QtCore.Qt.AlignLeft) 
        self.layout.addLayout(self.output_path_layout)

        # Add raster layer combo box
        raster_label, self.raster_combo = self._get_combo_box(
            "Raster layer for training:", self._populate_raster_combo
        )
        self.layout.addWidget(raster_label)
        self.layout.addWidget(self.raster_combo)

        # Add positive label vector layer combo box
        pos_label, self.vec_positive_combo = self._get_combo_box(
            "Vector layer for positive labels:", self._populate_vector_combo
        )
        self.layout.addWidget(pos_label)
        self.layout.addWidget(self.vec_positive_combo)

        # Add negative label vector layer combo box
        neg_label, self.vec_negative_combo = self._get_combo_box(
            "Vector layer for negative labels:", self._populate_vector_combo
        )
        self.layout.addWidget(neg_label)
        self.layout.addWidget(self.vec_negative_combo)

        # Add radio buttons for feature type
        feature_label, self.feature_type_group, self.feature_type_layout = (
            self._get_radio_buttons("Feature type:", ["FLAIR", "IDENTITY"], "FLAIR")
        )
        self.layout.addWidget(feature_label)
        self.layout.addLayout(self.feature_type_layout)

        # Add radio buttons for compute mode
        compute_label, self.compute_mode_group, self.compute_mode_layout = (
            self._get_radio_buttons(
                "Compute mode:", ["Normal", "Parallel", "Safe"], "Normal"
            )
        )
        self.layout.addWidget(compute_label)
        self.layout.addLayout(self.compute_mode_layout)

        # Add advanced options
        self._add_advanced_options()

        # Add run button
        button_layout = QtWidgets.QHBoxLayout()
        run_button = QtWidgets.QPushButton("run")
        run_button.clicked.connect(self.run_classification)
        run_button.setFixedSize(64, 32)
        button_layout.addWidget(run_button)

        # Add the button layout to the main layout
        self.layout.addLayout(button_layout)

        # Set the layout to the dialog
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

    def _browse_output_path(self):
        """Browse for the output path of the prediction."""
        output_path = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save Prediction", "", "TIFF Files (*.tif)"
        )
        if output_path[0]:
            self.output_path_line_edit.setText(output_path[0])

    def _get_output_path_input_elements(self):
        """Elements for the output path input."""
        # Label
        output_label = QtWidgets.QLabel("Output path for prediction:")
        output_label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        output_label.setFixedSize(600, 15)

        # Get output path
        # Default output path is the parent directory of the raster layer
        output_path_line_edit = QtWidgets.QLineEdit()
        output_path_line_edit.setFixedSize(600, 25)
        for layer in self.qgis_layers:
            if isinstance(layer, QgsRasterLayer):
                output_path = Path(layer.source()).parent / "prediction.tif"
        output_path_line_edit.setText(output_path.as_posix())

        # Add a button to browse for the output path
        browse_button = QtWidgets.QPushButton("...")
        browse_button.clicked.connect(self._browse_output_path)
        browse_button.setFixedSize(32, 25)

        return output_label, output_path_line_edit, browse_button

    def _get_combo_box(self, label_text, populate_function):
        """Add a combo box with a label to the layout."""
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        label.setFixedSize(600, 15)

        combo_box = QtWidgets.QComboBox()
        combo_box.setFixedSize(600, 25)
        populate_function(combo_box)

        return label, combo_box

    def _get_radio_buttons(self, label_text, options, default_option):
        """Add a set of radio buttons with a label to the layout."""
        label = QtWidgets.QLabel(label_text)
        label.setStyleSheet(f"font-size: {FONTSIZE}px;")
        label.setFixedSize(600, 15)
        button_group = QtWidgets.QButtonGroup(self)
        layout = QtWidgets.QHBoxLayout()
        for option in options:
            radio_button = QtWidgets.QRadioButton(option)
            if option == default_option:
                radio_button.setChecked(True)
            button_group.addButton(radio_button)
            layout.addWidget(radio_button)
        return label, button_group, layout

    def _add_advanced_options(self):
        """Add advanced options section to the layout."""
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

    def run_classification(self):
        """Run the classification algorithm."""

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
        print(f"Raster Layer: {raster_path}")
        print(f"Positive Vector Layer: {pos_labels_path}")
        print(f"Negative Vector Layer: {neg_labels_path}")

        # Get Feature Type
        feature_type = (
            FeatureType.FLAIR
            if self.feature_type_group.buttons()[0].isChecked()
            else FeatureType.IDENTITY
        )
        print(f"Feature Type: {feature_type}")

        # Get Compute Mode
        if self.compute_mode_group.buttons()[0].isChecked():
            compute_mode = "normal"
        elif self.compute_mode_group.buttons()[1].isChecked():
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
            output_path=output_path,
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
        for layer in self.qgis_layers:
            if isinstance(layer, QgsRasterLayer):
                combo_box.addItem(layer.name())

    def _populate_vector_combo(self, combo_box):
        """Populate the vector combo box with the loaded vector layers."""
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
