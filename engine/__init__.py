"""
FINALIS CONTRACT PROCESSING ENGINE
Version 3.0 - Refactored Architecture
"""

from .models import DealInput, DealResult
from .processor import DealProcessor

__all__ = ['DealProcessor', 'DealInput', 'DealResult']
