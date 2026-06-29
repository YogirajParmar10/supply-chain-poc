from datetime import date

import numpy as np

QUANTITY_RANGES: tuple[tuple[int, int], ...] = (
    (500, 2_000),
    (2_000, 10_000),
    (10_000, 50_000),
)


def generate_order_dates(
    count: int,
    start_date: date,
    end_date: date,
    rng: np.random.Generator,
) -> list[date]:
    start_ord = start_date.toordinal()
    end_ord = end_date.toordinal()
    day_offsets = rng.integers(0, end_ord - start_ord + 1, size=count)
    return [date.fromordinal(start_ord + int(offset)) for offset in day_offsets]


def generate_quantities(count: int, rng: np.random.Generator) -> list[int]:
    tier_indices = rng.integers(0, len(QUANTITY_RANGES), size=count)
    quantities: list[int] = []
    for tier_index in tier_indices:
        low, high = QUANTITY_RANGES[int(tier_index)]
        quantities.append(int(rng.integers(low, high + 1)))
    return quantities


def status_choices(
    status_weights: tuple[tuple[str, float], ...],
) -> tuple[list[str], list[float]]:
    statuses = [status for status, _ in status_weights]
    weights = [weight for _, weight in status_weights]
    return statuses, weights
