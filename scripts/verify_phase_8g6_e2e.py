"""Exercise one synthetic backend run through FastAPI and Flutter Live Mode.

The Python side uses an isolated temporary SQLite file and FastAPI TestClient.
Flutter's real API repository receives the exact JSON bodies returned by that
API through its injected test HTTP client. No application server, target, or
external service is contacted.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from argon2 import PasswordHasher

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from aegiscore.api import create_app
from aegiscore.api.auth import AuthSettings
from aegiscore.evaluation import (
    AdjudicationState,
    CanonicalLocus,
    EvaluationCaseManifestRecord,
    GroundTruthRecord,
    GroundTruthStatus,
    InclusionStatus,
    RunnerCondition,
)
from aegiscore.evaluation_harness import (
    EvaluationHarness,
    RunnerConditionRegistry,
    create_orchestration_replay_adapter,
)
from aegiscore.local_persistence import LocalRecordStore


FRONTEND = ROOT / "frontend"
FLUTTER_TEST = "test/phase_8g6_e2e_test.dart"
E2E_USERNAME = "phase8g7-e2e-user"
E2E_PASSWORD = "phase8g7-e2e-local-password"


def _e2e_auth_settings() -> AuthSettings:
    return AuthSettings(
        username=E2E_USERNAME,
        password_hash=PasswordHasher().hash(E2E_PASSWORD),
    )


def _create_synthetic_report(database: Path) -> tuple[str, str, str]:
    locus = CanonicalLocus(
        target_uri="http://127.0.0.1:3000/fixture/item",
        parameter="item_id",
        cwe_id="CWE-89",
    )
    case = EvaluationCaseManifestRecord(
        case_id="CASE-8G6-E2E",
        locus=locus,
        benchmark_target="synthetic-e2e-fixture",
        benchmark_version="1.0",
        vulnerability_class="SQL injection",
        expected_label=GroundTruthStatus.VULNERABLE,
        ground_truth_provenance="synthetic-e2e-test-only",
        review_status=AdjudicationState.ADJUDICATED,
        inclusion_status=InclusionStatus.INCLUDED,
    )
    truth = GroundTruthRecord(
        case_id=case.case_id,
        locus=locus,
        expected_status=GroundTruthStatus.VULNERABLE,
        vulnerability_class="SQL injection",
        evidence_reference="synthetic-e2e-fixture-reference",
        adjudication_state=AdjudicationState.ADJUDICATED,
        provenance="synthetic-e2e-test-only",
    )
    registry = RunnerConditionRegistry()
    registry.register_offline_replay_adapter(
        RunnerCondition.PROPOSED_MULTI_AGENT,
        create_orchestration_replay_adapter("phase-8g6-e2e-runner", [case]),
    )
    report = EvaluationHarness(
        registry=registry,
        record_store=LocalRecordStore.create_or_open(database),
    ).execute(
        RunnerCondition.PROPOSED_MULTI_AGENT,
        [case],
        [truth],
        fixture_dataset_id="phase-8g6-synthetic-e2e",
        fixture_dataset_version="1.0.0",
    )
    if not report.raw_trial_runs[0].result.findings:
        raise RuntimeError("Synthetic E2E fixture did not produce its expected replay finding")
    return report.manifest.manifest_id, case.case_id, report.raw_trial_runs[0].run_id


def _api_body(client: TestClient, url: str, *, expected_status: int = 200) -> Any:
    response = client.get(url)
    if response.status_code != expected_status:
        raise RuntimeError(f"GET {url} returned HTTP {response.status_code}")
    return response.json()


def _collect_api_responses(database: Path) -> dict[str, Any]:
    settings = _e2e_auth_settings()
    app = create_app(local_store_path=database, auth_settings=settings)
    with TestClient(app) as client:
        denied = client.get("/sessions")
        bad_login = client.post(
            "/auth/login",
            json={"username": E2E_USERNAME, "password": "incorrect-e2e-password"},
        )
        if denied.status_code != 401 or bad_login.status_code != 401:
            raise RuntimeError("FastAPI did not reject missing or incorrect credentials")
        login = client.post(
            "/auth/login",
            json={"username": E2E_USERNAME, "password": E2E_PASSWORD},
        )
        if login.status_code != 200:
            raise RuntimeError("FastAPI local authentication did not accept the test account")
        token = login.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("FastAPI returned an invalid test session")
        client.headers["Authorization"] = f"Bearer {token}"
        auth_session = _api_body(client, "/auth/session")
        if auth_session.get("authenticated") is not True:
            raise RuntimeError("FastAPI did not validate the issued bearer session")

        health = _api_body(client, "/health")
        storage = _api_body(client, "/storage/status")
        summary = _api_body(client, "/dashboard/summary")
        sessions_page = _api_body(client, "/sessions?offset=0&limit=10")
        findings_page = _api_body(client, "/findings?offset=0&limit=100")
        reports_page = _api_body(client, "/reports?offset=0&limit=100")
        if storage["status"] != "available":
            raise RuntimeError("Persisted store was not available to the API")
        if sessions_page["total"] != 1 or reports_page["total"] != 1:
            raise RuntimeError("API pages did not contain the persisted workflow output")
        if findings_page["total"] < 1 or summary["empirical_run_count"] != 0:
            raise RuntimeError("API outputs lost findings or synthetic provenance")

        session = sessions_page["items"][0]
        finding = findings_page["items"][0]
        report = reports_page["items"][0]
        if (
            session["report_id"] != report["report_id"]
            or finding["session_id"] != session["session_id"]
            or finding["report_id"] != report["report_id"]
            or session["is_synthetic"] is not True
            or session["is_empirical"] is not False
            or report["is_synthetic"] is not True
            or report["is_empirical"] is not False
        ):
            raise RuntimeError("Persisted identifiers or provenance disagree across API records")

        paths = {
            "_test_access_token": token,
            "/api/auth/session": auth_session,
            "/api/health": health,
            "/api/storage/status": storage,
            "/api/dashboard/summary": summary,
            "/api/sessions?offset=0&limit=10": sessions_page,
            f"/api/sessions/{session['session_id']}": _api_body(
                client, f"/sessions/{session['session_id']}"
            ),
            "/api/findings?offset=0&limit=100": findings_page,
            f"/api/findings/{finding['finding_id']}": _api_body(
                client, f"/findings/{finding['finding_id']}"
            ),
            "/api/reports?offset=0&limit=100": reports_page,
            f"/api/reports/{report['report_id']}": _api_body(
                client, f"/reports/{report['report_id']}"
            ),
        }

    # Recreate the app and store reader to model a process restart. The same
    # persisted identifiers and details must remain retrievable.
    with TestClient(create_app(local_store_path=database, auth_settings=settings)) as restarted_client:
        stale = restarted_client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        if stale.status_code != 401:
            raise RuntimeError("App recreation did not invalidate its in-memory session")
        restarted_login = restarted_client.post(
            "/auth/login",
            json={"username": E2E_USERNAME, "password": E2E_PASSWORD},
        )
        restarted_client.headers["Authorization"] = (
            f"Bearer {restarted_login.json()['access_token']}"
        )
        restarted_session = _api_body(
            restarted_client, f"/sessions/{session['session_id']}"
        )
        restarted_report = _api_body(
            restarted_client, f"/reports/{report['report_id']}"
        )
    if (
        restarted_session["run_id"] != session["run_id"]
        or restarted_session["result"] != session["result"]
        or restarted_report["report_id"] != report["report_id"]
        or restarted_report["payload"] != paths[f"/api/reports/{report['report_id']}"]["payload"]
    ):
        raise RuntimeError("Stored records changed across API service recreation")

    return paths


def _run_flutter_test(bundle_path: Path) -> None:
    flutter = shutil.which("flutter")
    if flutter is None:
        raise RuntimeError("Flutter executable is not on PATH")
    environment = os.environ.copy()
    environment["AEGISCORE_PHASE_8G6_E2E_BUNDLE"] = str(bundle_path)
    command = [flutter, "test", "--reporter=expanded", "--timeout=30s", FLUTTER_TEST]
    if os.name == "nt" and Path(flutter).suffix.lower() in {".bat", ".cmd"}:
        command = ["cmd.exe", "/d", "/c", *command]
    result = subprocess.run(command, cwd=FRONTEND, env=environment, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aegiscore-8g6-e2e-") as temporary:
        temporary_path = Path(temporary)
        database = temporary_path / "records.sqlite3"
        manifest_id, case_id, run_id = _create_synthetic_report(database)
        responses = _collect_api_responses(database)
        access_token = str(responses.pop("_test_access_token"))
        bundle = temporary_path / "fastapi-responses.json"
        bundle.write_text(
            json.dumps(
                {
                    "responses": responses,
                    "expected": {
                        "manifest_id": manifest_id,
                        "case_id": case_id,
                        "run_id": run_id,
                        "access_token": access_token,
                        "username": E2E_USERNAME,
                    },
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print(
            "Python E2E stage passed: authenticated FastAPI reads, denied unauthenticated/"
            "incorrect credentials, temporary SQLite, and session revocation on service recreation."
        )
        _run_flutter_test(bundle)
    print(
        "Phase 8G.7 end-to-end path passed: Flutter restored the tested bearer session, "
        "sent it with API reads, and rendered the actual FastAPI session, finding, and report bodies."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
