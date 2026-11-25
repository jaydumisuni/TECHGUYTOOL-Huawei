"""Shared verified QDL runtime, no model-specific assumptions."""
from __future__ import annotations
from pathlib import Path
import re, subprocess
from .firmware_flash import FlashError, _digest

QDL_FILES = {
 "qdl.exe":"b4ddc5ae6cd119c77c80e8e3f16f32448242df22361b1b0efaae43de494898b4",
 "libzstd.dll":"b95c223a9548a9ecf51377c962e0bc8f0c51eb0c6f67a296dbc885996f0dd40d",
 "libbz2-1.dll":"a4fbb97c26662d2b8a80bf4597ed3effb69b12048b0cb1eef2c3f211e2e66673",
 "libusb-1.0.dll":"9858e2381221619e26a78a2824e5970c2a7ec48cdb75071c19eb7b61baa268e2",
 "zlib1.dll":"93e9243a44c29200eeacaf9658efe2558581770e4b11ca4b500e18e424a6e3b5",
 "libxml2-16.dll":"81e97f59e486f95de3b8b12973860102cddebbaaeedbbc22786aaec0728b2c68",
 "liblzma-5.dll":"ccb6a179acf35e704b2ffd7f232677982c4856bd1dda1341713a27518cf97ce1",
 "libzip.dll":"67c521647ba161a42325e92cb949ec5913463386d722d97f8ac347349b1837af",
 "libiconv-2.dll":"7a282a854e01be726c6cccfe46f548c716aa45b3014818468253aaa4efbcd067",
}
def resolve_qdl(project:Path)->Path:
    places=(project/"runtime"/"qdl"/"windows-x64",
        project/".workspace"/"tools"/"qdl-v2.9.1"/"extracted"/"qdl-binary-windows-x64")
    for folder in places:
        if all((folder/name).is_file() and not (folder/name).is_symlink()
               and _digest(folder/name)==digest for name,digest in QDL_FILES.items()):
            return folder/"qdl.exe"
    raise FlashError("Verified native QDL v2.9.1 runtime unavailable.")


def _run(qdl:Path,args:list[str],cwd:Path,timeout=120)->tuple[int,str]:
    p=subprocess.run([str(qdl),*args],cwd=cwd,shell=False,capture_output=True,text=True,
        errors="replace",timeout=timeout,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    return p.returncode,p.stdout+"\n"+p.stderr


def _device(qdl:Path,folder:Path,runner=None)->str:
    code,out=(runner or _run)(qdl,["list"],folder,15)
    rows=[line.split("\t") for line in out.splitlines() if re.match(r"^[0-9a-f]{4}:[0-9a-f]{4}\t",line,re.I)]
    if code or len(rows)!=1 or rows[0][0].lower()!="05c6:9008" or len(rows[0])!=3:
        raise FlashError("Connect exactly one Qualcomm QDLoader 9008 COM device.")
    serial=rows[0][1].strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}",serial):
        raise FlashError("QDL did not expose a stable device serial.")
    return serial
