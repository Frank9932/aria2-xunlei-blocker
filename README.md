# aria2-xunlei-blocker
A lightweight, behavior-based anti-leeching tool for aria2 BitTorrent peers.

This project detects and blocks Xunlei and Xunlei-like leeching clients
by analyzing aria2 RPC peer information and peer behavior.

## Intended audience

This tool is intended for users who:

- Use aria2 with RPC enabled
- Run aria2 on Linux (VPS / NAS / server)
- Understand iptables and ipset basics
- Want more control than aria2 natively provides

This is NOT a one-click solution for beginners.

## Requirements

The following components are assumed to be present:

- Linux system with root access
- Python 3.8+
- aria2 with RPC enabled
- iptables
- ipset
- Python requests module

No dependency installation is performed by this project.

## How it works

1. Query active BitTorrent peers via aria2 RPC
2. Decode peerId (URL-encoded raw bytes)
3. Apply detection rules:
   - peerId starting with "-XL"(Xunlei clients) → immediate ban
   - otherwise, apply behavior scoring:
     - high download speed
     - low or zero upload
4. Block IPs using ipset with timeout

## Detection logic

For non-XL peers, a leeching score is calculated:

score = (1 - upload/download) * log2(download + 1)

Peers exceeding the score threshold are considered leeching.

## Usage

1. Enable aria2 RPC
2. Ensure ipset and iptables are available
3. Edit configuration section inside the script if needed
4. Run the script as root:

```bash
sudo python3 peer_inspect_ban_ipset.py

