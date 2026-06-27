"""The narrative-provider seam - where an optional AI renderer plugs in.

The Scientific Briefing's *facts* are deterministic and provider-free. An optional
*interpretation* (natural-language narrative) is produced by a
:class:`NarrativeProvider`: a renderer that turns the deterministic
:class:`~snomniman.ai.report.BriefingContext` into prose. The rest of SNOMNIMAN
depends only on this protocol, never on a specific model vendor.

**No model SDK is bundled in this milestone** (zero new dependency). A future commit
will add a concrete provider (e.g. Anthropic) behind this same protocol, as an
*optional* extra, lazy-imported, never required for the backend or CI. The prompt a
provider should send is built here (:func:`build_orientation_prompt`) so it is
testable without any network, and so every provider grounds identically: it may use
**only** the supplied facts and must never invent.
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

from .report import BriefingContext

#: Instructions shared by every provider. Grounding is enforced by construction
#: (the model receives only the facts payload) and reinforced here.
ORIENTATION_SYSTEM = (
    "You are an experienced scattering-type scanning near-field optical microscopy "
    "(s-SNOM) and nano-FTIR scientist writing a brief orientation for a colleague who "
    "has just opened a measurement.\n"
    "Rules:\n"
    "- Use ONLY the facts provided below. Do not invent values, channels, or history.\n"
    "- If something is not in the facts, treat it as unknown and say so.\n"
    "- Clearly separate established facts from any interpretation you offer.\n"
    "- Do NOT recommend or perform processing; this is orientation only.\n"
    "- Be concise: a short paragraph, not a report."
)


def build_orientation_prompt(context: BriefingContext) -> str:
    """Build the grounded prompt for a narrative provider (deterministic).

    The entire factual payload is embedded verbatim; there is no hidden context.
    Testable without a network, and identical across providers.
    """
    facts = json.dumps(context.to_dict(), indent=2, sort_keys=True)
    return (
        f"{ORIENTATION_SYSTEM}\n\n"
        "FACTS (the only information you may use):\n"
        f"{facts}\n\n"
        "Write the orientation now, grounded entirely in the facts above."
    )


@runtime_checkable
class NarrativeProvider(Protocol):
    """A renderer that turns deterministic facts into a narrative interpretation.

    Implementations must be side-effect-free with respect to the dataset and must
    derive their output solely from ``context``. ``name`` identifies the provider
    for auditability (recorded on the :class:`~snomniman.ai.report.Briefing`).
    """

    name: str

    def narrate(self, context: BriefingContext) -> str: ...


class MockNarrativeProvider:
    """A deterministic, network-free provider for tests and demos.

    It does not call any model; it emits a fixed-shape narrative derived from the
    context, proving the grounding path end-to-end (the facts flow in, the
    narrative cites them) without external dependencies.
    """

    name = "mock"

    def narrate(self, context: BriefingContext) -> str:
        desc = context.description
        n_channels = len(desc.get("channels", []))
        is_raw = desc.get("is_raw")
        kind = desc.get("data_kind", "measurement")
        state = "raw" if is_raw else "derived"
        return (
            f"[mock interpretation] This {state} {kind} measurement has "
            f"{n_channels} channel(s). Narrative grounded in the supplied facts."
        )


__all__ = [
    "ORIENTATION_SYSTEM",
    "MockNarrativeProvider",
    "NarrativeProvider",
    "build_orientation_prompt",
]
