from .coeusai import CoeusAIPlugin

def classFactory(iface):
    return CoeusAIPlugin(iface)