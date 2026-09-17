from core.registry import AppRegistry
from apps.darksky import DarkskyApp

__all__ = ["default_registry"]


def default_registry() -> AppRegistry:
    registry = AppRegistry()
    registry.register(DarkskyApp())
    return registry
