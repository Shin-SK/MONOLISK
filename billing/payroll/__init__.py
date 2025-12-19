# billing/payroll/__init__.py
"""給与計算エンジン群"""

from .engines import get_engine

__all__ = ['get_engine']
