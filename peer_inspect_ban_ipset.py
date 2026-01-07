#!/usr/bin/env python3
"""
aria2-xunlei-blocker

A behavior-based anti-leeching tool for aria2 BitTorrent peers.

Core features:
- Decode aria2 RPC peerId (URL-encoded raw bytes)
- Identify Xunlei clients (-XL peerId)
- Detect leeching behavior via upload/download ratio
- Block peers using ipset with timeout

This script assumes:
- Linux system
- aria2 with RPC enabled
- ipset + iptables already available

Author: <your handle>
License: MIT
"""
import requests
import subprocess
import math
import time
from urllib.parse import unquote_to_bytes

# aria2 RPC endpoint
ARIA2_RPC = "http://127.0.0.1:6800/jsonrpc"
TOKEN = "token:YOUR_SECRET"

# === Detection and blocking parameters ===
DL_MIN = 50 * 1024          # Minimum download speed (50 KB/s)
SCORE_BAN = 6.0             # Leeching score threshold
BAN_TIMEOUT = 86400         # Ban duration in seconds (24 hours)
DRY_RUN = False             # If True, do not actually block IPs

# =========================================

def rpc(method, params):
    """
    Perform a JSON-RPC call to aria2.
    """
    payload = {
        "jsonrpc": "2.0",
        "id": "inspect",
        "method": method,
        "params": [TOKEN] + params
    }
    r = requests.post(ARIA2_RPC, json=payload, timeout=5)
    r.raise_for_status()
    return r.json()["result"]


def decode_peer_id(peer_id: str) -> str:
    """
    Decode aria2 peerId.

    aria2 returns peerId as URL-encoded raw bytes.
    This function converts it back to a readable ASCII string.
    """
    raw = unquote_to_bytes(peer_id)
    return raw.decode("ascii", errors="replace")


def parse_client_tag(pid_ascii: str) -> str:
    """
    Extract a short client identifier from the decoded peerId.

    Examples:
    - '-XLxxxx-'  -> 'XL'        (Xunlei)
    - '-qB4670-'  -> 'qB4670'    (qBittorrent)
    - '-TR4040-'  -> 'TR4040'    (Transmission)
    """
    if pid_ascii.startswith("-XL"):
        return "XL"

    if len(pid_ascii) >= 8 and pid_ascii[0] == "-" and pid_ascii[3].isdigit():
        return pid_ascii[1:7]

    return "UNK"


def ipset_add(ip):
    """
    Add an IP address to the ipset blacklist with timeout.
    """
    cmd = [
        "ipset", "add", "xunlei_blacklist", ip,
        "timeout", str(BAN_TIMEOUT), "-exist"
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    print(f"\n[{time.strftime('%F %T')}] scan start")

    # Retrieve all active aria2 tasks
    gids = rpc("aria2.tellActive", [])

    for g in gids:
        # Retrieve peers for each active task
        peers = rpc("aria2.getPeers", [g["gid"]])

        for p in peers:
            ip = p.get("ip")
            dl = int(p.get("downloadSpeed", "0"))
            ul = int(p.get("uploadSpeed", "0"))
            seeder = p.get("seeder") == "true"

            pid_ascii = decode_peer_id(p.get("peerId", ""))
            client = parse_client_tag(pid_ascii)

            # === Strategy C: immediately block Xunlei peers ===
            if client == "XL":
                print(f"{ip:15} XL      DIRECT BAN")
                if not DRY_RUN:
                    ipset_add(ip)
                continue

            # === Non-Xunlei peers: apply behavior-based scoring ===
            if seeder or dl < DL_MIN:
                continue

            ratio = ul / (dl + 1)
            score = (1 - ratio) * math.log2(dl + 1)

            print(
                f"{ip:15} {client:6} "
                f"DL={dl//1024:4}KB "
                f"UL={ul//1024:4}KB "
                f"R={ratio:.3f} "
                f"S={score:.2f}"
            )

            if score >= SCORE_BAN:
                print("  >>> SCORE BAN")
                if not DRY_RUN:
                    ipset_add(ip)

    print(f"[{time.strftime('%F %T')}] scan end")


if __name__ == "__main__":
    main()
