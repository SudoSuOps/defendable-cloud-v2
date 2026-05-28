"""Smoke tests — the CLI structure works, no API calls made.

We don't test the full network round-trip here (that's phase 2, the e2e
test). These tests assert the structure is intact: the typer app loads, the
help text exists for every subcommand, and the public-verify token extractor
is correct.
"""
from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

# Isolate tests from any real credential file.
os.environ["DEFENDABLE_HOME"] = "/tmp/defendable-cli-test"
os.environ["DEFENDABLE_API"] = "https://api.test.invalid"

from defendablecloud_cli.commands.public import _extract_token  # noqa: E402
from defendablecloud_cli.errors import CLIError  # noqa: E402
from defendablecloud_cli.main import app  # noqa: E402

runner = CliRunner()


def test_root_help_prints_doctrine():
    r = runner.invoke(app, ["--help"])
    assert r.exit_code == 0
    assert "defendable" in r.output.lower()
    # Doctrine line in the help — drift would mean someone rewrote the brand voice.
    assert "rulebook" in r.output.lower()


def test_version_flag():
    r = runner.invoke(app, ["--version"])
    assert r.exit_code == 0
    assert "defendable" in r.output


@pytest.mark.parametrize(
    "group",
    [
        "auth",
        "projects",
        "flight-sheets",
        "runs",
        "evidence",
        "submission",
        "audit",
        "approval",
        "receipt",
        "receipts",
        "ledger",
        "datasets",
        "models",
        "policy",
        "verify",
    ],
)
def test_each_subcommand_group_help(group: str):
    r = runner.invoke(app, [group, "--help"])
    assert r.exit_code == 0, f"--help failed for `defendable {group}`:\n{r.output}"
    assert group in r.output.lower() or len(r.output) > 50


def test_auth_status_no_credentials_exits_2():
    """`defendable auth status` exits 2 when there's no signed-in profile."""
    # Clear any test-local profile.
    creds_dir = os.environ["DEFENDABLE_HOME"]
    creds_file = f"{creds_dir}/credentials.json"
    try:
        os.remove(creds_file)
    except FileNotFoundError:
        pass
    r = runner.invoke(app, ["auth", "status", "--json"])
    assert r.exit_code == 2
    assert "signed_in" in r.output


def test_extract_token_from_full_url():
    t = _extract_token("https://app.defendablecloud.com/r/shr_abc123_xyz")
    assert t == "shr_abc123_xyz"


def test_extract_token_from_path_only():
    t = _extract_token("/r/shr_xyz")
    assert t == "shr_xyz"


def test_extract_token_from_raw_token():
    t = _extract_token("shr_just_a_token")
    assert t == "shr_just_a_token"


def test_extract_token_rejects_garbage():
    with pytest.raises(CLIError):
        _extract_token("this is not a token nor a url")


def test_extract_token_from_api_share_url():
    """Sprint 15 · /share/{token} URLs (the API-side form sealed into cook
    receipts as pin_share_url) must extract the same way as /r/{token}."""
    t = _extract_token("https://api.defendablecloud.com/share/shr_api_xyz")
    assert t == "shr_api_xyz"


def test_receipts_recent_command_registered():
    """The /receipts/recent CLI mirror must surface via `defendable receipts recent`."""
    r = runner.invoke(app, ["receipts", "recent", "--help"])
    assert r.exit_code == 0, f"`receipts recent --help` failed:\n{r.output}"
    out = r.output.lower()
    assert "schema" in out
    assert "limit" in out


def test_receipt_show_command_registered():
    """`defendable receipt show <token>` must surface as a sibling of `generate`."""
    r = runner.invoke(app, ["receipt", "show", "--help"])
    assert r.exit_code == 0, f"`receipt show --help` failed:\n{r.output}"
    assert "share" in r.output.lower() or "token" in r.output.lower()


def test_receipt_renderer_dispatches_on_schema():
    """The shared renderer must cover all 5 known schema prefixes (eval, cook,
    incident, dataset-download, model-pin). If a schema's prefix is missing
    its case here, this test surfaces the gap."""
    from defendablecloud_cli.commands._receipt_render import SCHEMA_LABELS

    required = {
        "defendablecloud.eval",
        "defendablecloud.cook",
        "defendablecloud.incident",
        "defendablecloud.dataset-download",
        "defendablecloud.model-pin",
    }
    missing = required - set(SCHEMA_LABELS.keys())
    assert not missing, (
        f"receipt renderer dispatch missing schema prefixes: {sorted(missing)}. "
        "Add to SCHEMA_LABELS + the dispatch chain in render_public_receipt."
    )


def test_receipts_recent_schema_shortcuts_cover_known_lanes():
    """`defendable receipts recent --schema <shortcut>` must accept all 5
    canonical lane shortcuts so members don't have to type the full URN."""
    from defendablecloud_cli.commands.receipts import SCHEMA_SHORTCUTS

    required = {"eval", "cook", "incident", "download", "pin"}
    missing = required - set(SCHEMA_SHORTCUTS.keys())
    assert not missing, f"receipts recent shortcuts missing: {sorted(missing)}"
    # Each shortcut must map to a full schema URI.
    for short, full in SCHEMA_SHORTCUTS.items():
        assert full.startswith("defendablecloud."), (
            f"shortcut {short!r} maps to non-canonical schema: {full!r}"
        )


def test_locked_doctrine_in_main_module():
    """If someone deletes the doctrine line from main.py's help, the test fails.

    The CLI surface IS the doctrine — every command maps to a wire-locked
    API endpoint. Keep the help text honest.
    """
    import defendablecloud_cli.main as m

    src = m.__doc__ or ""
    assert "rulebook, not a judge" in src
    assert "To the shed" in src or "to the shed" in src
