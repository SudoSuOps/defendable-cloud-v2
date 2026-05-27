from app.checks import run_checks
from app.hashing import canonical, sha256_hex
from app.receipts import build_payload, render_pdf


def test_checks_dataset_pass():
    results, verdict = run_checks(
        "dataset",
        {"source": "internal", "row_count": 100},
        [{"kind": "note", "label": "n", "sha256": "abc"}],
    )
    keys = {r.check_key for r in results}
    assert "dataset_rows" in keys
    assert "evidence_present" in keys
    assert verdict.outcome == "pass"


def test_checks_dataset_fail_missing_fields():
    results, verdict = run_checks("dataset", {}, [])
    assert verdict.outcome == "fail"
    assert verdict.checks_failed >= 1


def test_receipt_payload_and_pdf():
    payload = build_payload(
        receipt_id="DCR-000000-abcd1234",
        org_seq=0,
        parent_hash="0" * 64,
        created_at="2026-05-27T00:00:00Z",
        org={"id": "o1", "name": "Acme"},
        project={"id": "p1", "name": "Pilot"},
        run={"id": "r1", "lane": "compute", "title": "RTX 5090 smash", "inputs": {"machine": "rig-1", "benchmark_score": 9000}},
        evidence=[{"kind": "log", "label": "bench.log", "sha256": "d" * 64, "content_type": "text/plain", "byte_size": 12}],
        checks=[{"check_key": "compute_score", "label": "Benchmark score is numeric", "category": "math", "status": "pass", "detail": "ok", "score": None}],
        verdict={"outcome": "pass", "summary": "all good", "score": 1.0, "checks_passed": 4, "checks_failed": 0},
        approval={"decision": "approved", "approver_email": "ops@acme.com", "note": "ship it", "created_at": "2026-05-27T00:01:00Z"},
        share_url="https://api.defendablecloud.com/share/tok",
    )
    receipt_sha256 = sha256_hex(canonical(payload))
    assert len(receipt_sha256) == 64
    pdf = render_pdf(payload, receipt_sha256)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 800


def test_app_constructs():
    from app.main import app

    assert app.title == "DefendableCloud API"
    paths = {r.path for r in app.routes}
    assert "/healthz" in paths
    assert "/runs/{run_id}/receipt" in paths
