from __future__ import annotations

"""Process-safe, UI-independent service request execution.

Non-terminal service operations remain read-first. Terminal write commands
are explicitly confirmed, device-bound and never invoked automatically.
"""

from dataclasses import dataclass
from pathlib import Path

from .action_health import ActionState
from .device_engine import DeviceEngine, DeviceSnapshot, EngineResult
from .evidence import EvidenceJournal
from .live_service import LiveHuaweiService
from .firmware_flash import FlashError, _digest, plan as prepare_generic_plan, apply as execute_generic_plan
from .caz_al10_recovery import BASE_SHA
from .service_loader_registry import resolve_loader
from .terminal_engine import execute_console
from .operation_log import ActionLog, device_read_lines
from typing import Callable


DEVICE_OPERATIONS = frozenset(
    {"read_device", "verlist", "full_oeminfo", "board_repair", "backup_restore"}
)
SERVICE_OPERATIONS = DEVICE_OPERATIONS | {"flash_firmware", "terminal_read", "terminal_write", "fix_drivers", "pair", "huawei_id", "bootloader", "frp_repair"}


@dataclass(frozen=True, slots=True)
class ServiceRequest:
    action_id: str
    project_root: Path
    evidence_journal: Path
    firmware_path: str = ""
    firmware_mode: str = "Upgrade"
    firmware_model: str = ""
    firmware_chipset: str = ""
    firmware_apply: bool = False
    firmware_plan_hash: str = ""
    terminal_line: str = ""
    action_log_dir: Path | None = None
    terminal_approved: bool = False
    terminal_fingerprint: str = ""
    terminal_expected_serial: str = ""
    terminal_working_directory: Path | None = None
    partition_operation: str = ""
    partition_name: str = ""
    partition_source: str = ""
    partition_serial: str = ""
    partition_model: str = ""
    partition_chipset: str = ""
    partition_fingerprint: str = ""
    service_wait: bool = False
    service_expected_serial: str = ""


@dataclass(frozen=True, slots=True)
class ServiceResponse:
    action_id: str
    result: EngineResult
    device_snapshot: DeviceSnapshot | None = None
    log_path: str = ""
    record_path: str = ""
    elapsed_ms: int = 0


def execute(
    request: ServiceRequest,
    progress: Callable[[str], None] | None = None,
    cancel=None,
) -> ServiceResponse:
    """Run in the service worker and persist one distinct log per action."""
    logger = ActionLog(
        request.action_log_dir or request.evidence_journal.parent / "action-logs",
        request.action_id, progress=None if request.action_id == "read_device" else progress,
    )
    snapshot: DeviceSnapshot | None = None
    result: EngineResult
    try:
        if request.action_id not in SERVICE_OPERATIONS:
            result = EngineResult(
                False, "Unknown or unauthorized service operation.", ActionState.GUARDED
            )
        elif request.action_id in {"pair","huawei_id","bootloader","frp_repair"}:
            from .owner_services import run
            engine=DeviceEngine(request.project_root,EvidenceJournal(request.evidence_journal))
            result=run(engine,request.action_id,request.service_expected_serial)
            logger.add(result.message)
        elif request.action_id == "fix_drivers":
            from .driver_inventory import repair
            logger.add("Checking and rediscovering local Windows driver interfaces...")
            result=repair()
            for row in (result.payload or {}).get("interfaces",[]):
                logger.add(f"{row.get('name','USB interface')}: {row.get('status','Unknown')} / {row.get('problem','')}")
            logger.add(result.message)
        elif request.action_id in {"terminal_read", "terminal_write"}:
            logger.add(
                "Executing explicitly confirmed terminal command..."
                if request.terminal_approved else "Executing terminal read command..."
            )
            if request.terminal_working_directory is not None:
                logger.add("Terminal working directory: " + str(request.terminal_working_directory))
            result = execute_console(
                request.project_root,
                request.evidence_journal,
                request.terminal_line,
                approved=request.terminal_approved,
                command_fingerprint=request.terminal_fingerprint,
                expected_serial=request.terminal_expected_serial,
                working_directory=request.terminal_working_directory,
            )
            logger.add(result.message)
        elif request.action_id == "backup_restore" and request.partition_operation:
            from . import partition_service as ps
            engine=DeviceEngine(request.project_root,EvidenceJournal(request.evidence_journal))
            binary=engine._tool("fastboot")
            if not binary:raise FlashError("Local Fastboot runtime unavailable")
            args=(binary,request.partition_serial,request.partition_model,request.partition_chipset,request.partition_name)
            action=request.partition_operation
            root=request.evidence_journal.parent/"partition-backups"
            root.mkdir(parents=True,exist_ok=True)
            if action=="backup":
                payload=ps.backup(*args,Path(request.partition_source) if request.partition_source else root,logger.add)
                result=EngineResult(True,"Partition backup completed and hashed.",ActionState.READY,payload)
            elif action=="erase":
                if request.partition_fingerprint:
                    payload=ps.apply_erase(*args,request.partition_fingerprint,root,logger.add)
                    result=EngineResult(payload["readback_verified"],
                        "Partition erase acknowledged; readback verified." if payload["readback_verified"] else "Erase acknowledged; readback inconclusive.",
                        ActionState.READY if payload["readback_verified"] else ActionState.FAILED,payload)
                else:
                    payload=ps.prepare_erase(*args)
                    result=EngineResult(True,"Review the selected partition and confirm erase.",ActionState.READY,
                        {"partition_plan":payload,"preflight_only":True})
            elif action in {"write","restore"}:
                if request.partition_fingerprint:
                    payload=ps.apply(*args,request.partition_source,action=="restore",request.partition_fingerprint,root,logger.add)
                    result=EngineResult(True,"Partition write and readback verified.",ActionState.READY,payload)
                else:
                    payload=ps.prepare(*args,request.partition_source,action=="restore")
                    result=EngineResult(True,"Review the selected partition and confirm the write.",ActionState.READY,
                        {"partition_plan":payload,"preflight_only":True})
            else:raise FlashError("Unknown partition operation")
            logger.add(result.message)
        elif request.action_id == "flash_firmware":
            logger.add("Inspecting firmware, chipset and matching service transport...")
            engine = DeviceEngine(request.project_root, EvidenceJournal(request.evidence_journal))
            package = Path(request.firmware_path)
            if request.firmware_mode == "Board Firmware" and package.suffix.lower() == ".xml" and package.name.lower().startswith("rawprogram"):
                from . import qualcomm_package as generic_board
                from . import caz_al10_board_runtime as reference_board
                evidence = request.evidence_journal.parent / "firmware-flash"
                is_reference = (package.is_file() and package.name.lower() == "rawprogram_unsparse.xml"
                                and _digest(package) == "3018238303813569598a88b2ae305e60a9e6bdecbb571563b570f0769ca2d3ff")
                if is_reference:
                    board_plan, board_apply = reference_board.board_plan, reference_board.board_apply
                else:
                    board_plan, board_apply = generic_board.plan, generic_board.apply
                if request.firmware_apply:
                    output = board_apply(request.project_root, package, request.firmware_model,
                        request.firmware_chipset, request.firmware_plan_hash, evidence, logger.add)
                    result = EngineResult(True, "Board image programming and scoped readback completed. Verify normal boot.",
                        ActionState.READY, {**output,"preflight_only":False,"write_authorized":True})
                else:
                    payload = board_plan(request.project_root, package, request.firmware_model,
                        request.firmware_chipset, evidence)
                    message = ("Package validated: " + str(len(payload["partitions"])) +
                        " selected firmware operations. " +
                        ("GPT-preserving repair; no automatic reset." if payload.get("same_layout") else
                         "Vendor GPT reconstruction; backup and readback before reset." if payload.get("vendor_reconstruction") else "Reference board reconstruction; backup and readback before reset."))
                    if not payload.get("fingerprint"):
                        message += " " + payload.get("device_status","Connect the matching device to confirm.")
                    result = EngineResult(True,message,ActionState.READY,payload)
            elif (request.firmware_mode == "Repair" and package.name.upper() == "UPDATE.APP"
                  and request.firmware_model.strip().upper() == "CAZ-AL10"
                  and package.is_file() and package.stat().st_size == 3925603036 and _digest(package) == BASE_SHA):
                from .caz_al10_recovery import stock_plan, stock_apply
                # Route by proven package identity, not by the model alone.
                fastboot = engine._tool("fastboot")
                if not fastboot:
                    result = EngineResult(False, "Approved Fastboot executable unavailable.", ActionState.MISSING_DEPENDENCY)
                elif request.firmware_apply:
                    output = stock_apply(request.firmware_path, request.firmware_model,
                        request.firmware_chipset, request.firmware_mode, fastboot,
                        request.firmware_plan_hash, request.evidence_journal.parent / "firmware-flash", logger.add)
                    result = EngineResult(True, "CAZ-AL10 stock writes complete; reboot and verify Android/network. Factory boot chain retained.",
                        ActionState.READY, {**output,"preflight_only":False,"write_authorized":True})
                else:
                    payload = stock_plan(request.firmware_path, request.firmware_model,
                        request.firmware_chipset, request.firmware_mode, fastboot,
                        request.evidence_journal.parent / "firmware-flash")
                    result = EngineResult(True, "CAZ-AL10 B175 all/cn recovery ready: eight verified images, including userdata. Confirm replacement.",
                        ActionState.READY, payload)
            elif request.firmware_mode=="Board Firmware" and package.suffix.lower()==".xml":
                from .kirin_board_package import inspect
                vendor=inspect(package,request.firmware_model,request.firmware_chipset)
                result=EngineResult(True,
                    "Vendor board package inspected. For an already authorized Fastboot device, select Repair for ordinary firmware images. Factory service-entry and vendor-only operations are separate.",
                    ActionState.READY,{"model":vendor["model"],"chipset":vendor["chipset"],
                    "mode":"Board Firmware","version":vendor["version"],"package_sha256":vendor["package_sha256"],
                    "partitions":vendor["stages"],"excluded":vendor["excluded"],
                    "preflight_only":True,"write_authorized":False})
            elif package.suffix.lower() == ".json" or package.name.upper() == "UPDATE.APP" or (request.firmware_mode=="Repair" and package.suffix.lower()==".xml"):
                fastboot = engine._tool("fastboot")
                if not fastboot:
                    result = EngineResult(False, "Approved Fastboot executable unavailable.",
                                          ActionState.MISSING_DEPENDENCY)
                elif request.firmware_apply:
                    output = execute_generic_plan(
                        request.firmware_path, request.firmware_model,
                        request.firmware_chipset, request.firmware_mode,
                        fastboot, request.firmware_plan_hash,
                        request.evidence_journal.parent / "firmware-flash",
                        logger.add,
                    )
                    result = EngineResult(
                        True, f"Firmware writes complete ({output['completed']}); NO REBOOT.",
                        ActionState.READY, {**output, "write_authorized": True,
                                            "preflight_only": False},
                    )
                else:
                    from dataclasses import asdict
                    model,chip=request.firmware_model,request.firmware_chipset
                    try:
                        plan = prepare_generic_plan(request.firmware_path,model,chip,request.firmware_mode,fastboot)
                    except FlashError as exc:
                        # A missing authorized transport can wait; a rejected
                        # lock state, incompatible image or ambiguous identity
                        # is not a request to bypass device authorization.
                        if not (request.service_wait and cancel is not None and request.firmware_mode=="Repair"
                                and str(exc)=="Exactly one responding Fastboot device is required"):
                            raise
                        from .firmware_flash import _load_selection
                        from .fastboot_identity import canonical_chipset
                        from .kirin_repair_session import wait_for_repair
                        model,chip,_,_=_load_selection(package,model,chip,request.firmware_mode)
                        if not canonical_chipset(chip).startswith(("kirin","hisi")):raise
                        serial=wait_for_repair(fastboot,model,chip,logger.add,cancel,request.service_expected_serial)
                        plan=prepare_generic_plan(request.firmware_path,model,chip,request.firmware_mode,fastboot)
                        from hashlib import sha256
                        if plan.serial_hash!=sha256(serial.encode()).hexdigest()[:12]:
                            raise FlashError("Repair target changed before preflight completed")
                    result = EngineResult(
                        True,
                        f"Ready: {plan.model} / {plan.chipset} — {len(plan.operations)} "
                        "verified partitions. Review and explicitly confirm; no automatic reboot.",
                        ActionState.READY,
                        {"schema": "techguy.huawei.firmware-plan.v1",
                         "model": plan.model, "chipset": plan.chipset,
                         "device_reported_model": plan.device_reported_model,
                         "mode": plan.mode,
                         "service_loader": resolve_loader(request.project_root, plan.chipset).to_dict(),
                         "service_loader_required": False,
                         "partitions": [asdict(item) for item in plan.operations],
                         "excluded": list(plan.excluded),
                         "fingerprint": plan.fingerprint,
                         "preflight_only": True, "write_authorized": False,
                         "no_reboot": True},
                    )
            else:
                service = LiveHuaweiService(engine, expected_serial=request.service_expected_serial)
                result = service.prepare_firmware(request.firmware_path, request.firmware_mode)
            logger.add(result.message)
        else:
            engine = DeviceEngine(request.project_root, EvidenceJournal(request.evidence_journal))
            service = LiveHuaweiService(engine, expected_serial=request.service_expected_serial)
            if request.action_id == "read_device":
                logger.add("Waiting for device...")
                def read_progress(line):
                    logger.add(line)
                    if progress:progress(line)
                engine.progress = read_progress
            else:
                logger.add(f"Starting {request.action_id} read-only service...")
            handlers = {
                "read_device": engine.probe,
                "verlist": service.inspect_verlist,
                "full_oeminfo": service.read_oeminfo,
                "board_repair": service.board_firmware,
                "backup_restore": service.backup_restore,
            }
            result = handlers[request.action_id]()
            if request.action_id == "read_device":
                from .xray_read_device import enrich
                from .fastboot_partition_inventory import enrich_inventory
                fastboot_serial=engine.snapshot.serial if engine.snapshot.interface=="Fastboot" and result.ok else ""
                # A multi-device rejection is not permission to select another
                # handset. Run deep observation only for a single session or
                # unresolved USB presence.
                if "Multiple Huawei devices" not in result.message:
                    result=enrich(engine,result,request.evidence_journal.parent/"xray",read_progress)
                result=enrich_inventory(engine,result,fastboot_serial,read_progress)
                snapshot = engine.snapshot
                logger.add("Read device info...")
                for line in device_read_lines(snapshot, result):
                    logger.add(line)
            else:
                logger.add(result.message)
    except FlashError as exc:
        result = EngineResult(False, str(exc), ActionState.GUARDED,
                              {"preflight_only": not request.firmware_apply,
                               "write_authorized": False})
        logger.add(result.message)
    except Exception as exc:
        result = EngineResult(
            False,
            f"Service failed: {type(exc).__name__}: {exc}",
            ActionState.FAILED,
        )
        logger.add(result.message)
    elapsed = logger.complete(result, snapshot)
    return ServiceResponse(
        request.action_id,
        result,
        snapshot,
        str(logger.log_path),
        str(logger.record_path),
        elapsed,
    )
