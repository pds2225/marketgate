from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from task05_shortlist import normalize_text  # noqa: E402
from task06_fit_score import recommendation_lines_v0  # noqa: E402


def build_recommendation_lines(score_result: Mapping[str, Any]) -> list[str]:
    decision = normalize_text(score_result.get("decision"))
    raw_explanations = [
        normalize_text(line)
        for line in score_result.get("explanation_reasons", [])
        if normalize_text(line)
    ]
    if decision == "rejected" and not raw_explanations:
        lines = [
            "Hard Gate 미통과로 shortlist 대상에서 제외했습니다.",
            "gate_reason을 먼저 확인한 뒤 country/HS/capacity 조건을 보정해야 합니다.",
            "재평가 전까지는 ranking 점수를 부여하지 않습니다.",
        ]
    else:
        lines = [
            normalize_text(line)
            for line in recommendation_lines_v0(score_result)
            if normalize_text(line)
        ]
    if not lines:
        lines = [
            "핵심 적합도 근거는 확보됐지만 설명용 텍스트가 제한적입니다.",
            "score_breakdown과 matched_terms를 함께 확인하는 것이 좋습니다.",
            "추가 정밀화는 TASK-08 이후 explanation 템플릿에서 확장할 수 있습니다.",
        ]

    while len(lines) < 3:
        lines.append("추천 근거를 생성할 수 있는 정보가 제한적입니다.")
    return lines[:3]


def _demo() -> None:
    sample = {
        "decision": "shortlist",
        "explanation_reasons": [
            "HS 적합도가 높습니다 (330499 vs 3304) 그리고 serum, cream 키워드가 함께 겹칩니다.",
            "타깃 국가 미국과 buyer 국가 미국이 일치합니다.",
            "최근 6개월 내 사용 가능한 inquiry signal이 있습니다, 연락 가능한 contact 정보가 확인됩니다.",
        ],
    }
    print("[task08-demo] recommendation_lines =", build_recommendation_lines(sample))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TASK-08 추천 근거 3줄 자동 생성")
    parser.add_argument("--demo", action="store_true", help="추천 근거 3줄 예시를 출력한다.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.demo or not any(vars(args).values()):
        _demo()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
