from qgis.PyQt import QtWidgets
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject


class DroneMLDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(DroneMLDialog, self).__init__(parent)

        # Set up the dialog window properties
        self.setWindowTitle("DroneML Plugin")
        self.resize(800, 600)


        # Create a layout to organize widgets in the dialog
        layout = QtWidgets.QVBoxLayout()

        # Combo box for raster layers
        # Label
        raster_label = QtWidgets.QLabel("Raster layer for training:")
        raster_label.setGeometry(50, 50, 200, 30)
        # Combo box
        layout.addWidget(raster_label)
        self.raster_combo = QtWidgets.QComboBox()
        _populate_raster_combo(self.raster_combo)
        layout.addWidget(self.raster_combo)

        # Combo box for raster layers
        vec_positive_label = QtWidgets.QLabel("Vector layer for positive labels:")
        layout.addWidget(vec_positive_label)
        self.vec_positive = QtWidgets.QComboBox()
        _populate_vector_combo(self.vec_positive)
        layout.addWidget(self.vec_positive)

         # Combo box for raster layers
        vec_negative_label = QtWidgets.QLabel("Vector layer for negative labels:")
        layout.addWidget(vec_negative_label)
        self.vec_negative = QtWidgets.QComboBox()
        _populate_vector_combo(self.vec_negative)
        layout.addWidget(self.vec_negative)

        # Create a horizontal layout for buttons (zoom in/out and load raster)
        button_layout = QtWidgets.QHBoxLayout()

        # Add Load Raster Button
        run_button = QtWidgets.QPushButton("run")
        # run_button.clicked.connect(self.load_raster)
        run_button.setFixedSize(64, 32)
        button_layout.addWidget(run_button)

        # Add the button layout to the main layout
        layout.addLayout(button_layout)

        # Set the layout to the dialog
        self.setLayout(layout)

def _populate_raster_combo(raster_combo):
    """Poluate the raster combo box with the loaded raster layers."""

    # Get the list of layers in the current QGIS project
    layers = QgsProject.instance().mapLayers().values()
    for layer in layers:
        if isinstance(layer, QgsRasterLayer):
            raster_combo.addItem(layer.name())

def _populate_vector_combo(vector_combo):
    """Poluate the vector combo box with the loaded vector layers."""

    # Get the list of layers in the current QGIS project
    layers = QgsProject.instance().mapLayers().values()
    for layer in layers:
        if isinstance(layer, QgsVectorLayer):
            vector_combo.addItem(layer.name())

    