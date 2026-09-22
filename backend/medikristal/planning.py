from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .errors import DomainError


@dataclass(frozen=True)
class BranchCost:
    probability: float
    amount_minor: int


def expected_cost(initial_amount_minor: int, branches: Iterable[BranchCost]) -> float:
    """Expected monetary cost for a finite, synthetic strategy tree.

    This is economic arithmetic only. Branch probabilities must come from an admitted
    decision model; the function never derives disease probabilities from prices.
    """
    if initial_amount_minor < 0:
        raise DomainError("invalid_request", 422, "Un coût ne peut pas être négatif.")
    total_probability = 0.0
    expected = float(initial_amount_minor)
    for branch in branches:
        if not 0.0 <= branch.probability <= 1.0:
            raise DomainError("invalid_request", 422, "Probabilité de branche invalide.")
        if branch.amount_minor < 0:
            raise DomainError("invalid_request", 422, "Un coût ne peut pas être négatif.")
        total_probability += branch.probability
        expected += branch.probability * branch.amount_minor
    if total_probability > 1.0000000001:
        raise DomainError("strategy_incomplete", 422, "Les branches se chevauchent ou dépassent une probabilité totale de 1.")
    return expected


def pareto_front(rows: list[dict], criteria: list[str]) -> list[dict]:
    """Return non-dominated rows; unknown criteria do not become zero."""
    def dominates(a: dict, b: dict) -> bool:
        better_or_equal = True
        strictly_better = False
        for key in criteria:
            av, bv = a.get(key), b.get(key)
            if av is None or bv is None:
                return False
            if av > bv:
                better_or_equal = False
                break
            if av < bv:
                strictly_better = True
        return better_or_equal and strictly_better
    out=[]
    for row in rows:
        if not any(other is not row and dominates(other,row) for other in rows):
            out.append(row)
    return out
