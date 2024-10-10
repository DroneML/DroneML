from .droneml import DroneMLPlugin

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load DroneMLPlugin class from file DroneMLPlugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    
    return DroneMLPlugin(iface)
