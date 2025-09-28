#!/usr/bin/env python3
import json, time, re, subprocess, yaml
from pathlib import Path
from web3 import Web3
from eth_account import Account
from telegram_send import send_burner_info, send_status

# Directories for node cache
BASE_DIR = Path.home() / ".mawari_automation"
WORKER = "worker1"
WORKER_DIR = BASE_DIR / "workers" / WORKER
CACHE_DIR = WORKER_DIR / "cache"
META = WORKER_DIR / "meta.json"
CACHE_JSON = CACHE_DIR / "flohive-cache.json"

def load_cfg():
    return yaml.safe_load(Path("config.yaml").read_text())

def ensure_dirs():
    for p in (WORKER_DIR, CACHE_DIR):
        p.mkdir(parents=True, exist_ok=True)

def derive_owner(cfg):
    if cfg.get("owner_address"):
        return cfg["owner_address"]
    return Account.from_key(cfg["owner_private_key"]).address

def run_container(image, owner_addr):
    print("== Run Guardian node ==")
    cname = f"mawari_{WORKER}"
    subprocess.run(["bash","-lc", f"docker rm -f {cname} >/dev/null 2>&1 || true"])
    cmd = ["docker","run","--pull","always","--name",cname,
           "-v", f"{str(CACHE_DIR)}:/app/cache",
           "-e", f"OWNERS_ALLOWLIST={owner_addr}",
           "--restart=unless-stopped","-d", image]
    print(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout + r.stderr)
    else:
        print(r.stdout.strip())

def capture_burner(timeout=60):
    print("== Capture burner address ==")
    cname = f"mawari_{WORKER}"
    p = subprocess.Popen(["docker","logs","-f","--tail=200",cname], stdout=subprocess.PIPE, text=True)
    burner = None; t0 = time.time()
    while time.time() - t0 < timeout:
        line = p.stdout.readline()
        if not line:
            time.sleep(0.1); continue
        print(line, end="")
        m = re.search(r'Using burner wallet.*\{"address":\s*"(0x[0-9a-fA-F]+)"}', line)
        if m:
            burner = m.group(1); break
    try: p.terminate()
    except: pass
    if burner:
        META.write_text(json.dumps({"burner": burner}, indent=2))
        print("Burner:", burner)
    else:
        print("Failed to capture burner in logs.")
    return burner

def get_burner_pk_from_cache():
    try:
        d = json.loads(CACHE_JSON.read_text())
        for k in ("privateKey","private_key","ethPrivateKey"):
            if k in d and d[k]:
                return d[k]
        if "wallet" in d:
            for k in ("privateKey","private_key"):
                if k in d["wallet"] and d["wallet"][k]:
                    return d["wallet"][k]
    except Exception:
        pass
    return None

def get_balance_native(w3, addr):
    return float(w3.from_wei(w3.eth.get_balance(w3.to_checksum_address(addr)), "ether"))

def wait_for_balance(w3, addr, min_need, tries=10, sleep=6):
    min_need = float(min_need)
    for _ in range(tries):
        bal = get_balance_native(w3, addr)
        print(f"[BAL] {addr} = {bal:.6f} MAWARI (need >= {min_need})")
        if bal >= min_need:
            return True
        time.sleep(sleep)
    return False

def transfer_native_v7(w3, sender_pk, to_addr, amount_native, chain_id):
    sender_addr = Account.from_key(sender_pk).address
    tx = {
        "to": w3.to_checksum_address(to_addr),
        "value": int(float(amount_native) * (10**18)),
        "gas": 21000,
        "gasPrice": w3.eth.gas_price,
        "nonce": w3.eth.get_transaction_count(sender_addr),
        "chainId": int(chain_id),
    }
    signed = w3.eth.account.sign_transaction(tx, private_key=sender_pk)
    txh = w3.eth.send_raw_transaction(signed.raw_transaction)  # Web3.py v7
    return w3.to_hex(txh)

def watch_heartbeat(timeout=900):
    """Pantau log container sampai ada heartbeat; kirim Telegram status."""
    cname = f"mawari_{WORKER}"
    p = subprocess.Popen(["docker","logs","-f","--tail=200",cname], stdout=subprocess.PIPE, text=True)
    t0 = time.time(); ok = False; buf=[]
    patterns = [
        r"delegation offer accepted",
        r"successfully submitted heartbeat",
        r"sending heartbeat"
    ]
    try:
        while time.time() - t0 < timeout:
            line = p.stdout.readline()
            if not line:
                time.sleep(0.1); continue
            buf.append(line.rstrip())
            if any(re.search(pat, line, re.IGNORECASE) for pat in patterns):
                ok = True; break
    finally:
        try: p.terminate()
        except: pass
    tail = "\n".join(buf[-12:])
    send_status(ok, details=f"```{tail}```")
    return ok

def main():
    cfg = load_cfg()
    ensure_dirs()
    owner_addr = derive_owner(cfg)
    print("Owner:", owner_addr)

    # 1) Start node & capture burner
    run_container(cfg["docker_image"], owner_addr)
    burner = capture_burner()
    if not burner:
        print("Gagal dapat burner dari log.")
        send_status(False, "```Failed to capture burner```")
        return

    # 2) Kirim notifikasi Telegram (owner + burner + PK kalau ada)
    burner_pk = get_burner_pk_from_cache()
    try:
        send_burner_info(owner_addr, burner, burner_pk)
    except Exception as e:
        print("Telegram send error:", e)

    # 3) Fund burner dari owner jika kurang
    w3 = Web3(Web3.HTTPProvider(cfg["rpc_url"]))
    min_bal = cfg.get("min_burner_balance", "0.5")
    if not wait_for_balance(w3, burner, min_bal, tries=1, sleep=1):
        amt = cfg.get("fund_burner_amount", "1")
        print(f"Funding burner {burner} from owner ({amt} MAWARI)")
        try:
            txh = transfer_native_v7(w3, cfg["owner_private_key"], burner, amt, cfg["chain_id"])
            print("Fund tx:", txh)
        except Exception as e:
            print("Funding error:", e)
        wait_for_balance(w3, burner, min_bal, tries=10, sleep=6)

    # 4) Watch heartbeat & kirim status ke Telegram
    watch_heartbeat(timeout=900)

if __name__ == "__main__":
    main()
