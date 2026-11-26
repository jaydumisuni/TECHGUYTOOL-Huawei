"""Read-only target projection from observed Huawei device identity."""
from dataclasses import dataclass
import re
from .fastboot_identity import canonical_chipset

@dataclass(frozen=True)
class ObservedTarget:
    model: str = ""
    chipset: str = ""
    conflict: bool = False
    loader_variant: str = ""

def observed_target(snapshot, payload, lookup):
    if not snapshot.connected or not snapshot.serial:
        return ObservedTarget()
    xray=payload.get("xray",{})
    bound=isinstance(xray,dict) and xray.get("status")=="BOUND"
    if snapshot.interface not in {"ADB","Fastboot"} and not bound:
        return ObservedTarget()
    model=str(snapshot.model or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,8}-[A-Z0-9]{2,12}",model):
        model=""
    raw=str(snapshot.platform or "").strip().lower().replace(" ","")
    raw=raw.removeprefix("qualcomm").removeprefix("mediatek")
    chip=canonical_chipset(raw) if re.fullmatch(r"(?:kirin|hisi)[0-9]{3,4}[ac]?|(?:msm|sdm|sm|mt)[0-9]{4}|(?:hisi)?k3v2",raw) else ""
    catalog=canonical_chipset(lookup(model)) if model else ""
    exact=raw if raw.startswith("hisi") else raw.replace("kirin","hisi",1)
    families={
        "kirin650":{"hisi65x_a","hisi65x_b"},
        "kirin655":{"hisi65x_a","hisi65x_b"},
        "kirin658":{"hisi65x_a","hisi65x_b"},
        "kirin659":{"hisi65x_a","hisi65x_b"},
    }
    if exact in families.get(catalog,set()):
        return ObservedTarget(model,catalog,False,exact)
    # An explicit newer silicon suffix refines a generic catalogue family.
    # Do not infer an exact variant from an unqualified numeric chipset.
    refinements={"kirin620":"kirin620c","kirin710":"kirin710a"}
    if catalog in refinements and chip==refinements[catalog]:
        return ObservedTarget(model,catalog,False,exact)
    if chip and catalog and chip!=catalog:
        return ObservedTarget(model,chip,True)
    return ObservedTarget(model,chip or catalog)
