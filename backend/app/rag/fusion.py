from __future__ import annotations

from collections import defaultdict


def reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    RRF merge of multiple ranked ID lists (first item = best).
    Returns (id, score) sorted by score descending.
    """
    scores: dict[str, float] = defaultdict(float)
    for lst in ranked_lists:
        if not lst:
            continue
        for rank, cid in enumerate(lst):
            if not cid:
                continue
            scores[cid] += 1.0 / float(k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
