from qgis.PyQt import QtWidgets
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
import os
import shapely
import numpy as np
import geopandas as gpd
import rioxarray
from pyproj import CRS
from .segmentmytif.src.segmentmytiff.main import make_predictions

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

        # Get current selections
        raster_layer = QgsProject.instance().mapLayersByName(
            self.raster_combo.currentText()
        )[0]
        vec_positive_layer = QgsProject.instance().mapLayersByName(
            self.vec_positive_combo.currentText()
        )[0]
        vec_negative_layer = QgsProject.instance().mapLayersByName(
            self.vec_negative_combo.currentText()
        )[0]

        print(f"Raster Layer: {raster_layer}")
        print(f"Positive Vector Layer: {vec_positive_layer}")
        print(f"Negative Vector Layer: {vec_negative_layer}")

        # Load data as Python objects
        ds_raster = rioxarray.open_rasterio(raster_layer.source())  # Xarray DataArray
        positive_vector_gdf = _qgs_vector_layer_to_gdf(vec_positive_layer)
        negative_vector_gdf = _qgs_vector_layer_to_gdf(vec_negative_layer)

        # Align CRS
        # Covert from vector CRS to raster CRS, since raster can be big to reproject
        # Set raster CRS with EPSG code from QGIS layer
        ds_raster = ds_raster.rio.write_crs(
            CRS.from_string(raster_layer.crs().authid()), inplace=True
        )
        # Set vector CRS with EPSG code from QGIS vect layers, then convert to raster CRS
        positive_vector_gdf = positive_vector_gdf.set_crs(
            CRS.from_string(vec_positive_layer.crs().authid())
        ).to_crs(ds_raster.rio.crs)
        negative_vector_gdf = negative_vector_gdf.set_crs(
            CRS.from_string(vec_negative_layer.crs().authid())
        ).to_crs(ds_raster.rio.crs)

        # Crop the raster
        raster_positive = ds_raster.rio.clip(positive_vector_gdf.geometry, drop=False)
        raster_negative = ds_raster.rio.clip(negative_vector_gdf.geometry, drop=False)

        # Conver the to a binary mask
        positive_labels = raster_positive.where(
            raster_positive.isnull(), 1
        )  # Covert non-nan values to 1
        positive_labels = positive_labels.where(
            positive_labels == 1, -1
        )  # Covert non-positive values to -1
        negative_labels = raster_negative.where(
            raster_negative.isnull(), 0
        )  # Covert non-nan values to 0
        negative_labels = negative_labels.where(
            negative_labels == 0, -1
        )  # Covert non-negative values to -1
        labels = (
            positive_labels * negative_labels * -1
        )  # Combine positive and negative labels

        # Make segmentation predictions
        results = make_predictions(ds_raster.data, labels.data)

        negative_prediction = ds_raster.copy()
        negative_prediction.data = np.expand_dims(results[0, :, :], axis=0)
        positive_prediction = ds_raster.copy()
        positive_prediction.data = np.expand_dims(results[1, :, :], axis=0)

        # Write the DataArray to a GeoTIFF
        project_dir = os.path.dirname(QgsProject.instance().fileName())
        path_negative_prediction = os.path.join(project_dir, "negative_prediction.tif")
        path_positive_prediction = os.path.join(project_dir, "positive_prediction.tif")
        negative_prediction.rio.to_raster(path_negative_prediction)
        positive_prediction.rio.to_raster(path_positive_prediction)

        # Add the new raster layer to QGIS
        for layer_name, path in zip(
            ["positive", "negative"],
            [path_negative_prediction, path_positive_prediction],
        ):
            new_raster_layer = QgsRasterLayer(path, layer_name)
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


def _qgs_vector_layer_to_gdf(qgs_layer):
    """Convert QgsVectorLayer to GeoPandas DataFrame"""
    features = [f for f in qgs_layer.getFeatures()]
    geometries = [shapely.from_wkt(f.geometry().asWkt()) for f in features]
    attributes = [f.attributes() for f in features]
    field_names = [field.name() for field in qgs_layer.fields()]
    gdf = gpd.GeoDataFrame(attributes, columns=field_names, geometry=geometries)
    return gdf


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
