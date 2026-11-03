"""Stage the patched CPython 3.14 runtime without touching an installed application.

Only upstream, SHA-256-pinned artifacts are extracted. The old source runtime is
retained until release verification has completed. Run with a separate Python.
"""

import hashlib
import json
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

WORK = Path(__file__).resolve().parent
STAGE = WORK / "runtime-3.14.10-staging"
CACHE = WORK / "runtime-downloads"
ARTIFACTS = [
    (
        "CPython",
        "3.14.10",
        "https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-amd64.zip",
        "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159",
        "PSF-2.0 and included component notices",
    ),
    (
        "numpy",
        "2.5.4",
        "https://files.pythonhosted.org/packages/52/9a/e1e512ebc948d5b9dd33b08736760f0ebbed2848fd4eda1f553088a6dcee/numpy-2.5.4-cp314-cp314-win_amd64.whl",
        "2ca144f15135b6212a5c47b1e2aeca6e412f102f95a2d5d88d8aec77eb255de3",
        "BSD-3-Clause and bundled component licenses",
    ),
    (
        "zstandard",
        "0.25.0",
        "https://files.pythonhosted.org/packages/3a/43/241f9615bcf8ba8903b3f0432da069e857fc4fd1783bd26183db53c4804b/zstandard-0.25.0-cp314-cp314-win_amd64.whl",
        "c19bcdd826e95671065f8692b5a4aa95c52dc7a02a4c5a0cac46deb879a017a2",
        "BSD and included component notices",
    ),
    (
        "Pillow",
        "13.0.0",
        "https://files.pythonhosted.org/packages/50/e2/7ad17747517e4c813dca78257d6bb593466f8231baf1384bc98d92745edb/pillow-13.0.0-cp314-cp314-win_amd64.whl",
        "f7cbb7a64e7ec664775195e4f81923bc8a93d9451b963f844e59118f63147a7a",
        "HPND and included component notices",
    ),
    (
        "capstone",
        "5.0.9",
        "https://files.pythonhosted.org/packages/50/e6/6f06fdb6a9ed32b2f7cd9c036b92d5324112c3ef7080f2c71efc367d40dd/capstone-5.0.9-py3-none-win_amd64.whl",
        "732cedbbb56d42e723f14d7af6387f1454194a820b4b96b56d1e53f865ef85d0",
        "BSD and included component notices",
    ),
]


def main():
    current = WORK / "installer/runtime"
    if (current / "DISTRIBUTION.json").is_file():
        installed = json.loads(
            (current / "DISTRIBUTION.json").read_text(encoding="utf-8")
        )
        if installed["artifacts"][0]["version"] == "3.14.10":
            subprocess.run(
                [
                    str(current / "python.exe"),
                    "-B",
                    "-c",
                    "import numpy,zstandard,capstone,PIL,ssl",
                ],
                check=True,
            )
            print("Pinned runtime already prepared")
            return
    CACHE.mkdir(exist_ok=True)
    STAGE.mkdir(exist_ok=False)
    records = []
    for name, version, url, digest, license_name in ARTIFACTS:
        archive = CACHE / url.rsplit("/", 1)[-1]
        if (
            not archive.exists()
            or hashlib.sha256(archive.read_bytes()).hexdigest() != digest
        ):
            temporary = archive.with_suffix(archive.suffix + ".download")
            with urllib.request.urlopen(url, timeout=60) as response:
                temporary.write_bytes(response.read())
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
                raise ValueError(f"SHA-256 mismatch: {archive.name}")
            temporary.replace(archive)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
            raise ValueError(f"SHA-256 mismatch: {archive.name}")
        target = STAGE if name == "CPython" else STAGE / "Lib/site-packages"
        with zipfile.ZipFile(archive) as package:
            for entry in package.infolist():
                parts = Path(entry.filename).parts
                if entry.is_dir() or {"tests", "__pycache__"}.intersection(parts):
                    continue
                destination = (target / entry.filename).resolve()
                if not destination.is_relative_to(target.resolve()):
                    raise ValueError("Unsafe archive member")
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(package.read(entry))
        records.append(
            dict(
                name=name, version=version, url=url, sha256=digest, license=license_name
            )
        )

    (STAGE / "python314._pth").write_text(
        "python314.zip\n.\nLib/site-packages\nimport site\n", encoding="ascii"
    )
    (STAGE / "Lib/site-packages/opensmash_scriptdir.pth").write_text(
        "import sys,pathlib; sys.path.insert(0,str(pathlib.Path(sys.argv[0]).resolve().parent)) if sys.argv and pathlib.Path(sys.argv[0]).is_file() else None\n",
        encoding="ascii",
    )
    (STAGE / "DISTRIBUTION.json").write_text(
        json.dumps(
            dict(
                artifacts=records,
                changes="Isolated search path and running script directory enabled; package tests and bytecode caches omitted. No system installation or pip bundled.",
            ),
            indent=2,
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            str(STAGE / "python.exe"),
            "-B",
            "-c",
            "import sys,numpy,zstandard,capstone,PIL,ssl,sqlite3;print(sys.version); print(ssl.OPENSSL_VERSION); print(sqlite3.sqlite_version)",
        ],
        check=True,
    )
    backup = WORK / "runtime-before-3.3.0"
    if backup.exists():
        raise ValueError("Previous runtime backup exists; review it before replacing")
    if current.exists():
        current.rename(backup)
    try:
        STAGE.rename(current)
    except OSError:
        if backup.exists():
            backup.rename(current)
        raise


if __name__ == "__main__":
    main()
