"""
Agregacje analityczne
=====================
Funkcje liczące zagregowane widoki ponad zbiorem wyników (np. siła
sektorów na podstawie wyników skanera lub watchlisty). Czysta logika -
bez Streamlit, łatwa do przetestowania.
"""
from __future__ import annotations

from collections import defaultdict


def sector_strength(results: list[dict]) -> list[dict]:
    """Agreguje średni wynik (score) per sektor.

    results: lista dictów z kluczami co najmniej 'sector' i 'score'
             (np. z database.get_scan_results()).

    Zwraca listę dictów posortowaną malejąco po średnim wyniku:
        [{sector, avg_score, count, min_score, max_score}, ...]
    Pomija pozycje bez sektora (None / "Nieznany").
    """
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in results:
        sector = r.get("sector")
        score = r.get("score")
        if not sector or sector == "Nieznany" or score is None:
            continue
        buckets[sector].append(float(score))

    out = []
    for sector, scores in buckets.items():
        if not scores:
            continue
        out.append({
            "sector": sector,
            "avg_score": round(sum(scores) / len(scores), 1),
            "count": len(scores),
            "min_score": round(min(scores), 1),
            "max_score": round(max(scores), 1),
        })

    out.sort(key=lambda x: -x["avg_score"])
    return out
