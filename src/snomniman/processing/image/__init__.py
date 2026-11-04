"""snomniman.processing.image - image-domain processing operations.

Importing this sub-package registers all image operations in the global step
registry so they are discoverable via ``get_step("image.*")``.
"""

from .arithmetic import Arithmetic
from .crop import Crop
from .fix_zero import FixZero
from .line_flatten import LineFlatten
from .normalize_amplitude import NormalizeAmplitude
from .phase_offset import PhaseOffset
from .phase_unwrap import PhaseUnwrap
from .plane_level import PlaneLevel
from .reference_normalize import ReferenceNormalize
from .region_amplitude_reference import RegionAmplitudeReference
from .region_phase_reference import RegionPhaseReference
from .threshold_segment import ThresholdSegment

__all__ = [
    "Arithmetic",
    "Crop",
    "FixZero",
    "LineFlatten",
    "NormalizeAmplitude",
    "PhaseOffset",
    "PhaseUnwrap",
    "PlaneLevel",
    "ReferenceNormalize",
    "RegionAmplitudeReference",
    "RegionPhaseReference",
    "ThresholdSegment",
]
