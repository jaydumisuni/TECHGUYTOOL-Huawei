"""Read existing per-action reports without modifying historical evidence."""
from pathlib import Path
import re,json

def records(root:Path,limit=500):
    root=root.resolve()
    paths=[]
    for day in root.iterdir() if root.is_dir() else ():
        if day.is_symlink() or not day.is_dir() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",day.name):continue
        for p in day.glob("*.txt"):
            if not p.is_symlink() and p.is_file():paths.append(p)
    rows=[]
    for p in sorted(paths,key=lambda p:p.name,reverse=True)[:limit]:
        try:
            if p.stat().st_size>2*1024**2:continue
            lines=p.read_text(encoding="utf8",errors="replace").splitlines()
        except OSError:continue
        def field(prefix,last=False):
            matches=[x[len(prefix):].strip() for x in lines if x.startswith(prefix)]
            return (matches[-1] if last else matches[0]) if matches else ""
        action=field("Action: ")
        if not action:continue
        result=field("Result: ",True)
        status,_,message=result.partition(" | ")
        rows.append({"path":str(p),"run":p.stem,"date":p.parent.name,
            "time":field("Started: "),"operation":action,"model":field("Model: "),
            "interface":field("Interface: "),"platform":field("Chipset: "),
            "result":status or "INCOMPLETE","message":message,
            "elapsed":field("Elapsed Time: ",True)})
    return rows

def read_log(root,path):
    p=Path(path)
    if p.is_symlink() or p.suffix.lower()!=".txt" or root.resolve() not in p.resolve().parents:
        raise ValueError("Not a local operation report")
    if p.stat().st_size>2*1024**2:raise ValueError("Report exceeds display limit")
    return p.read_text(encoding="utf8",errors="replace")

def export(root,destination,rows):
    p=Path(destination)
    if p.exists():raise ValueError("Choose a new export file")
    # Preserve original logs; export only the displayed report index.
    with p.open("x",encoding="utf8") as f:json.dump(rows,f,indent=2,ensure_ascii=False)
