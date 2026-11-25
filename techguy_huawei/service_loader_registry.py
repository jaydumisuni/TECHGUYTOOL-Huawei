from __future__ import annotations

"""Exact chip-to-service-loader resolution; never transmits bootloader bytes.

A loader being available is NOT evidence that the Kirin USB service-entry
transport is certified on the attached phone. Firmware flash in an already
unlocked Fastboot session does not need a new service loader.
"""

from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
import json
import re

SCHEMA = "techguy.huawei.service-loader-registry.v1"
# Immutable, locally source-verified approval. A manifest edit by itself
# must not qualify another loader or replace these images.
QUALIFIED = {
    "kirin980": {
        "cpu": "hisi980",
        "xloader.img": "419abd240088c7b5cbc5a99d74402f77534328b4fd97964c45e4a942baf19d9b",
        "uce.img": "6a5bf1e70eb525f16785a98ea54d937ebf5069a2fcb52b1411fbbaa559361190",
        "fastboot.img": "f46cb0e80c47592a5ee2c3a82d824f8cd7914ca5e1b1eca05b1c17205cfff7b2",
    },
}


@dataclass(frozen=True)
class LoaderSelection:
    chipset: str
    status: str
    cpu: str = ""
    stage: str = ""
    transport: str = ""
    loader_root: str = ""
    image_names: tuple[str, ...] = ()
    transport_proven: bool = False
    reason: str = ""
    candidate_families: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _inventory_candidate(app_root: Path, selected: str) -> LoaderSelection:
    """Find owner-held container assets without guessing silicon variants or transmitting them."""
    try:
        data=json.loads((app_root/"data"/"kirin_loader_inventory.json").read_text(encoding="utf8"))
        if data.get("schema")!="techguy.huawei.kirin-loader-inventory.v1":
            raise ValueError("schema")
        source=(app_root/data["relative_source"]).resolve()
        if app_root.resolve() not in source.parents:
            raise ValueError("source escapes project")
        families={row["cpu"]:row for row in data["families"]}
    except (OSError,ValueError,KeyError,TypeError):
        return LoaderSelection(selected,"no_qualified_loader",reason="No verified inventory for chipset")
    cpu=selected.replace("kirin","hisi",1) if selected.startswith("kirin") else selected
    if cpu in {"hisi650","hisi655","hisi658","hisi659","hisi65x"}:
        candidates=tuple(x for x in ("hisi65x_a","hisi65x_b") if x in families)
    elif cpu=="hisi620":
        candidates=tuple(x for x in ("hisi620","hisi620c") if x in families)
    elif cpu=="hisi710":
        candidates=tuple(x for x in ("hisi710","hisi710a") if x in families)
    else:
        candidates=(cpu,) if cpu in families else ()
    if not candidates:
        return LoaderSelection(selected,"no_qualified_loader",reason="No matching loader in inventory")
    if len(candidates)!=1:
        return LoaderSelection(selected,"loader_variant_required",reason="Select exact board/loader variant; no automatic cross-variant selection",candidate_families=candidates)
    cpu=candidates[0]
    folder=source/cpu
    verified=[]
    for item in families[cpu]["files"]:
        name=item["name"]
        if not re.fullmatch(r"[a-z0-9_]+\.ktl",name):
            return LoaderSelection(selected,"registry_invalid",reason="Invalid container filename")
        file=folder/name
        if not file.is_file() or file.is_symlink():
            return LoaderSelection(selected,"loader_files_missing",cpu,reason="Missing "+name)
        if file.stat().st_size!=item["bytes"] or sha256(file.read_bytes()).hexdigest()!=item["sha256"]:
            return LoaderSelection(selected,"loader_hash_mismatch",cpu,reason="Integrity mismatch "+name)
        verified.append(name)
    return LoaderSelection(selected,"verified_container_available",cpu,"service-loader-container",
        "HUAWEI USB COM 1.0",str(folder),tuple(verified),False,
        "Existing owner-held loader containers verified; native stage adapter not qualified.",
        candidates)


def resolve_loader(app_root: Path, chipset: str) -> LoaderSelection:
    selected = chipset.strip().lower().replace(" ", "")
    if not selected:
        return LoaderSelection("", "awaiting_chipset", reason="Select/detect a chipset")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", selected):
        return LoaderSelection(selected, "invalid_chipset", reason="Invalid chipset")
    registry = app_root / "data" / "service_loader_profiles.json"
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        return LoaderSelection(selected, "registry_unavailable", reason=type(exc).__name__)
    if payload.get("schema") != SCHEMA or not isinstance(payload.get("profiles"), list):
        return LoaderSelection(selected, "registry_invalid", reason="Loader registry schema mismatch")
    matching = [p for p in payload["profiles"] if isinstance(p, dict) and p.get("chipset") == selected]
    if not matching or selected not in QUALIFIED:
        return _inventory_candidate(app_root,selected)
    if len(matching) != 1:
        return LoaderSelection(selected, "registry_invalid", reason="Ambiguous chipset-to-loader mapping")
    profile = matching[0]
    cpu = str(profile.get("cpu", ""))
    stage = str(profile.get("stage", ""))
    if (not re.fullmatch(r"hisi[0-9]{3,4}", cpu)
            or cpu != QUALIFIED[selected]["cpu"] or stage != "service-fastboot"):
        return LoaderSelection(selected, "registry_invalid", reason="Unsupported loader type/stage")
    sources = profile.get("files")
    if not isinstance(sources, list) or not sources:
        return LoaderSelection(selected, "registry_invalid", reason="No loader images registered")
    # The Builder includes runtime/. The registry is an allowlist: no path
    # from the selected chipset or user input is used as an executable path.
    root = app_root / "runtime" / "service-loaders" / cpu
    verified: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            return LoaderSelection(selected, "registry_invalid", reason="Malformed loader entry")
        name = str(source.get("name", ""))
        expected = str(source.get("sha256", "")).lower()
        length = source.get("bytes")
        if (name not in {"xloader.img", "uce.img", "fastboot.img"}
                or not re.fullmatch(r"[0-9a-f]{64}", expected)
                or expected != QUALIFIED[selected].get(name)):
            return LoaderSelection(selected, "registry_invalid", reason="Invalid loader image declaration")
        if name in verified:
            return LoaderSelection(selected, "registry_invalid", reason="Duplicate loader image")
        path = root / name
        if not path.is_file() or path.is_symlink():
            return LoaderSelection(selected, "loader_files_missing", cpu, stage,
                                   reason=f"Missing {name}")
        if path.stat().st_size != length:
            return LoaderSelection(selected, "loader_hash_mismatch", cpu, stage,
                                   reason=f"Unexpected size for {name}")
        hasher = sha256()
        with path.open("rb") as content:
            for block in iter(lambda: content.read(1024 * 1024), b""):
                hasher.update(block)
        if hasher.hexdigest() != expected:
            return LoaderSelection(selected, "loader_hash_mismatch", cpu, stage,
                                   reason=f"SHA-256 mismatch for {name}")
        verified.append(name)
    if set(verified) != {"xloader.img", "uce.img", "fastboot.img"}:
        return LoaderSelection(selected, "registry_invalid", cpu, stage,
                               reason="Incomplete service-Fastboot loader stage")
    return LoaderSelection(
        chipset=selected, status="verified_images_unstaged", cpu=cpu,
        stage=stage, transport=str(profile.get("transport", "")),
        loader_root=str(root), image_names=tuple(verified),
        transport_proven=profile.get("usb_stage_transport_proven") is True,
        reason="Exact chipset images selected and hash-verified; not transmitted to device",
    )
