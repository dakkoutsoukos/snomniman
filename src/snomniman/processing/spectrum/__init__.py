"""snomniman.processing.spectrum - spectral/interferometric processing operations.

Importing this sub-package registers all spectrum operations in the global step
registry so they are discoverable via ``get_step("spectrum.*")``.
"""

from .fft_interferogram import FftInterferogram
from .ratio import SpectrumRatio
from .savgol_smooth import SavgolSmooth

__all__ = [
    "FftInterferogram",
    "SavgolSmooth",
    "SpectrumRatio",
]
