"""Capture real local predict JSON and timings; never contacts deployed servers.

Run before changing code with --capture, then without it to compare. Authentication
is overridden locally; country/buyer scoring uses the repository's actual CSVs.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
import sys
import subprocess
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "services/p1-export-fit-api"
FIXTURES = API / "tests/fixtures/predict_golden"
BASE_SHA = "09ae2f7c49da503c9be221e85f885434affb42df"


class BaselineLoader(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Execute original modules from Git without modifying any worktree files."""

    sources = {
        "main": "services/p1-export-fit-api/main.py",
        "app.services.data_loaders": "services/p1-export-fit-api/app/services/data_loaders.py",
        "task06_fit_score": "services/cosmetics_mvp_preprocess/task06_fit_score.py",
        "shortlist_service": "services/cosmetics_mvp_preprocess/shortlist_service.py",
    }

    def find_spec(self, fullname, path=None, target=None):
        if fullname in self.sources:
            return importlib.util.spec_from_file_location(
                fullname, ROOT / self.sources[fullname], loader=self,
            )

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = subprocess.check_output([
            "git", "-C", str(ROOT), "show", f"{BASE_SHA}:{self.sources[module.__name__]}",
        ])
        exec(compile(source, module.__file__, "exec"), module.__dict__)


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--baseline", action="store_true", help="Execute original 09ae2f7 code from Git")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.capture:
        # Never replace the original golden JSON with results from optimized
        # code while labelling them as the original main snapshot.
        subprocess.run([
            "git", "-C", str(ROOT), "diff", "--quiet", BASE_SHA, "--",
            "services/p1-export-fit-api/main.py", "services/p1-export-fit-api/app",
            "services/cosmetics_mvp_preprocess/task05_shortlist.py",
            "services/cosmetics_mvp_preprocess/task06_fit_score.py",
            "services/cosmetics_mvp_preprocess/task08_recommendation.py",
            "services/cosmetics_mvp_preprocess/shortlist_service.py",
        ], check=True)
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = ""
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(API))
    os.chdir(API)
    if args.baseline:
        sys.meta_path.insert(0, BaselineLoader())
    from fastapi.testclient import TestClient
    from app.auth_deps import get_current_user
    import main as api
    from app.services import buyer_shortlist

    reference_date = date.today().isoformat() if args.capture else json.loads(
        (FIXTURES / "manifest.json").read_text(encoding="utf-8")
    )["reference_date"]

    class SnapshotDate(date):
        @classmethod
        def today(cls):
            return date.fromisoformat(reference_date)

    buyer_shortlist.date = SnapshotDate

    api.app.dependency_overrides[get_current_user] = lambda: {"user_id": "mg015-local"}
    client = TestClient(api.app)
    started = time.perf_counter()
    api._warm_predict_data()
    measurements = {"data_load_seconds": time.perf_counter() - started, "requests": []}
    cases = [
        {"hs_code": hs, "exporter_country_iso3": "KOR", "top_n": 5, "year": 2023}
        for hs in ("330499", "854140", "210690", "620343")
    ]
    cases.append({**cases[0], "top_n": 3, "filters": {"exclude_countries_iso3": ["USA"], "min_trade_value_usd": 1000}})
    for index, payload in enumerate(cases):
        name = payload["hs_code"] + ("_filters" if index == 4 else "")
        expected = None if args.capture else json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["response"]
        for attempt in ("first", "repeat"):
            started = time.perf_counter()
            response = client.post("/v1/predict", json=payload)
            elapsed = time.perf_counter() - started
            response.raise_for_status()
            content = response.json()
            content.pop("request_id")
            content.pop("timestamp")
            if attempt == "first" and args.capture:
                FIXTURES.mkdir(parents=True, exist_ok=True)
                (FIXTURES / f"{name}.json").write_text(json.dumps({"request": payload, "response": content}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                expected = content
            assert content == expected, f"golden mismatch: {name}/{attempt}"
            measurement = {"case": name, "attempt": attempt, "seconds": elapsed, "countries": len(content["data"]["results"]), "buyers": len(content["data"]["buyers"]["items"])}
            measurements["requests"].append(measurement)
            print(json.dumps(measurement), flush=True)
    if args.capture:
        paths = ["services/cosmetics_mvp_preprocess/output/buyer_candidate.csv", "services/cosmetics_mvp_preprocess/output/opportunity_item.csv"]
        from app.config import Files
        paths += [(Path("services/p1-export-fit-api") / getattr(Files, key)).as_posix() for key in ("KOTRA_RECO", "MOFA_ISO3", "TRADE", "WB_GDP", "WB_GDP_GROWTH", "DISTANCE")]
        hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}
        opportunity = "services/cosmetics_mvp_preprocess/output/opportunity_item.csv"
        (FIXTURES / "opportunity_item.csv").write_bytes((ROOT / opportunity).read_bytes())
        manifest = {"base_sha": BASE_SHA, "reference_date": reference_date,
                    "fixture_overrides": {opportunity: "opportunity_item.csv"}, "data_sha256": hashes}
        (FIXTURES / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.resolve().write_text(json.dumps(measurements, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
