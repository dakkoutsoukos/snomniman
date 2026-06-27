"""snomniman.processing.image - image-domain processing operations.

Importing this sub-package registers all image operations in the global step
registry so they are discoverable via ``get_step("image.*")``.
"""

from .plane_level import PlaneLevel

__all__ = ["PlaneLevel"]
