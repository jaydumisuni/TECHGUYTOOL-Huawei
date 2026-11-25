"""Stage verified local runtime assets for the existing Huawei Builder.

No network calls, firmware packages, device operations or global installations.
The caller supplies the owner-controlled canonical X-Ray checkout at build time.
"""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from techguy_huawei.qdl_runtime import QDL_FILES,resolve_qdl

XRAY_COMMIT="47df719f60d85e06ccecd867fdd4d65b26864378"

def digest(p):
    with p.open("rb") as f:
        h=hashlib.sha256()
        for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
        return h.hexdigest()

def copy_verified(source,destination,expected,size=None):
    if not source.is_file() or source.is_symlink() or digest(source)!=expected or (size is not None and source.stat().st_size!=size):
        raise RuntimeError("Source integrity mismatch: "+str(source))
    if destination.exists():
        if destination.is_symlink() or digest(destination)!=expected:raise RuntimeError("Existing runtime differs: "+str(destination))
        return
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=destination.with_name(destination.name+".staging")
    if tmp.exists():raise RuntimeError("Unexpected existing staging file: "+str(tmp))
    shutil.copyfile(source,tmp)
    if digest(tmp)!=expected:raise RuntimeError("Staging integrity mismatch")
    tmp.replace(destination)

def stage(root=ROOT,xray=None):
    runtime=root/"runtime"
    inventory=json.loads((root/"data/kirin_loader_inventory.json").read_text(encoding="utf8"))
    source=(root/inventory["relative_source"]).resolve()
    count=0
    for family in inventory["families"]:
        for item in family["files"]:
            rel=Path(family["cpu"])/item["name"]
            dest=runtime/"kirin-loaders"/rel
            # Rebuild may run without reference archive once assets are staged.
            origin=dest if dest.is_file() else source/rel
            copy_verified(origin,dest,item["sha256"],item["bytes"]);count+=1
    qdl=resolve_qdl(root)
    for name,sha in QDL_FILES.items():
        copy_verified(qdl.parent/name,runtime/"qdl/windows-x64"/name,sha)
    dest=runtime/"xray"
    manifest=dest/"source-manifest.json"
    if manifest.is_file():
        record=json.loads(manifest.read_text(encoding="utf8"))
        if record.get("commit")!=XRAY_COMMIT:raise RuntimeError("X-Ray source pin differs")
        for rel,sha in record["files"].items():
            file=dest/rel
            if not file.is_file() or digest(file)!=sha:raise RuntimeError("Bundled X-Ray file integrity mismatch: "+rel)
    else:
        xray=Path(xray or root.parent/"TTG-Device-X-Ray").resolve()
        def git(*args):
            return subprocess.check_output(["git","-c","safe.directory="+xray.as_posix(),"-C",str(xray),*args])
        names=git("ls-tree","-r","--name-only",XRAY_COMMIT,"src/ttg_device_xray","LICENSE").decode().splitlines()
        if "src/ttg_device_xray/cli.py" not in names:raise RuntimeError("Pinned X-Ray source missing")
        files={}
        for name in names:
            raw=git("show",XRAY_COMMIT+":"+name)
            sha=hashlib.sha256(raw).hexdigest()
            path=dest/name
            if path.exists() and digest(path)!=sha:raise RuntimeError("Existing X-Ray runtime differs: "+name)
            path.parent.mkdir(parents=True,exist_ok=True)
            if not path.exists():path.write_bytes(raw)
            files[name]=sha
        manifest.write_text(json.dumps({"commit":XRAY_COMMIT,"files":files},indent=2)+"\n",encoding="utf8")
    print("Local runtime staged:",count,"loader containers,",len(QDL_FILES),"QDL files, pinned X-Ray",XRAY_COMMIT)
if __name__=="__main__":
    stage(xray=sys.argv[1] if len(sys.argv)>1 else None)
