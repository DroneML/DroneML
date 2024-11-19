from qgis.PyQt import QtWidgets
from qgis.PyQt.QtCore import Qt
from qgis.PyQt import QtCore
from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgsMapCanvas
from qgis.core import QgsRasterLayer, QgsProject, QgsMapSettings
import os


class DroneMLDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(DroneMLDialog, self).__init__(parent)

        # Set up the dialog window properties
        self.setWindowTitle("DroneML Plugin")
        self.resize(800, 600)

        # Create a layout to organize widgets in the dialog
        layout = QtWidgets.QVBoxLayout()

        # Create the QgsMapCanvas and set it up
        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        map_settings = QgsMapSettings()
        self.canvas.setExtent(map_settings.extent())
        layout.addWidget(self.canvas)

        # Create a horizontal layout for buttons (zoom in/out and load raster)
        button_layout = QtWidgets.QHBoxLayout()

        # Add Zoom In Button
        zoom_in_button = QtWidgets.QPushButton("Zoom In")
        zoom_in_button.clicked.connect(self.zoom_in)
        button_layout.addWidget(zoom_in_button)

        # Add Zoom Out Button
        zoom_out_button = QtWidgets.QPushButton("Zoom Out")
        zoom_out_button.clicked.connect(self.zoom_out)
        button_layout.addWidget(zoom_out_button)

        # Add Load Raster Button
        load_raster_button = QtWidgets.QPushButton("Load Raster")
        load_raster_button.clicked.connect(self.load_raster)
        load_raster_button.setFixedSize(32, 32)
        button_layout.addWidget(load_raster_button)

        # Add the button layout to the main layout
        layout.addLayout(button_layout)

        # Set the layout to the dialog
        self.setLayout(layout)

    def zoom_in(self):
        self.canvas.zoomIn()

    def zoom_out(self):
        self.canvas.zoomOut()

    def load_raster(self):
        # Open a file dialog to select a raster file
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Raster", "", "Raster Files (*.tif *.tiff *.img)")

        if file_path:
            # Load the raster layer
            raster_layer = QgsRasterLayer(file_path, "Loaded Raster")

            # Check if the raster layer is valid
            if not raster_layer.isValid():
                QtWidgets.QMessageBox.critical(self, "Error", "Failed to load the raster file.")
                return

            # Add the raster layer to the current project
            # QgsProject.instance().addMapLayer(raster_layer)
            # self.canvas.addLayer(raster_layer)

            # Set the canvas to show the raster layer
            # self.canvas.setTheme('')
            self.canvas.setLayers([raster_layer])

            # Zoom to the full extent of the raster layer
            self.canvas.setExtent(raster_layer.extent())
            self.canvas.refresh()      