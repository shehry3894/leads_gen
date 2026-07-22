"""
Shared pytest fixtures.

Keep this file thin: fixtures belong here only when they're used by more
than one test module. Test-specific setup goes in the test file itself.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def machine_fingerprint() -> str:
    """Real fingerprint for this machine — used by license tests that need
    a key the LicenseManager will accept."""
    from leads_gen.licensing.fingerprint import generate_machine_fingerprint

    return generate_machine_fingerprint()


@pytest.fixture
def isolated_license_key(tmp_path, monkeypatch):
    """
    Redirect LicenseManager's license file to a tmp path so tests can
    write/delete license keys without touching the real leads_gen/license.key.

    Yields the tmp path (which does NOT exist yet — tests write to it
    when they want a specific license key on disk).
    """
    from leads_gen.licensing import license_manager as lm_mod

    tmp_key = tmp_path / "license.key"

    def _get_license_path(self):
        return tmp_key

    monkeypatch.setattr(lm_mod.LicenseManager, "get_license_path", _get_license_path)
    yield tmp_key


@pytest.fixture
def clean_env(monkeypatch):
    """Remove any HEADLESS_MODE / CHROMEDRIVER_PATH env vars for the test."""
    monkeypatch.delenv("HEADLESS_MODE", raising=False)
    monkeypatch.delenv("CHROMEDRIVER_PATH", raising=False)
    yield


@pytest.fixture
def tmp_output_dir(tmp_path, monkeypatch):
    """
    Point leads_gen.utils.paths.get_output_dir() at a tmp dir so pipeline
    tests write their Excel files somewhere disposable.
    """
    from leads_gen.utils import paths

    out = tmp_path / "output"
    out.mkdir()
    monkeypatch.setattr(paths, "get_output_dir", lambda: out)
    yield out


@pytest.fixture
def real_license_key_file():
    """
    Backs up leads_gen/license.key before the test and restores it after.
    The test can freely delete/overwrite it. Yields the Path.

    Needed by tests that spawn a subprocess (CLI or Streamlit) since
    monkeypatching LicenseManager doesn't cross the process boundary.
    """
    key_path = PROJECT_ROOT / "leads_gen" / "license.key"
    backup = key_path.read_bytes() if key_path.exists() else None
    try:
        yield key_path
    finally:
        if backup is not None:
            key_path.write_bytes(backup)
        elif key_path.exists():
            key_path.unlink()


def _wait_for_http_ok(url: str, deadline: float, proc: subprocess.Popen) -> None:
    """Poll until GET url returns 200 or deadline passes.
    Raises if the subprocess dies before readiness."""
    import requests

    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read().decode(errors="replace") if proc.stdout else ""
            raise RuntimeError(f"Subprocess exited early:\n{out}")
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(0.4)
    raise RuntimeError(f"Timed out waiting for {url}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def streamlit_server(project_root):
    """
    Spawn `streamlit run app.py` on a free port for the whole session, with
    LEADS_GEN_TESTING=true so the "scrape" returns demo data instead of
    hitting Google Maps.

    Yields the base URL (e.g. http://127.0.0.1:8599). Teardown terminates
    the subprocess.
    """
    port = _free_port()
    url = f"http://127.0.0.1:{port}"

    env = os.environ.copy()
    env["LEADS_GEN_TESTING"] = "true"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    proc = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            "app.py",
            "--server.port",
            str(port),
            "--server.address",
            "127.0.0.1",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
            "--server.runOnSave",
            "false",
        ],
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_http_ok(url, time.time() + 60, proc)
    except Exception:
        proc.terminate()
        raise

    yield url

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture
def ui_browser():
    """
    Chrome for driving the Streamlit UI.

    Headless by default. Set ``UI_HEADLESS=false`` to watch the browser
    interact with the app (useful for debugging selectors or seeing what
    the flow actually looks like).
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    headless = os.environ.get("UI_HEADLESS", "true").lower() not in ("false", "0", "no")

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1400,1000")

    driver_path = os.environ.get("CHROMEDRIVER_PATH") or ChromeDriverManager().install()
    driver = webdriver.Chrome(service=Service(driver_path), options=opts)
    driver.set_page_load_timeout(30)
    try:
        yield driver
    finally:
        driver.quit()
