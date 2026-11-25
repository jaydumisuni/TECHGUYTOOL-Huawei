from pathlib import Path

import pytest

from techguy_huawei.qualcomm_board import BoardPlanError, build_plan


def fixture(tmp_path: Path) -> Path:
    (tmp_path / "prog.mbn").write_bytes(b"\x7fELF" + b"\x00" * 8)
    (tmp_path / "boot.img").write_bytes(b"\x00" * 512)
    (tmp_path / "oem.img").write_bytes(b"\x01" * 512)
    (tmp_path / "raw.xml").write_text(
        '<data><program label="boot" filename="boot.img" SECTOR_SIZE_IN_BYTES="512" '
        'num_partition_sectors="2" file_sector_offset="0" start_sector="100" '
        'physical_partition_number="0" sparse="false"/>'
        '<program label="oeminfo" filename="oem.img" SECTOR_SIZE_IN_BYTES="512" '
        'num_partition_sectors="2" file_sector_offset="0" start_sector="102" '
        'physical_partition_number="0"/>'
        '<program label="unused" filename="" SECTOR_SIZE_IN_BYTES="512" '
        'num_partition_sectors="0" file_sector_offset="0" start_sector="104" '
        'physical_partition_number="0"/></data>'
    )
    (tmp_path / "patch.xml").write_text(
        '<patches><patch filename="DISK" start_sector="NUM_DISK_SECTORS-1." '
        'byte_offset="0" size_in_bytes="4" physical_partition_number="0" '
        'value="NUM_DISK_SECTORS-34."/></patches>'
    )
    return tmp_path


def test_plan_bound_to_file_hashes(tmp_path):
    path = fixture(tmp_path)
    plan = build_plan(path, "raw.xml", "patch.xml", "prog.mbn")
    assert plan["summary"]["file_backed_entries"] == 2
    assert plan["summary"]["unique_partitions"] == ["oeminfo"]
    assert plan["summary"]["empty_entries"] == 1
    assert plan["patches"][0]["start_sector"] == "NUM_DISK_SECTORS-1."
    (path / "boot.img").write_bytes(b"\x02" * 512)
    assert build_plan(path, "raw.xml", "patch.xml", "prog.mbn")["fingerprint"] != plan["fingerprint"]


def test_reject_traversal_and_excess_geometry(tmp_path):
    path = fixture(tmp_path)
    with pytest.raises(BoardPlanError):
        build_plan(path, "../raw.xml", "patch.xml", "prog.mbn")
    (path / "boot.img").write_bytes(b"\x00" * 2048)
    with pytest.raises(BoardPlanError, match="allocation"):
        build_plan(path, "raw.xml", "patch.xml", "prog.mbn")


def test_reject_missing_images(tmp_path):
    path = fixture(tmp_path)
    (path / "oem.img").unlink()
    with pytest.raises(BoardPlanError, match="Missing"):
        build_plan(path, "raw.xml", "patch.xml", "prog.mbn")

def test_legacy_patch_expression_without_period(tmp_path):
    path = fixture(tmp_path)
    patch = path / "patch.xml"
    patch.write_text(patch.read_text().replace('NUM_DISK_SECTORS-1.', 'NUM_DISK_SECTORS-1'))
    assert build_plan(path, "raw.xml", "patch.xml", "prog.mbn")["patches"][0]["start_sector"] == "NUM_DISK_SECTORS-1"