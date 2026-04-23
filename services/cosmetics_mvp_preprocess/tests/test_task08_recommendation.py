from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task08_recommendation import build_recommendation_lines  # noqa: E402


def test_build_recommendation_lines_keeps_three_lines() -> None:
    result = {
        "decision": "shortlist",
        "explanation_reasons": [
            "HS 적합도가 높습니다.",
            "타깃 국가가 일치합니다.",
            "연락 가능한 정보가 확인됩니다.",
        ],
    }

    lines = build_recommendation_lines(result)

    assert lines == result["explanation_reasons"]


def test_build_recommendation_lines_has_rejected_fallback() -> None:
    lines = build_recommendation_lines({"decision": "rejected", "explanation_reasons": []})

    assert len(lines) == 3
    assert "Hard Gate" in lines[0]
