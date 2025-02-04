"""__init__.py for the DroneML plugin.

Inspired by github.com/cholmes/qgis_plugin_gpq_downloader
"""

from .droneml import DroneMLPlugin

import os
import platform
import subprocess
import sys
from pathlib import Path

from qgis.PyQt.QtWidgets import QProgressBar
from qgis.PyQt.QtCore import QCoreApplication, QTimer
from qgis.core import Qgis, QgsTask, QgsApplication
from qgis.utils import iface

# Backend dependency name
BACKEND_NAME = "segmentmytif"

# Global flag to track installation status
BACKEND_INSTALLED = False


class BackendInstallerTask(QgsTask):
    def __init__(self, callback):
        # Simple initialization with just CanCancel flag
        super().__init__("Installing Backend", QgsTask.CanCancel)
        self.success = False
        self.message = ""
        self.exception = None
        self.callback = callback

    def run(self):
        # print("Task run method started")
        try:
            print("Starting Backend installation...")
            py_path = sys.executable

            print(f"Using Python path: {py_path}")
            print(f"Running pip install command...")

            subprocess.check_call(
                [py_path, "-m", "pip", "install", "--user", BACKEND_NAME]
            )

            # print("Pip install completed, reloading modules...")
            import importlib

            importlib.invalidate_caches()

            self.success = True
            self.message = "Backend installed successfully"
            return True

        except subprocess.CalledProcessError as e:
            self.exception = e
            self.message = f"Pip install failed: {str(e)}"
            print(f"Installation failed with error: {str(e)}")
            return False
        except Exception as e:
            self.exception = e
            self.message = f"Failed to install/upgrade Backend: {str(e)}"
            print(f"Installation failed with error: {str(e)}")
            return False

    def finished(self, result):
        global BACKEND_INSTALLED
        msg_bar = iface.messageBar()
        msg_bar.clearWidgets()

        if result and self.success:
            try:
                import Backend

                self.message = f"Backend {Backend.__version__} installed successfully"
            except ImportError:
                pass
            msg_bar.pushSuccess("Success", self.message)
            print(self.message)
            BACKEND_INSTALLED = True
            if self.callback:
                self.callback()
        else:
            msg_bar.pushCritical("Error", self.message)
            print(self.message)
            BACKEND_INSTALLED = False


def ensure_Backend(callback=None):
    try:
        import Backend

        version = Backend.__version__
        from packaging import version as version_parser

        if version_parser.parse(version) >= version_parser.parse("1.1.0"):
            print(f"Backend {version} already installed")
            global BACKEND_INSTALLED
            BACKEND_INSTALLED = True
            if callback:
                callback()
            return True
        else:
            print(f"Backend {version} found but needs upgrade to 1.1.0+")
            raise ImportError("Version too old")

    except ImportError:
        print("Backend not found or needs upgrade, attempting to install/upgrade...")
        try:
            msg_bar = iface.messageBar()
            progress = QProgressBar()
            progress.setMinimum(0)
            progress.setMaximum(0)
            progress.setValue(0)

            msg = msg_bar.createMessage("Installing Backend...")
            msg.layout().addWidget(progress)
            msg_bar.pushWidget(msg)
            QCoreApplication.processEvents()

            # Create and start the task
            task = BackendInstallerTask(callback)
            # print("Created installer task")

            # Get the task manager and add the task
            task_manager = QgsApplication.taskManager()
            # print(f"Task manager has {task_manager.count()} tasks")

            # Add task and check if it was added successfully
            success = task_manager.addTask(task)
            # print(f"Task added successfully: {success}")

            # Check task status
            print(f"Task manager now has {task_manager.count()} tasks")
            print(f"Task description: {task.description()}")
            print(f"Task status: {task.status()}")

            # Schedule periodic status checks with guarded access
            def check_status():
                try:
                    status = task.status()
                except RuntimeError:
                    # print("Task has been deleted, stopping status checks")
                    return

                # print(f"Current task status: {status}")
                if status == QgsTask.Queued:
                    # print("Task still queued, retriggering...")
                    try:
                        QgsApplication.taskManager().triggerTask(task)
                    except RuntimeError:
                        print("Failed to trigger task, object likely deleted")
                        return
                    QTimer.singleShot(1000, check_status)
                elif status == QgsTask.Running:
                    # print("Task is running")
                    QTimer.singleShot(1000, check_status)
                elif status == QgsTask.Complete:
                    print("Task completed")

            # Start checking status after a short delay
            QTimer.singleShot(100, check_status)

            return True

        except Exception as e:
            msg_bar.clearWidgets()
            msg_bar.pushCritical(
                "Error", f"Failed to install/upgrade Backend: {str(e)}"
            )
            print(f"Failed to setup task with error: {str(e)}")
            print(f"Error type: {type(e)}")
            import traceback

            print(f"Traceback: {traceback.format_exc()}")
            return False


# Instead of a standalone delayed_plugin_load, we now embed the real plugin loading logic
# into our dummy plugin.
class DummyPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.real_plugin = None

    def initGui(self):
        # Optionally show a temporary message or a "loading" placeholder
        self.iface.messageBar().pushInfo(
            "Info", "Plugin is loading… Please wait while dependencies install."
        )

    def unload(self):
        # Unload the real plugin if it has been loaded.
        if self.real_plugin:
            self.real_plugin.unload()

    def loadRealPlugin(self):
        from .qgis_plugin_gpq_downloader import QgisPluginGeoParquet

        self.real_plugin = QgisPluginGeoParquet(self.iface)
        # The real plugin adds the buttons and other UI elements
        self.real_plugin.initGui()
        self.iface.messageBar().pushSuccess(
            "Success", "Plugin fully loaded with all functionalities"
        )
        # print("Real plugin loaded and UI initialized.")


def classFactory(iface):
    """Plugin entry point"""
    # Setup the path for Backend
    plugin_dir = os.path.dirname(__file__)
    ext_libs_path = os.path.join(plugin_dir, "ext-libs")
    backend_path = os.path.join(ext_libs_path, "Backend")

    # Add paths to sys.path if they're not already there
    for path in [ext_libs_path, backend_path]:
        if path not in sys.path:
            sys.path.insert(0, path)

    # Create the dummy plugin instance
    dummy_plugin = DummyPlugin(iface)

    # Schedule Backend installation and, once complete, load the real plugin UI.
    QTimer.singleShot(0, lambda: ensure_Backend(dummy_plugin.loadRealPlugin))

    # Return the dummy plugin so QGIS has a valid plugin instance immediately
    return dummy_plugin
