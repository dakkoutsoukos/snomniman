"""Suggested Next Steps - orchestrating the Scientific Reasoning Rule Engine.

:func:`recommend_workflow` builds a deterministic :class:`~snomniman.ai.reasoning.ReasoningContext`
and evaluates every registered :class:`~snomniman.ai.reasoning.ReasoningRule` against it,
enforcing the universal guards (the operation must be *applicable* and *not already
applied*), honouring rule prerequisites and exclusions, and ranking the survivors by
priority. The result is a deterministic, grounded, ordered list of next steps - the
scientific authority for "what next" (CLAUDE.md AI rule 3). Nothing is executed; the
dataset is never modified.

Separation of concerns: the recommendation *data types* live in :mod:`snomniman.ai.report`;
the *rules* (the scientific judgment) live in :mod:`snomniman.ai.reasoning`; this module is
only the engine that runs them. See ``docs/scientific-reasoning.md`` (ADR-0022/ADR-0023).
"""

from __future__ import annotations

from snomniman.core import Dataset

from .reasoning import ReasoningContext, ReasoningRule, RuleOutcome, iter_rules
from .report import BriefingContext, Recommendation, WorkflowSuggestions

#: A (rule, its verdict) pair that survived the guards.
_Proposal = tuple[ReasoningRule, RuleOutcome]


def recommend_workflow(
    dataset: Dataset, *, title: str | None = None
) -> WorkflowSuggestions:
    """Build ranked, grounded next-step suggestions for *dataset* (read-only).

    Evaluates the registered reasoning rules over the deterministic facts; only
    operations that are applicable, not already applied, with their prerequisites
    satisfied and not excluded by a stronger peer, and supported by a rule's
    evidence, survive. Nothing is executed and the dataset is never modified.
    """
    ctx = ReasoningContext.build(dataset, title=title)

    proposals: list[_Proposal] = []
    for rule in iter_rules():
        app = ctx.applicability(rule.step_id)
        if app is None or not app.applicable or app.already_applied:
            continue
        if not _prerequisites_satisfied(rule, ctx):
            continue
        outcome = rule.evaluate(ctx)
        if outcome is not None:
            proposals.append((rule, outcome))

    kept = _resolve_exclusions(proposals)
    recommendations = [_to_recommendation(rule, outcome) for rule, outcome in kept]
    recommendations.sort(key=lambda r: r.confidence, reverse=True)

    note = None if recommendations else _empty_note(ctx)
    context = BriefingContext(
        description=ctx.description.to_dict(), diagnostics=ctx.diagnostics.to_dict()
    )
    return WorkflowSuggestions(
        title=title,
        recommendations=tuple(recommendations),
        note=note,
        context=context,
    )


def _prerequisites_satisfied(rule: ReasoningRule, ctx: ReasoningContext) -> bool:
    """A rule is offered only once all its prerequisite operations are applied.

    With no prerequisites (today's rules) this is always True; when a rule does
    declare one, the recommendation surfaces only *after* the prerequisite has been
    done - so the engine yields a naturally sequenced workflow across the process
    loop, without an up-front ordering solve.
    """
    return all(step in ctx.applied_steps for step in rule.prerequisite_steps)


def _resolve_exclusions(proposals: list[_Proposal]) -> list[_Proposal]:
    """Drop the lower-confidence side of any mutually-excluded pair of proposals."""
    dropped: set[str] = set()
    for rule, outcome in proposals:
        for other_rule, other_outcome in proposals:
            if other_rule.rule_id == rule.rule_id:
                continue
            if (
                other_rule.step_id in rule.excluded_steps
                or other_rule.rule_id in rule.excluded_steps
            ):
                dropped.add(
                    other_rule.rule_id
                    if outcome.confidence >= other_outcome.confidence
                    else rule.rule_id
                )
    return [(rule, outcome) for rule, outcome in proposals if rule.rule_id not in dropped]


def _to_recommendation(rule: ReasoningRule, outcome: RuleOutcome) -> Recommendation:
    return Recommendation(
        rule_id=rule.rule_id,
        step_id=rule.step_id,
        title=_op_title(rule.step_id),
        params=dict(outcome.params),
        confidence=round(outcome.confidence, 2),
        rationale=outcome.rationale,
        evidence=outcome.evidence,
        considerations=outcome.considerations,
        expected_outcome=outcome.expected_outcome,
    )


def _op_title(step_id: str) -> str:
    """Human title from a step_id: ``image.plane_level`` -> ``Plane Level``."""
    return step_id.split(".")[-1].replace("_", " ").title()


def _empty_note(ctx: ReasoningContext) -> str:
    if any(a.already_applied for a in ctx.diagnostics.applicability):
        return (
            "No further steps are suggested right now: the operations this measurement "
            "supports have already been applied, or there is no deterministic evidence "
            "that another step is needed."
        )
    return (
        "No next steps are suggested: there is no deterministic evidence that a processing "
        "step is currently needed."
    )


__all__ = ["recommend_workflow"]
