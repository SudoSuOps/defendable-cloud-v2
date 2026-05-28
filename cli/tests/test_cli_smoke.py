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
        "ledger",
        "datasets",
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


def test_locked_doctrine_in_main_module():
    """If someone deletes the doctrine line from main.py's help, the test fails.

    The CLI surface IS the doctrine — every command maps to a wire-locked
    API endpoint. Keep the help text honest.
    """
    import defendablecloud_cli.main as m

    src = m.__doc__ or ""
    assert "rulebook, not a judge" in src
    assert "To the shed" in src or "to the shed" in src
