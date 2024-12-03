from qgis.PyQt import QtWidgets
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject
import shapely
import geopandas as gpd
import rioxarray

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

        ds_raster = rioxarray.open_rasterio(raster_layer.source())
        print(ds_raster)

        # Convert positive vector layer to GeoDataFrame
        positive_vector_gdf = _qgs_vector_layer_to_gdf(vec_positive_layer)
        print(positive_vector_gdf)

        # Convert negative vector layer to GeoDataFrame
        negative_vector_gdf = _qgs_vector_layer_to_gdf(vec_negative_layer)
        print(negative_vector_gdf)

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
