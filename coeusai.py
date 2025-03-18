import os
import inspect
from .coeusai_dialog import CoeusAIDialog
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon


cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]


class CoeusAIPlugin:
    def __init__(self, iface):
        self.iface = iface

    def initGui(self):
        icon = os.path.join(os.path.join(cmd_folder, "icon.png"))
        self.action = QAction(QIcon(icon), "CoeusAI", self.iface.mainWindow())
        self.iface.addToolBarIcon(self.action)
        self.action.triggered.connect(self.run)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        del self.action

    def run(self):
        # Instantiate the dialog
        self.dlg = CoeusAIDialog()

        # Show the dialog
        self.dlg.show()
