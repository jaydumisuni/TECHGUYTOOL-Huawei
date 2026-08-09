from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECIPE = ROOT / "recipes" / "vog_l29_c185.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TARGET_PROFILE_ID = "VOG-L29.C185"
HARDWARE_PENDING = "HARDWARE_PENDING"
RELEASE_CONDITIONS = frozenset(
    {"target_identity_verified", "remaining_firmware_completed", "target_boot_environment_ready"}
)
DONOR_MARKERS = ("VTR", "C432")


class RecipeError(ValueError):
    """Fail-closed VOG recipe validation or compilation error."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def recipe_hash(recipe: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(recipe).encode("utf-8")).hexdigest()


def load_recipe(source: Mapping[str, Any] | str | Path | None = None) -> dict[str, Any]:
    if source is None:
        payload = json.loads(DEFAULT_RECIPE.read_text(encoding="utf-8"))
    elif isinstance(source, Mapping):
        payload = deepcopy(dict(source))
    else:
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
    validate_recipe(payload)
    return payload


def validate_recipe(recipe: Mapping[str, Any]) -> None:
    required_top = {
        "schema", "recipe_id", "recipe_version", "authority", "execution_authority",
        "device_authority", "production_enablement", "target_profile",
        "accepted_source_profiles", "required_starting_mode", "service_entry", "oeminfo",
        "artifact_requirements", "stages", "service_release_conditions",
        "verification_states", "provenance", "certification", "truth_boundary",
    }
    missing = sorted(required_top - set(recipe))
    if missing:
        raise RecipeError("RECIPE_FIELD_MISSING", ",".join(missing))
    unknown = sorted(set(recipe) - required_top)
    if unknown:
        raise RecipeError("RECIPE_FIELD_UNKNOWN", ",".join(unknown))

    if recipe["schema"] != "techguytool-huawei.repair-recipe.vog-l29-c185.v1":
        raise RecipeError("RECIPE_SCHEMA_INVALID", str(recipe["schema"]))
    if recipe["recipe_id"] != "vog-l29-c185-revive-v1":
        raise RecipeError("RECIPE_ID_INVALID", str(recipe["recipe_id"]))
    if recipe["authority"] != "planning_only" or recipe["device_authority"] != "none":
        raise RecipeError("RECIPE_AUTHORITY_EXPANDED", "Phase 9 public recipe must not own device authority")
    if recipe["execution_authority"] != "lease_required":
        raise RecipeError("LEASE_REQUIREMENT_MISSING", "all execution must remain lease-bound")
    if recipe["production_enablement"] != HARDWARE_PENDING:
        raise RecipeError("HARDWARE_BOUNDARY_INVALID", "software recipe must remain HARDWARE_PENDING")

    target = _mapping(recipe["target_profile"], "target_profile")
    expected_target = {
        "profile_id": TARGET_PROFILE_ID,
        "family": "VOG",
        "model": "VOG-L29",
        "soc": "Kirin980",
        "region": "C185",
        "vendor": "hw",
        "country": "meafnaf",
    }
    for key, expected in expected_target.items():
        if target.get(key) != expected:
            raise RecipeError("TARGET_PROFILE_MISMATCH", f"{key}={target.get(key)!r}")

    source_profiles = recipe["accepted_source_profiles"]
    if source_profiles != ["VOG-AL00.board_service", "VOG-L29.board_service"]:
        raise RecipeError("SOURCE_PROFILE_SET_INVALID", repr(source_profiles))
    if recipe["required_starting_mode"] != "board_service_fastboot":
        raise RecipeError("STARTING_MODE_INVALID", str(recipe["required_starting_mode"]))

    service = _mapping(recipe["service_entry"], "service_entry")
    if service.get("testpoint_transport") != "huawei_usb_com_1_0":
        raise RecipeError("SERVICE_ENTRY_INVALID", "expected Huawei USB COM 1.0")
    if service.get("service_mode") != "board_service_fastboot" or service.get("preserve_until_release") is not True:
        raise RecipeError("SERVICE_MODE_POLICY_INVALID", "Board-Service Fastboot must remain protected")

    oeminfo = _mapping(recipe["oeminfo"], "oeminfo")
    if (oeminfo.get("total_size_bytes"), oeminfo.get("copy_count"), oeminfo.get("copy_size_bytes")) != (
        96 * 1024 * 1024,
        2,
        48 * 1024 * 1024,
    ):
        raise RecipeError("OEMINFO_LAYOUT_INVALID", "expected 96 MiB as two 48 MiB copies")
    for flag in (
        "derive_target_identity_from_exact_firmware",
        "preserve_device_specific_records",
        "backup_required",
        "readback_required",
    ):
        if oeminfo.get(flag) is not True:
            raise RecipeError("OEMINFO_POLICY_INVALID", flag)
    if oeminfo.get("hardcoded_record_offsets_allowed") is not False:
        raise RecipeError("HARDCODED_OFFSET_FORBIDDEN", "OEMINFO record offsets require runtime reviewed authority")

    requirements = recipe["artifact_requirements"]
    if not isinstance(requirements, list) or not requirements:
        raise RecipeError("ARTIFACT_REQUIREMENTS_INVALID", "non-empty list required")
    roles: list[str] = []
    for item in requirements:
        spec = _mapping(item, "artifact_requirement")
        if set(spec) != {"role", "kind", "executable"}:
            raise RecipeError("ARTIFACT_REQUIREMENT_SHAPE_INVALID", repr(sorted(spec)))
        role = spec.get("role")
        if not isinstance(role, str) or not role:
            raise RecipeError("ARTIFACT_ROLE_INVALID", repr(role))
        roles.append(role)
    if len(roles) != len(set(roles)):
        raise RecipeError("ARTIFACT_ROLE_DUPLICATE", repr(roles))

    stages = recipe["stages"]
    if not isinstance(stages, list) or not stages:
        raise RecipeError("STAGE_SET_INVALID", "non-empty list required")
    stage_ids = [str(_mapping(stage, "stage").get("id", "")) for stage in stages]
    if any(not value for value in stage_ids) or len(stage_ids) != len(set(stage_ids)):
        raise RecipeError("STAGE_ID_INVALID", repr(stage_ids))
    _validate_stage_order(stages)

    release = recipe["service_release_conditions"]
    if set(release) != RELEASE_CONDITIONS or len(release) != len(RELEASE_CONDITIONS):
        raise RecipeError("RELEASE_CONDITIONS_INVALID", repr(release))

    cert = _mapping(recipe["certification"], "certification")
    if cert.get("simulation") != "REQUIRED" or cert.get("replay") != "REQUIRED":
        raise RecipeError("SOFTWARE_PROOF_REQUIRED", repr(cert))
    if cert.get("physical_vog") != HARDWARE_PENDING or cert.get("production_enabled") is not False:
        raise RecipeError("PHYSICAL_CERTIFICATION_NOT_PENDING", repr(cert))

    serialized = _canonical(recipe)
    for marker in DONOR_MARKERS:
        if marker in serialized:
            raise RecipeError("DONOR_DATA_LEAK", marker)


def validate_artifact_bindings(
    recipe: Mapping[str, Any], bindings: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    validate_recipe(recipe)
    expected = {item["role"]: item for item in recipe["artifact_requirements"]}
    missing = sorted(set(expected) - set(bindings))
    extra = sorted(set(bindings) - set(expected))
    if missing:
        raise RecipeError("ARTIFACT_BINDING_MISSING", ",".join(missing))
    if extra:
        raise RecipeError("ARTIFACT_BINDING_UNKNOWN", ",".join(extra))

    normalized: dict[str, dict[str, Any]] = {}
    seen_hashes: set[str] = set()
    for role, requirement in expected.items():
        binding = _mapping(bindings[role], f"artifact_binding:{role}")
        required = {
            "sha256", "size_bytes", "target_profile_id", "kind", "executable",
            "custody", "provenance_uri_sha256",
        }
        if set(binding) != required:
            raise RecipeError("ARTIFACT_BINDING_SHAPE_INVALID", role)
        sha = binding.get("sha256")
        provenance = binding.get("provenance_uri_sha256")
        if not isinstance(sha, str) or SHA256_RE.fullmatch(sha) is None:
            raise RecipeError("ARTIFACT_HASH_INVALID", role)
        if not isinstance(provenance, str) or SHA256_RE.fullmatch(provenance) is None:
            raise RecipeError("ARTIFACT_PROVENANCE_HASH_INVALID", role)
        if sha in seen_hashes:
            raise RecipeError("ARTIFACT_HASH_REUSED", role)
        seen_hashes.add(sha)
        if binding.get("target_profile_id") != TARGET_PROFILE_ID:
            raise RecipeError("ARTIFACT_TARGET_MISMATCH", role)
        if binding.get("kind") != requirement["kind"]:
            raise RecipeError("ARTIFACT_KIND_MISMATCH", role)
        if binding.get("executable") is not requirement["executable"]:
            raise RecipeError("ARTIFACT_EXECUTABLE_MISMATCH", role)
        if not isinstance(binding.get("size_bytes"), int) or isinstance(binding.get("size_bytes"), bool) or binding["size_bytes"] <= 0:
            raise RecipeError("ARTIFACT_SIZE_INVALID", role)
        if binding.get("custody") not in {
            "private_drive", "approved_workstation", "customer_vault", "ephemeral_runtime"
        }:
            raise RecipeError("ARTIFACT_CUSTODY_INVALID", role)
        normalized[role] = dict(binding)
    return normalized


def validate_range_manifests(recipe: Mapping[str, Any], range_manifests: Mapping[str, str]) -> dict[str, str]:
    required_stages = {
        stage["id"] for stage in recipe["stages"] if stage.get("range_manifest_required") is True
    }
    missing = sorted(required_stages - set(range_manifests))
    extra = sorted(set(range_manifests) - required_stages)
    if missing:
        raise RecipeError("RANGE_MANIFEST_MISSING", ",".join(missing))
    if extra:
        raise RecipeError("RANGE_MANIFEST_UNKNOWN", ",".join(extra))
    result: dict[str, str] = {}
    for stage_id in sorted(required_stages):
        value = range_manifests[stage_id]
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise RecipeError("RANGE_MANIFEST_HASH_INVALID", stage_id)
        result[stage_id] = value
    return result


def validate_preflight_evidence(recipe: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    validate_recipe(recipe)
    required = {
        "physical_session_id", "device_continuity_certified", "xray_bundle_sha256",
        "storage_inventory_sha256", "board_identity_sha256", "board_identity_verified",
        "mode_lease_id", "mode", "mode_lease_reboot_allowed", "service_mode_certified",
        "target_profile_id", "model", "soc", "region", "vendor", "country",
        "package_manifest_sha256", "base_cust_preload_relationship", "anti_rollback_state",
    }
    if set(evidence) != required:
        raise RecipeError("PREFLIGHT_EVIDENCE_SHAPE_INVALID", repr(sorted(set(evidence))))
    for field in (
        "xray_bundle_sha256", "storage_inventory_sha256", "board_identity_sha256",
        "package_manifest_sha256",
    ):
        value = evidence[field]
        if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
            raise RecipeError("PREFLIGHT_HASH_INVALID", field)
    import uuid
    for field in ("physical_session_id", "mode_lease_id"):
        try:
            uuid.UUID(str(evidence[field]))
        except (ValueError, TypeError, AttributeError) as exc:
            raise RecipeError("PREFLIGHT_UUID_INVALID", field) from exc
    if evidence["device_continuity_certified"] is not True:
        raise RecipeError("DEVICE_CONTINUITY_UNCERTIFIED", "physical session continuity required")
    if evidence["board_identity_verified"] is not True:
        raise RecipeError("BOARD_IDENTITY_UNVERIFIED", "board identity must be evidence-backed")
    if evidence["mode"] != "board_service_fastboot" or evidence["service_mode_certified"] is not True:
        raise RecipeError("SERVICE_MODE_UNCERTIFIED", str(evidence["mode"]))
    if evidence["mode_lease_reboot_allowed"] is not False:
        raise RecipeError("NO_REBOOT_LEASE_REQUIRED", "mode lease must prohibit reboot")
    expected = {
        "target_profile_id": TARGET_PROFILE_ID,
        "model": "VOG-L29",
        "soc": "Kirin980",
        "region": "C185",
        "vendor": "hw",
        "country": "meafnaf",
    }
    for field, value in expected.items():
        if evidence[field] != value:
            raise RecipeError("PREFLIGHT_TARGET_MISMATCH", field)
    if evidence["base_cust_preload_relationship"] != "verified":
        raise RecipeError("BASE_CUST_PRELOAD_RELATIONSHIP_INVALID", "relationship not verified")
    if evidence["anti_rollback_state"] != "compatible":
        raise RecipeError("ANTI_ROLLBACK_CONSTRAINT_UNRESOLVED", str(evidence["anti_rollback_state"]))
    return dict(evidence)


def compile_recipe_plan(
    recipe: Mapping[str, Any],
    *,
    source_profile: str,
    current_mode: str,
    artifact_bindings: Mapping[str, Mapping[str, Any]],
    range_manifests: Mapping[str, str],
    preflight_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    validate_recipe(recipe)
    if source_profile not in recipe["accepted_source_profiles"]:
        raise RecipeError("SOURCE_PROFILE_UNSUPPORTED", source_profile)
    if current_mode != recipe["required_starting_mode"]:
        raise RecipeError("SERVICE_MODE_REQUIRED", current_mode)
    preflight = validate_preflight_evidence(recipe, preflight_evidence)
    artifacts = validate_artifact_bindings(recipe, artifact_bindings)
    ranges = validate_range_manifests(recipe, range_manifests)
    r_hash = recipe_hash(recipe)

    compiled_stages: list[dict[str, Any]] = []
    for index, stage in enumerate(recipe["stages"], start=1):
        stage_artifacts = {
            role: artifacts[role]["sha256"] for role in stage.get("artifact_roles", [])
        }
        compiled_stages.append(
            {
                "ordinal": index,
                "stage_id": stage["id"],
                "kind": stage["kind"],
                "expected_mode": stage["mode"],
                "reboot_allowed": stage["reboot_allowed"],
                "requires": list(stage.get("requires", [])),
                "produces": list(stage.get("produces", [])),
                "artifact_hashes": stage_artifacts,
                "range_manifest_sha256": ranges.get(stage["id"]),
                "lease_required": stage["kind"] in {"bounded_write", "conditional_bounded_write", "reboot"},
            }
        )

    return {
        "schema": "techguytool-huawei.compiled-vog-recipe-plan.v1",
        "recipe_id": recipe["recipe_id"],
        "recipe_hash": r_hash,
        "target_profile_id": TARGET_PROFILE_ID,
        "source_profile": source_profile,
        "starting_mode": current_mode,
        "physical_session_id": preflight["physical_session_id"],
        "mode_lease_id": preflight["mode_lease_id"],
        "preflight_evidence_sha256": hashlib.sha256(_canonical(preflight).encode("utf-8")).hexdigest(),
        "stages": compiled_stages,
        "service_release_conditions": sorted(RELEASE_CONDITIONS),
        "simulation_status": "READY",
        "physical_certification": HARDWARE_PENDING,
        "production_enabled": False,
        "device_authority": "none",
        "truth_boundary": recipe["truth_boundary"],
    }


def service_release_allowed(evidence_states: set[str] | frozenset[str]) -> bool:
    return RELEASE_CONDITIONS.issubset(evidence_states)


def production_enabled(recipe: Mapping[str, Any]) -> bool:
    validate_recipe(recipe)
    return recipe["certification"]["production_enabled"] is True


def _validate_stage_order(stages: list[Mapping[str, Any]]) -> None:
    by_id = {stage["id"]: index for index, stage in enumerate(stages)}
    required = (
        "preserve_service_environment",
        "restore_oeminfo_identity",
        "verify_oeminfo_readback",
        "continue_base_cust_preload",
        "continue_super",
        "verify_target_boot_environment",
        "restore_stock_fastboot",
        "release_service_mode",
        "reboot_to_target_system",
        "verify_normal_boot",
        "normalize_branding_if_required",
        "final_xray_verification",
    )
    missing = [stage_id for stage_id in required if stage_id not in by_id]
    if missing:
        raise RecipeError("REQUIRED_STAGE_MISSING", ",".join(missing))
    indices = [by_id[stage_id] for stage_id in required]
    if indices != sorted(indices):
        raise RecipeError("RECIPE_STAGE_ORDER_INVALID", repr(required))

    for stage in stages:
        if stage["id"] in {"restore_stock_recovery", "restore_stock_fastboot", "release_service_mode"}:
            if not RELEASE_CONDITIONS.issubset(set(stage.get("requires", []))):
                raise RecipeError("PREMATURE_FINALIZATION_POSSIBLE", stage["id"])
        if stage["id"] == "continue_super" and stage.get("hardcoded_chunk_count_allowed") is True:
            raise RecipeError("SUPER_CHUNK_COUNT_HARDCODED", stage["id"])

    super_plan = stages[by_id["derive_super_sparse_plan"]]
    if super_plan.get("hardcoded_chunk_count_allowed") is not False:
        raise RecipeError("SUPER_CHUNK_POLICY_INVALID", "chunk set must be derived from validated artifact")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RecipeError("MAPPING_REQUIRED", label)
    return value
