from qgis.PyQt import QtWidgets

class DroneMLDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        """Constructor."""
        super(DroneMLDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        # self.setupUi(self)

        self.setWindowTitle("DroneML Plugin")
        self.resize(500,300)