import os
import inspect
import sys
import subprocess

from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
from qgis.utils import iface

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]


class DroneMLPlugin:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        icon = os.path.join(os.path.join(cmd_folder, "icon.png"))
        self.action = QAction(QIcon(icon), "DroneML", self.iface.mainWindow())
        self.iface.addToolBarIcon(self.action)
        self.action.triggered.connect(self.run)

        # Setup the path for Backend
        plugin_dir = os.path.dirname(__file__)
        ext_libs_path = os.path.join(plugin_dir, "ext-libs")
        backend_path = os.path.join(ext_libs_path, "segmentmytif")

        # Add paths to sys.path if they're not already there
        for path in [ext_libs_path, backend_path]:
            if path not in sys.path:
                sys.path.insert(0, path)

        installed = ensure_backend(backend_path)

        # Ensure the backend is installed
        if not installed:
            print("DroneML plugin not loaded")
            return None

        print("DroneML plugin loaded")

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        """load and show the dialog"""
        from .droneml_dialog import DroneMLDialog

        # Instantiate the dialog
        self.dlg = DroneMLDialog()

        # Show the dialog
        self.dlg.show()


def ensure_backend(backend_path):
    """Ensure the backend is installed in backend_path."""

    try:
        sys.path.insert(0, backend_path)
        import segmentmytif

        version = segmentmytif.__version__
        print(f"segmentmytif {version} already installed.")
        return True

    except ImportError:
        print("Backend not found or needs upgrade, attempting to install/upgrade...")
        try:
            msg_bar = iface.messageBar()
            msg = msg_bar.createMessage("Installing segmentmytif, a command line window will be opened...")
            msg_bar.pushWidget(msg)
            QCoreApplication.processEvents()

            subprocess.check_call(
                [
                    "python",
                    "-m",
                    "pip",
                    "install",
                    "segmentmytif",
                    "--target",
                    backend_path,
                ]
            )

        except Exception as e:
            msg_bar.clearWidgets()
            msg_bar.pushCritical(
                "Error", f"Failed to install/upgrade segmentmytif: {str(e)}"
            )
            print(f"Failed to setup task with error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback

            print(f"Traceback: {traceback.format_exc()}")
            return False
