"""snomniman.processing.image - image-domain processing operations.

Importing this sub-package registers all image operations in the global step
registry so they are discoverable via ``get_step("image.*")``.
"""

from .crop import Crop
from .line_flatten import LineFlatten
from .phase_unwrap import PhaseUnwrap
from .plane_level import PlaneLevel
from .reference_normalize import ReferenceNormalize

__all__ = ["Crop", "LineFlatten", "PhaseUnwrap", "PlaneLevel", "ReferenceNormalize"]
