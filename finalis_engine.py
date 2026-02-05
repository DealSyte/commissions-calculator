"""
FINALIS CONTRACT PROCESSING ENGINE
Python implementation
VERSION 3.0 - Refactored Architecture

This file provides a simple wrapper around the new `engine` package.
The actual implementation is in the `engine` package with modular calculators.
"""

from typing import Dict, Any
import json

# Import from new architecture
from engine import DealProcessor
from engine.processor import process_deal_from_dict, process_deal_from_json


class FinalisEngine:
    """
    Wrapper for the DealProcessor.
    
    For new code, you can use engine.DealProcessor directly.
    """

    def __init__(self):
        self._processor = DealProcessor()

    def process_deal(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a deal using the new architecture."""
        return self._processor.process_from_dict(input_data)

    # Keep the old constants for any code that references them
    FINRA_RATE = '0.004732'
    DISTRIBUTION_RATE = '0.10'
    SOURCING_RATE = '0.10'
    DEAL_EXEMPT_RATE = '0.015'

    @staticmethod
    def to_money(value) -> float:
        """Convert to float with exactly 2 decimal places."""
        return round(float(value), 2)


# Export for backward compatibility
__all__ = ['FinalisEngine', 'process_deal_from_dict', 'process_deal_from_json']
