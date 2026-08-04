from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    logs: Path
    evidence: Path
    backups: Path
    firmware: Path
    settings: Path
    registration: Path

    @classmethod
    def resolve(cls) -> "AppPaths":
        system = platform.system()
        if system == "Windows":
            root = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "THETECHGUY" / "Huawei"
        elif system == "Darwin":
            root = Path.home() / "Library" / "Application Support" / "THETECHGUY" / "Huawei"
        else:
            root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "thetechguy" / "huawei"
        paths = cls(
            root=root,
            logs=root / "logs",
            evidence=root / "evidence",
            backups=root / "backups",
            firmware=root / "firmware",
            settings=root / "settings.json",
            registration=root / "registration.json",
        )
        for directory in (paths.root, paths.logs, paths.evidence, paths.backups, paths.firmware):
            directory.mkdir(parents=True, exist_ok=True)
        return paths
