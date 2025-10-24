# billing/payroll/engines/__init__.py
import importlib, pkgutil
from typing import Dict, Type
from .base import BaseEngine

_REGISTRY: Dict[str, Type[BaseEngine]] = {}
_DISCOVERED = False

def register(slug: str):
    def deco(cls):
        _REGISTRY[slug] = cls
        return cls
    return deco

def _autodiscover():
    global _DISCOVERED
    if _DISCOVERED: return
    pkg = __name__ + ".stores"
    try:
        m = importlib.import_module(pkg)
    except ModuleNotFoundError:
        _DISCOVERED = True
        return
    for info in pkgutil.iter_modules(m.__path__):
        importlib.import_module(f"{pkg}.{info.name}")
    _DISCOVERED = True

def get_engine(store) -> BaseEngine:
    _autodiscover()
    cls = _REGISTRY.get(getattr(store, "slug", None))
    return cls(store) if cls else BaseEngine(store)
