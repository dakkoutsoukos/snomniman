"""snomniman.physics - deterministic material-parameter extraction (Phase 8).

A Qt-free backend package (Rule 4), sibling to :mod:`snomniman.diagnostics` /
:mod:`snomniman.describe` / :mod:`snomniman.ai`, depending only on ``numpy``/
``scipy`` over plain arrays (no ``core``/``processing`` dependency - it operates on
already-extracted spectral arrays, the same boundary :mod:`snomniman.viz.measure`
uses). It exists because a fitted physical parameter (a Drude plasma frequency, a
Lorentz oscillator strength, a finite-dipole-inverted permittivity) is a genuinely new
class of derived scientific knowledge - the output of inverting a physical *model*
through the data, not a statistic about the array (``diagnostics``) or a projection
of existing metadata (``describe``). See ``docs/phase7-9-master-roadmap.md`` Section
4.2 for the full architectural justification (the same category of decision that
justified ``describe``/``diagnostics``/``ai`` each getting their own module).

Every capability here is split, exactly as the project always splits it
(Section 4.1): *"can a researcher run this fit, previewed, on a spectrum they
chose?"* is a plain analysis (Category A - the standard operation Definition of
Done, no Scientific Validation Phase study needed) versus *"should the engine
auto-recommend which physical model applies, or auto-assert a fitted parameter as a
fact?"* (a judgement - Category B, gated by the full Scientific Validation Phase).
This module ships **only** the former: every fit here is researcher-initiated,
never automatically asserted. No auto-recommendation rule is registered anywhere in
this module.

Phase 8A (shipped): :func:`~snomniman.physics.dielectric.fit_dielectric_model` - a
shared Drude/Lorentz-oscillator fit to a measured complex near-field spectrum. Phase
8B (finite dipole model, tip-model dielectric-function inversion) and 8C
(carrier-density estimation) are named in the design doc but not yet implemented.
"""

from __future__ import annotations

from .dielectric import (
    DRUDE,
    LORENTZ,
    MODEL_KINDS,
    DielectricFit,
    drude_epsilon,
    fit_dielectric_model,
    lorentz_epsilon,
)

__all__ = [
    "DRUDE",
    "LORENTZ",
    "MODEL_KINDS",
    "DielectricFit",
    "drude_epsilon",
    "fit_dielectric_model",
    "lorentz_epsilon",
]
