"""Shared Huawei Fastboot response parsing; no transport or write authority."""
import re

# Legacy Huawei uses CAZ-AL10C00B387; newer builds use ELE-L29 10.0...
_MODEL = re.compile(r"\b([A-Z]{2,6}-[A-Z0-9]{2,12}?)(?=C\d{2,4}B\d+\b|\s+\d+\.\d+|[\s(\r\n]|$)",re.I)
def model_from_build(text):
    m=_MODEL.search(text)
    return m.group(1).upper() if m else ""

def lock_state(text):
    states=[]
    for line in text.splitlines():
        m=re.search(r"(?:\block\s+state\s*(?:is|:|=)\s*|\(bootloader\)\s*(?:bootinfo:\s*)?)(unlocked|unlock|locked|lock)\s*$",line,re.I)
        if m:states.append("unlocked" if m.group(1).lower().startswith("un") else "locked")
    return states[0] if states and len(set(states))==1 else "unverified"

def product_from_response(text):
    m=re.search(r"\bproduct:\s*([a-z0-9_.-]+)",text,re.I)
    return m.group(1).lower() if m else ""

def kirin_product(product):
    return bool(re.fullmatch(r"(?:kirin|hisi)[a-z0-9_]+",product,re.I))

def canonical_chipset(value):
    value=value.strip().lower().replace(" ","")
    if re.fullmatch(r"hisi\d{3,4}",value):return "kirin"+value[4:]
    if value in {"hisi710a","hisi620c"}:return "kirin"+value[4:]
    if value in {"kirink3v2","k3v2"}:return "hisik3v2"
    return value

def acknowledged(part: str, code: int, output: str) -> bool:
    if code or "FAILED" in output.upper():
        return False
    target = re.escape(part)
    writes = re.findall(r"Writing\s+'"+target+r"'\s+OKAY\b", output, re.I)
    sparse = re.findall(r"Sending sparse\s+'"+target+r"'\s+(\d+)/(\d+).*?OKAY\b", output, re.I)
    if sparse:
        total = int(sparse[0][1])
        return total > 0 and len(writes) == total and [(int(a),int(b)) for a,b in sparse] == [(i,total) for i in range(1,total+1)]
    return len(writes) == 1
