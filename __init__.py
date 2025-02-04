from .droneml import DroneMLPlugin

def classFactory(iface):
    """Plugin entry point"""
    return DroneMLPlugin(iface)
