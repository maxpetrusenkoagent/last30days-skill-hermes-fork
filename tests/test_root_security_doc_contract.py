"""Contract tests for the root `SECURITY.md` threat model.

`SECURITY.md` makes code-checkable claims about credential sources, network
destinations, and CI enforcement. These tests fail when the document drifts
from the repository it describes.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECURITY = ROOT / "SECURITY.md"


def _security() -> str:
    return SECURITY.read_text(encoding="utf-8")


def test_credential_sources_name_real_setup_scripts():
    security = _security()
    scripts = ROOT / "skills" / "last30days" / "scripts"
    for name in ("setup-keychain.sh", "setup-pass.sh"):
        assert (scripts / name).is_file()
        assert f"skills/last30days/scripts/{name}" in security


def test_network_destinations_name_dynamic_and_local_surfaces():
    security = _security()
    assert "bsky.social" in security
    assert "api.bsky.app" in security
    assert "BSKY_SEARCH_HOST" in security
    assert "XIAOHONGSHU_API_BASE" in security
    assert "http://localhost:18060" in security
    assert "http://host.docker.internal:18060" in security
    assert "HTTPS webhook" in security
    assert "It never sends data to endpoints other than the ones listed below" not in security


def test_secret_file_permission_warning_is_described_as_non_blocking():
    security = _security()
    assert "non-blocking warning" in security
    assert "group or other users can read" in security
    assert "continues loading" in security
    assert "secret files must be `0600`" not in security


def test_ci_enforcement_levels_match_the_workflows():
    security = _security()
    assert "TruffleHog" in security
    assert "Semgrep SAST scan" in security
    assert "continue-on-error" in security
    assert "Scorecard" in security
    assert "OSV-Scanner" in security
    assert "Every commit and pull request runs through CI that includes" not in security
