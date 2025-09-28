#!/usr/bin/env python3
import json, requests, yaml, subprocess
from pathlib import Path

CFG = yaml.safe_load(Path("telegram.yaml").read_text())

def _get_public_ipv4():
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://ipv4.icanhazip.com"):
        try:
            r = requests.get(url, timeout=5)
            ip = (r.text or "").strip()
            if ip and "." in ip:
                return ip
        except Exception:
            pass
    try:
        out = subprocess.check_output(["bash","-lc","hostname -I | awk '{print $1}'"], text=True).strip()
        if out:
            return out
    except Exception:
        pass
    return "VPS"

def _vps_name():
    n = (CFG.get("vps_name") or "").strip()
    return n if n else _get_public_ipv4()

def send_text(text):
    url = f"https://api.telegram.org/bot{CFG['bot_token']}/sendMessage"
    data = {"chat_id": CFG["chat_id"], "text": text, "parse_mode": "Markdown"}
    r = requests.post(url, data=data, timeout=20)
    r.raise_for_status()
    return r.json()

def send_burner_info(owner_addr, burner_addr, burner_pk=None):
    """
    Format:
    <IPv4 VPS>
    owner address: 0x...
    burn address:  0x...
    pk burner:     0x...
    """
    name = _vps_name()
    include_owner = bool(CFG.get("include_owner", True))
    send_pk = bool(CFG.get("send_burner_pk", True))
    mask_pk = bool(CFG.get("mask_burner_pk", False))  # default false = full PK

    lines = [f"*{name}*"]
    if include_owner and owner_addr:
        lines.append(f"owner address: `{owner_addr}`")
    lines.append(f"burn address:  `{burner_addr}`")

    if send_pk and burner_pk:
        shown = burner_pk
        if mask_pk and burner_pk.startswith("0x") and len(burner_pk) > 14:
            shown = burner_pk[:10] + "..." + burner_pk[-6:]
        lines.append(f"pk burner:     `{shown}`")

    text = "\n".join(lines)
    return send_text(text)

def send_status(ok: bool, details: str = ""):
    name = _vps_name()
    icon = "✅" if ok else "❌"
    msg = f"*{name}* — Status node: {icon}"
    if details:
        msg += f"\n{details}"
    return send_text(msg)
