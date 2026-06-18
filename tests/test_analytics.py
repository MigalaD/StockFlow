"""
Testy dla analytics.py (agregacja siły sektorów).
"""
from analytics import sector_strength


def test_sector_strength_basic():
    data = [
        {"sector": "Technology", "score": 70},
        {"sector": "Technology", "score": 60},
        {"sector": "Energy", "score": 40},
    ]
    result = sector_strength(data)
    assert len(result) == 2
    # posortowane malejąco -> Technology pierwsze
    assert result[0]["sector"] == "Technology"
    assert result[0]["avg_score"] == 65.0
    assert result[0]["count"] == 2
    assert result[0]["min_score"] == 60.0
    assert result[0]["max_score"] == 70.0


def test_sector_strength_skips_unknown():
    data = [
        {"sector": "Technology", "score": 70},
        {"sector": "Nieznany", "score": 99},
        {"sector": None, "score": 99},
        {"sector": "Energy", "score": None},
    ]
    result = sector_strength(data)
    sectors = {r["sector"] for r in result}
    assert sectors == {"Technology"}


def test_sector_strength_empty():
    assert sector_strength([]) == []


def test_sector_strength_sorted_descending():
    data = [
        {"sector": "A", "score": 30},
        {"sector": "B", "score": 80},
        {"sector": "C", "score": 55},
    ]
    result = sector_strength(data)
    scores = [r["avg_score"] for r in result]
    assert scores == sorted(scores, reverse=True)
