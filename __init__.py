from .droneml import DroneMLPlugin

def classFactory(iface):
    return DroneMLPlugin(iface)