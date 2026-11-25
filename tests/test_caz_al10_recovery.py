import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from techguy_huawei import caz_al10_recovery as c
from techguy_huawei.firmware_flash import FlashError

class RecoveryTests(unittest.TestCase):
    def test_exact_model(self):
        self.assertTrue(c.matches_target("CAZ-AL10","MSM8953"))
        self.assertFalse(c.matches_target("CAZ-TL10","MSM8953"))
        self.assertFalse(c.matches_target("CAZ-AL10","kirin980"))
    def test_segment_acks(self):
        self.assertTrue(c._acknowledged("boot",0,"Writing 'boot' OKAY [0.1s]"))
        log="Sending sparse 'system' 1/2 (100 KB) OKAY\nWriting 'system' OKAY\nSending sparse 'system' 2/2 (10 KB) OKAY\nWriting 'system' OKAY"
        self.assertTrue(c._acknowledged("system",0,log))
        self.assertFalse(c._acknowledged("system",0,log.rsplit("\n",1)[0]))
        self.assertFalse(c._acknowledged("system",0,log+" FAILED"))
        self.assertFalse(c._acknowledged("system",1,log))
        self.assertFalse(c._acknowledged("system",0,log.replace("2/2","1/2")))
    def test_live_identity_and_factory_geometry(self):
        replies=[(0,"product: MSM8953"),(0,"HUAWEI CAZ-AL10"),(0,"rescue: 0.3"),(0,"partition-size:system: 0xe7400000")]
        with patch.object(c,"_unique_device",return_value="example"), patch.object(c,"_exec",side_effect=replies):
            self.assertEqual(c._stock_device("fastboot"),"example")
        replies[-1]=(0,"partition-size:system: 0xbc000000")
        with patch.object(c,"_unique_device",return_value="example"), patch.object(c,"_exec",side_effect=replies):
            with self.assertRaises(FlashError): c._stock_device("fastboot")
    def test_board_preflight_no_write_authority(self):
        ops=[{"label":"system","filename":"img"} for _ in range(150)]+[{"label":x,"filename":"img"} for x in c.BOARD_EXCLUDED]
        with patch.object(c,"build_plan",return_value={"fingerprint":c.BOARD_FINGERPRINT,"operations":ops}):
            plan=c.board_preview(Path("rawprogram_unsparse.xml"))
            self.assertEqual(len(plan["partitions"]),150)
            self.assertNotIn("fingerprint",plan)
            self.assertFalse(plan["write_authorized"])
    def test_board_fingerprint_mismatch(self):
        with patch.object(c,"build_plan",return_value={"fingerprint":"wrong"}):
            with self.assertRaises(FlashError): c.board_preview(Path("rawprogram_unsparse.xml"))
    def test_apply_revalidates_and_records(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); image=root/"payload";image.write_bytes(b"abc")
            op={"partition":"boot","source":str(image),"offset":0,"size":3,"sha256":hashlib.sha256(b"abc").hexdigest()}
            plan={"fingerprint":"p","serial_hash":hashlib.sha256(b"device").hexdigest(),"staging_root":str(root),"partitions":[op]}
            with patch.object(c,"stock_plan",return_value=plan),patch.object(c,"_stock_device",return_value="device"),patch.object(c,"_unique_device",return_value="device"),patch.object(c,"_exec",return_value=(0,"Writing 'boot' OKAY")) as ex,patch.object(c.shutil,"disk_usage",return_value=type("D",(),{"free":10**10})()):
                with self.assertRaises(FlashError): c.stock_apply("pkg","CAZ-AL10","msm8953","Repair","fastboot","wrong",root,lambda _:None)
                ex.assert_not_called()
                result=c.stock_apply("pkg","CAZ-AL10","msm8953","Repair","fastboot","p",root,lambda _:None)
                self.assertEqual(result["completed"],1)
                self.assertFalse(result["boot_verified"])
                self.assertEqual(ex.call_args.args[1][0:6],["-s","device","-S","256M","flash","boot"])
                self.assertEqual(list(root.glob("*.img")),[])
    def test_failed_write_retains_image(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); image=root/"payload";image.write_bytes(b"abc")
            op={"partition":"boot","source":str(image),"offset":0,"size":3,"sha256":hashlib.sha256(b"abc").hexdigest()}
            plan={"fingerprint":"p","serial_hash":hashlib.sha256(b"device").hexdigest(),"staging_root":str(root),"partitions":[op]}
            with patch.object(c,"stock_plan",return_value=plan),patch.object(c,"_stock_device",return_value="device"),patch.object(c,"_unique_device",return_value="device"),patch.object(c,"_exec",return_value=(1,"FAILED")),patch.object(c.shutil,"disk_usage",return_value=type("D",(),{"free":10**10})()):
                with self.assertRaises(FlashError): c.stock_apply("pkg","CAZ-AL10","msm8953","Repair","fastboot","p",root,lambda _:None)
                self.assertEqual(len(list(root.glob("*.img"))),1)
