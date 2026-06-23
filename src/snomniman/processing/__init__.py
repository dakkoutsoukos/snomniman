"""snomniman.processing - operations on datasets (depends on snomniman.core).

Defines the ``ProcessingStep`` command abstraction and the step registry, plus
concrete, non-mutating operations grouped by domain (``image``, ``spectrum``,
``common``). Every step returns a new ``Dataset`` carrying one appended
``StepRecord`` and never mutates its input (ADR-0004, ADR-0005). Phase
operations (invert / re-reference / unwrap / normalize) are always explicit and
recorded - never silent (OHD-6D); unwrapped phase is a first-class channel
(OHD-4).
"""
