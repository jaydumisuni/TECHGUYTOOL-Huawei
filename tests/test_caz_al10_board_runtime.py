import struct
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from techguy_huawei import caz_al10_board_runtime as b
from techguy_huawei.firmware_flash import FlashError

def gpt():
    raw=bytearray(34*512)
    entries=bytearray(128*128)
    entries[0:16]=b"X"*16
    struct.pack_into("<QQ",entries,32,34,100)
    name="boot".encode("utf-16le")
    entries[56:56+len(name)]=name
    raw[1024:1024+len(entries)]=entries
    h=bytearray(512)
    h[:8]=b"EFI PART"
    struct.pack_into("<II",h,8,0x10000,92)
    struct.pack_into("<QQQQ",h,24,1,b.SECTORS-1,34,b.SECTORS-34)
    struct.pack_into("<QIII",h,72,2,128,128,zlib.crc32(entries))
    struct.pack_into("<I",h,16,zlib.crc32(h[:92]))
    raw[512:1024]=h
    return raw

class BoardRuntimeTests(unittest.TestCase):
    def test_gpt_crc_and_geometry(self):
        raw=gpt()
        self.assertEqual(b._layout(raw,0,1),{"boot":[34,100]})
        raw[1024]^=1
        with self.assertRaises(FlashError): b._layout(raw,0,1)
    def test_gpt_capacity(self):
        raw=gpt(); h=bytearray(raw[512:1024])
        struct.pack_into("<Q",h,32,b.SECTORS-2)
        h[16:20]=b"\0"*4;struct.pack_into("<I",h,16,zlib.crc32(h[:92]))
        raw[512:1024]=h
        with self.assertRaises(FlashError): b._layout(raw,0,1)
    def test_qdl_single_bound_serial(self):
        with patch.object(b,"_run",return_value=(0,"05c6:9008\tA123\tCOM4\n")):
            self.assertEqual(b._device(Path("qdl"),Path(".")),"A123")
        for output in ("No devices found","05c6:9008\t\tCOM4","05c6:9008\tA123\tCOM4\n05c6:9008\tB123\tCOM5","05c6:900e\tA123\tCOM4"):
            with patch.object(b,"_run",return_value=(0,output)):
                with self.assertRaises(FlashError): b._device(Path("qdl"),Path("."))
    def test_program_receipt_all_acks(self):
        names=["system"]*149+["PrimaryGPT"]
        log="\n".join('flashed "'+n+'" successfully' for n in names)+"\n13 patches applied\npartition 0 is now bootable\nflashed 150 partitions"
        self.assertTrue(b._acks(log,names))
        self.assertFalse(b._acks(log.replace("13 patches","12 patches"),names))
        self.assertFalse(b._acks(log.replace('flashed "PrimaryGPT" successfully',''),names))
    def test_pin_runtime_on_athena_if_present(self):
        root=Path(__file__).resolve().parents[1]
        q=root/".workspace"/"tools"/"qdl-v2.9.1"/"extracted"/"qdl-binary-windows-x64"/"qdl.exe"
        bundled=root/"runtime"/"qdl"/"windows-x64"/"qdl.exe"
        expected=bundled if bundled.is_file() else q
        if not expected.exists():self.skipTest("native QDL not staged on this host")
        self.assertEqual(b.resolve_qdl(root),expected)
