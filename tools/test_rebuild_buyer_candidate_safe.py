"""안전 구매자 재생성 도구의 핵심 회귀 테스트."""

from __future__ import annotations

import pandas as pd
import pytest

from merge_p1_p2_buyer_sources import BUYER_COLUMNS
from rebuild_buyer_candidate_safe import (
    EXPECTED_BUYER_SOURCES,
    rebuild_safe_outputs,
    validate_expected_counts,
    write_outputs,
)


def _row(
    source: str,
    row_no: int,
    *,
    name: str,
    country: str = "미국",
    email: str = "",
    estimated: str = "False",
    record_type: str = "buyer_candidate",
) -> dict[str, str]:
    row = {column: "" for column in BUYER_COLUMNS}
    row.update(
        {
            "record_type": record_type,
            "source_dataset": source,
            "source_file": f"{source}.csv",
            "source_row_no": str(row_no),
            "title": name,
            "normalized_name": name,
            "country_raw": country,
            "country_norm": country,
            "contact_email": email,
            "contact_email_estimated": estimated,
            "has_contact": "True" if email else "False",
        }
    )
    return row


def _fixture_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sources = sorted(EXPECTED_BUYER_SOURCES)
    baseline_rows = [
        _row(
            sources[0],
            1,
            name="Verified Buyer",
            email="verified@buyer.example",
        ),
        _row(
            sources[1],
            2,
            name="Estimated Buyer",
            email="estimate@portal.example",
            estimated="True",
        ),
        _row(
            sources[2],
            3,
            name="Second Estimated",
            email="second@estimate.example",
            estimated="True",
        ),
        _row(sources[3], 4, name="Buyer Four"),
        _row(sources[4], 5, name="Buyer Five"),
        _row(sources[5], 6, name="Buyer Six"),
        _row(
            "대한무역투자진흥공사_buyKOREA인콰이어리",
            7,
            name="Inquiry One",
        ),
        _row(
            "중소벤처기업진흥공단_GoBizKorea인콰이어리",
            8,
            name="Inquiry Two",
        ),
    ]
    baseline = pd.DataFrame(baseline_rows, columns=BUYER_COLUMNS)
    reduced = pd.DataFrame(
        [
            _row(
                sources[1],
                2,
                name="Estimated Buyer",
                email="estimate@portal.example",
            )
        ],
        columns=BUYER_COLUMNS,
    )
    opportunity = pd.DataFrame(
        [
            _row(
                "기존_기회",
                1,
                name="Existing Opportunity",
                record_type="opportunity_item",
            )
        ],
        columns=BUYER_COLUMNS,
    )
    return baseline, reduced, opportunity


def test_rebuild_preserves_sources_and_separates_only_inquiries() -> None:
    baseline, reduced, opportunity = _fixture_frames()
    baseline_before = baseline.copy(deep=True)

    result = rebuild_safe_outputs(baseline, reduced, opportunity)

    assert len(result.buyer) == 6
    assert set(result.buyer["source_dataset"]) == EXPECTED_BUYER_SOURCES
    assert result.report["inquiry_separation"]["moved_from_buyer"] == 2
    assert len(result.opportunity) == 3
    pd.testing.assert_frame_equal(baseline, baseline_before)


def test_rebuild_quarantines_estimated_and_keeps_verified_email() -> None:
    baseline, reduced, opportunity = _fixture_frames()

    result = rebuild_safe_outputs(baseline, reduced, opportunity)

    assert len(result.estimated_quarantine) == 2
    assert len(result.restored_assignment_quarantine) == 1
    safe_emails = set(
        result.buyer.loc[
            result.buyer["contact_email"].ne(""), "contact_email"
        ]
    )
    assert safe_emails == {"verified@buyer.example"}
    assert (
        result.report["email_quarantine"]["restored_assignment_audit"][
            "matched_estimated"
        ]
        == 1
    )


def test_rebuild_fails_when_required_source_is_missing() -> None:
    baseline, reduced, opportunity = _fixture_frames()
    baseline = baseline[
        baseline["source_dataset"] != sorted(EXPECTED_BUYER_SOURCES)[0]
    ]

    with pytest.raises(ValueError, match="필수 구매자 출처"):
        rebuild_safe_outputs(baseline, reduced, opportunity)


def test_expected_counts_fail_closed() -> None:
    baseline, reduced, opportunity = _fixture_frames()
    result = rebuild_safe_outputs(baseline, reduced, opportunity)

    validate_expected_counts(
        result,
        expected_baseline_rows=8,
        expected_restored_estimated=1,
    )
    with pytest.raises(ValueError, match="기준 구매자 행 수"):
        validate_expected_counts(
            result,
            expected_baseline_rows=9,
            expected_restored_estimated=1,
        )
    with pytest.raises(ValueError, match="복원 추정 이메일 수"):
        validate_expected_counts(
            result,
            expected_baseline_rows=8,
            expected_restored_estimated=2,
        )


def test_writer_never_overwrites_existing_safe_outputs(
    tmp_path,
) -> None:
    baseline, reduced, opportunity = _fixture_frames()
    result = rebuild_safe_outputs(baseline, reduced, opportunity)
    protected = tmp_path / "buyer_candidate.csv"
    protected.write_text("original", encoding="utf-8")

    paths = write_outputs(
        result,
        tmp_path / "safe",
        protected_inputs=[protected],
    )
    assert protected.read_text(encoding="utf-8") == "original"
    assert len(paths) == 5

    with pytest.raises(FileExistsError):
        write_outputs(
            result,
            tmp_path / "safe",
            protected_inputs=[protected],
        )
