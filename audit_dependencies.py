"""Read official release metadata and OSV advisories without changing packages."""

import datetime
import json
import urllib.request
from pathlib import Path

WORK = Path(__file__).resolve().parent


def request(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": "OpenSmash-maintenance-audit",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main():
    runtime = json.loads(
        (WORK / "installer/runtime/DISTRIBUTION.json").read_text(encoding="utf-8")
    )
    packages = []
    for package in runtime["artifacts"]:
        if package["name"] == "CPython":
            continue
        name, version = package["name"], package["version"]
        latest = request(f"https://pypi.org/pypi/{name}/json")
        current = request(f"https://pypi.org/pypi/{name}/{version}/json")
        osv = request(
            "https://api.osv.dev/v1/query",
            {
                "package": {"ecosystem": "PyPI", "name": name.lower()},
                "version": version,
            },
        )
        packages.append(
            dict(
                name=name,
                installed=version,
                latest=latest["info"]["version"],
                pypi_vulnerabilities=current.get("vulnerabilities", []),
                osv_vulnerabilities=osv.get("vulns", []),
            )
        )
    upstream = {}
    for repo in (
        "Raytwo/ARCropolis",
        "HDR-Development/smashline",
        "ultimate-research/nro-hook-plugin",
        "ip7z/7zip",
    ):
        metadata = request(f"https://api.github.com/repos/{repo}/releases/latest")
        upstream[repo] = dict(
            latest=metadata["tag_name"],
            url=metadata["html_url"],
            published=metadata["published_at"],
        )
    report = dict(
        checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        packages=packages,
        external_game_integrations=upstream,
        limitation="Point-in-time advisory lookup, not a guarantee that vulnerabilities do not exist. External game integrations are compatibility pins and are not redistributed or silently upgraded.",
    )
    (WORK / "dependency-audit-3.6.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if any(p["pypi_vulnerabilities"] or p["osv_vulnerabilities"] for p in packages):
        raise SystemExit("Published package advisories require review")


if __name__ == "__main__":
    main()
