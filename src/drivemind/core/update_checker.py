from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from drivemind.version import GITHUB_LATEST_API_URL, GITHUB_RELEASES_URL, __version__


SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$")


@dataclass(slots=True)
class UpdateResult:
    ok: bool
    has_update: bool = False
    current_version: str = __version__
    latest_version: str = ""
    release_url: str = GITHUB_RELEASES_URL
    message: str = ""


def parse_version(version: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.match(version.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


def is_newer(latest: str, current: str = __version__) -> bool:
    latest_tuple = parse_version(latest)
    current_tuple = parse_version(current)
    if not latest_tuple or not current_tuple:
        return latest.strip().lstrip("v") != current.strip().lstrip("v")
    return latest_tuple > current_tuple


def should_check_update(frequency: str, last_check: str) -> bool:
    frequency = (frequency or "daily").lower()
    if frequency in {"never", "none", "off", "チェックしない"}:
        return False
    if not last_check:
        return True
    try:
        last = date.fromisoformat(last_check[:10])
    except Exception:
        return True
    today = date.today()
    days = (today - last).days
    if frequency == "daily":
        return days >= 1
    if frequency == "weekly":
        return days >= 7
    if frequency == "monthly":
        return days >= 30
    return True


def check_latest_release(timeout: int = 8) -> UpdateResult:
    request = urllib.request.Request(
        GITHUB_LATEST_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "DriveMind Update Checker",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return UpdateResult(ok=True, has_update=False, message="GitHub Release はまだ公開されていません。")
        return UpdateResult(ok=False, message=f"更新確認に失敗しました: HTTP {exc.code}")
    except Exception as exc:
        return UpdateResult(ok=False, message=f"更新確認に失敗しました: {exc}")

    tag = str(data.get("tag_name") or "").strip()
    html_url = str(data.get("html_url") or GITHUB_RELEASES_URL)
    if not tag:
        return UpdateResult(ok=False, message="Release情報にバージョン番号がありません。")
    return UpdateResult(
        ok=True,
        has_update=is_newer(tag, __version__),
        latest_version=tag,
        release_url=html_url,
        message="新しいバージョンがあります。" if is_newer(tag, __version__) else "最新バージョンです。",
    )


def today_iso() -> str:
    return datetime.now().date().isoformat()


def suppress_today_expired(suppress_date: str) -> bool:
    try:
        return date.fromisoformat(suppress_date[:10]) < date.today()
    except Exception:
        return True
