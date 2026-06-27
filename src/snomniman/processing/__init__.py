"""snomniman.processing - operations on datasets (depends on snomniman.core).

Every scientific transformation is a :class:`ProcessingStep` subclass.
Steps are registered with :func:`register` and retrieved from the registry
with :func:`get_step`.  The framework guarantees:

- :meth:`~ProcessingStep.apply` never mutates its input Datasets.
- Every result carries a :class:`~snomniman.core.StepRecord` in its
  provenance DAG (step_id, version, params, inputs, software versions).
- Params are JSON-serializable (scalars only; no NumPy arrays).

Phase operations (invert / re-reference / unwrap / normalize) are always
explicit and recorded - never silent (OHD-6D); unwrapped phase is a
first-class channel (OHD-4).

Concrete operations live in sub-packages by domain::

    snomniman.processing.image   - crop, level, normalize, phase ops
    snomniman.processing.common  - masking, unit conversion, statistics
"""

from .registry import get_step, list_steps, register
from .step import (
    CHANNEL_ANY,
    CHANNEL_COMPLEX,
    CHANNEL_REAL,
    ParameterSpec,
    ProcessingStep,
)

__all__ = [
    "CHANNEL_ANY",
    "CHANNEL_COMPLEX",
    "CHANNEL_REAL",
    "ParameterSpec",
    "ProcessingStep",
    "get_step",
    "list_steps",
    "register",
]

# Domain sub-packages (snomniman.processing.image, etc.) are NOT imported here
# to keep the processing package free of circular-import risk.  Import the
# sub-package explicitly when you need its operations to be registered:
#
#   import snomniman.processing.image   # registers image.plane_level etc.
#
# The GUI (window.py) and the pipeline replay engine are responsible for
# importing the sub-packages they need before calling get_step().
