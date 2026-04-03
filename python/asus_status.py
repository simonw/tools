#!/usr/bin/env python3
"""
Fetch network status from an ASUS ZenWiFi XT8 router via its HTTP API.

Uses the same API that the ASUS Router mobile app uses (appGet.cgi),
which requires a specific User-Agent header to bypass the single-session
lock that affects the web UI.

Usage:
    python asus_status.py [--host HOST] [--username USER] [--password PASS] [--json]
"""

import argparse
import base64
import getpass
import json
import sys
import urllib.request
import urllib.parse
import urllib.error

USER_AGENT = "asusrouter-Android-DUTUtil-1.0.0.3.58-163"


def login(host, username, password):
    """Authenticate and return the asus_token session cookie."""
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    data = urllib.parse.urlencode({"login_authorization": auth}).encode()
    req = urllib.request.Request(
        f"http://{host}/login.cgi",
        data=data,
        headers={"User-Agent": USER_AGENT},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    for header in resp.headers.get_all("Set-Cookie") or []:
        if "asus_token=" in header:
            return header.split("asus_token=")[1].split(";")[0]
    raise RuntimeError("Login failed — no asus_token in response")


def logout(host, token):
    """Release the session so it doesn't block other logins."""
    req = urllib.request.Request(
        f"http://{host}/Logout.asp",
        headers={
            "User-Agent": USER_AGENT,
            "Cookie": f"asus_token={token}",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def api_call(host, token, hook):
    """POST to appGet.cgi with the given hook string, return parsed JSON."""
    data = urllib.parse.urlencode({"hook": hook}).encode()
    req = urllib.request.Request(
        f"http://{host}/appGet.cgi",
        data=data,
        headers={
            "User-Agent": USER_AGENT,
            "Cookie": f"asus_token={token}",
        },
    )
    resp = urllib.request.urlopen(req, timeout=15)
    body = resp.read().decode()
    if "Main_Login.asp" in body:
        raise RuntimeError("Session expired — got login redirect")
    return json.loads(body)


def get_nvram(host, token, keys):
    """Fetch multiple nvram values in a single request."""
    hook = ";".join(f"nvram_get({k})" for k in keys)
    return api_call(host, token, hook)


BAND_NAMES = {"0": "2.4GHz", "1": "5GHz-1", "2": "5GHz-2"}
WL_BAND = {"0": "wired", "1": "2.4GHz", "2": "5GHz"}


def _resolve_node_name(nodes, mac):
    """Resolve a MAC to a node alias. Checks primary MAC and all radio MACs."""
    for n in nodes:
        if n["mac"] == mac:
            return n["alias"]
        # Check radio-specific MACs (ap2g, ap5g, ap5g1, apdwb, sta2g, sta5g)
        for key in ("ap2g", "ap5g", "ap5g1", "apdwb", "ap6g", "sta2g", "sta5g", "sta6g",
                     "ap2g_fh", "ap5g_fh", "ap5g1_fh"):
            if n.get(key) == mac:
                return n["alias"]
    return mac


def format_rssi(rssi):
    """Return RSSI with a quality label."""
    try:
        val = int(rssi)
    except (ValueError, TypeError):
        return rssi or "n/a"
    if val >= -50:
        quality = "excellent"
    elif val >= -60:
        quality = "good"
    elif val >= -70:
        quality = "fair"
    elif val >= -80:
        quality = "weak"
    else:
        quality = "very weak"
    return f"{val} dBm ({quality})"


def fetch_all(host, token):
    """Gather all useful status info and return as a dict."""
    result = {}

    # -- Device info and wireless config --
    nvram_keys = [
        "productid", "firmver", "buildno", "extendno",
        "lan_ipaddr", "wan0_ipaddr", "wan_proto",
        "smart_connect_x",
        "wl0_ssid", "wl1_ssid", "wl2_ssid",
        "wl0_channel", "wl1_channel", "wl2_channel",
        "wl0_chanspec", "wl1_chanspec", "wl2_chanspec",
        "wl0_bw", "wl1_bw", "wl2_bw",
        "wl0_bw_160", "wl1_bw_160", "wl2_bw_160",
        "wl0_nmode_x", "wl1_nmode_x", "wl2_nmode_x",
        "wl0_11ax", "wl1_11ax", "wl2_11ax",
        "wl0_auth_mode_x", "wl1_auth_mode_x", "wl2_auth_mode_x",
        "wl0_closed", "wl1_closed", "wl2_closed",
        "wl0_radio", "wl1_radio", "wl2_radio",
        "wl0_mfp", "wl1_mfp", "wl2_mfp",
        "wl0_twt", "wl1_twt", "wl2_twt",
    ]
    result["nvram"] = get_nvram(host, token, nvram_keys)

    # -- AiMesh nodes --
    result["aimesh"] = api_call(host, token, "get_cfg_clientlist()")

    # -- Client list --
    result["clients"] = api_call(host, token, "get_clientlist()")

    # -- Per-band station lists --
    result["stations"] = api_call(
        host, token,
        "wl_sta_list_2g();wl_sta_list_5g();wl_sta_list_5g_2()"
    )

    # -- WAN/LAN port status --
    result["ports"] = api_call(host, token, "get_wan_lan_status()")

    # -- Available channels --
    result["channels"] = api_call(
        host, token,
        "channel_list_2g();channel_list_5g();channel_list_5g_2()"
    )

    return result


def print_report(data):
    """Print a human-readable summary."""
    nv = data["nvram"]

    print("=" * 65)
    print(f"  ASUS {nv.get('productid', '?')}  —  Firmware {nv.get('firmver', '?')}.{nv.get('buildno', '?')}_{nv.get('extendno', '?')}")
    print(f"  LAN: {nv.get('lan_ipaddr', '?')}   WAN: {nv.get('wan0_ipaddr', '?')} ({nv.get('wan_proto', '?')})")
    print("=" * 65)

    # Wireless bands
    print("\n── Wireless Bands ──")
    smart = {"0": "Off", "1": "Tri-Band Smart Connect"}.get(
        nv.get("smart_connect_x", ""), nv.get("smart_connect_x", "?")
    )
    print(f"  Smart Connect: {smart}")
    for i, label in [(0, "2.4 GHz"), (1, "5 GHz-1"), (2, "5 GHz-2 (backhaul)")]:
        ssid = nv.get(f"wl{i}_ssid", "?")
        ch = nv.get(f"wl{i}_chanspec", "?") or nv.get(f"wl{i}_channel", "auto")
        bw = nv.get(f"wl{i}_bw", "?")
        ax = "ax" if nv.get(f"wl{i}_11ax") == "1" else "non-ax"
        radio = "on" if nv.get(f"wl{i}_radio") == "1" else "OFF"
        hidden = " [hidden]" if nv.get(f"wl{i}_closed") == "1" else ""
        print(f"  {label}: SSID={ssid}{hidden}  ch={ch}  bw={bw}  {ax}  radio={radio}")

    # AiMesh nodes
    print("\n── AiMesh Nodes ──")
    nodes = data["aimesh"].get("get_cfg_clientlist", [])
    for node in nodes:
        alias = node.get("alias", "?")
        ip = node.get("ip", "?")
        mac = node.get("mac", "?")
        online = "ONLINE" if node.get("online") == "1" else "OFFLINE"
        level = node.get("level", "?")
        fw = node.get("fwver", "?")

        rssi_2g = node.get("rssi2g", "")
        rssi_5g = node.get("rssi5g", "")
        pap_2g = node.get("pap2g", "")
        pap_5g = node.get("pap5g", "")

        print(f"\n  {alias} ({ip}) — {online}")
        print(f"    MAC: {mac}  Level: {level}  FW: {fw}")
        if pap_5g:
            parent = _resolve_node_name(nodes, pap_5g)
            print(f"    Backhaul 5GHz → {parent}: {format_rssi(rssi_5g)}")
        if pap_2g:
            parent = _resolve_node_name(nodes, pap_2g)
            print(f"    Backhaul 2.4GHz → {parent}: {format_rssi(rssi_2g)}")
        if not pap_5g and not pap_2g and level == "0":
            print("    (main router — no backhaul)")

    # Connected clients
    print("\n── Connected Clients ──")
    clients_data = data["clients"].get("get_clientlist", {})
    maclist = clients_data.pop("maclist", [])
    maclist = clients_data.pop("ClientAPILevel", maclist)

    # Separate online/offline and mesh nodes
    online_clients = []
    offline_clients = []
    mesh_macs = {n["mac"] for n in nodes}

    for mac, info in clients_data.items():
        if not isinstance(info, dict):
            continue
        if mac in mesh_macs:
            continue
        if info.get("amesh_isRe") == "1":
            continue
        if info.get("isOnline") == "1":
            online_clients.append(info)
        else:
            offline_clients.append(info)

    if online_clients:
        print(f"\n  Online ({len(online_clients)}):")
        for c in sorted(online_clients, key=lambda x: x.get("rssi", "0")):
            name = c.get("nickName") or c.get("name") or c.get("mac")
            ip = c.get("ip", "?")
            rssi = format_rssi(c.get("rssi"))
            band = WL_BAND.get(c.get("isWL", ""), "?")
            tx = c.get("curTx", "")
            rx = c.get("curRx", "")
            uptime = c.get("wlConnectTime", "")
            via_node = ""
            pap = c.get("amesh_papMac", "")
            if pap:
                via_name = next(
                    (n["alias"] for n in nodes if n["mac"] == pap), pap
                )
                via_node = f" via {via_name}"
            print(f"    {name:30s} {ip:16s} {band:8s} RSSI={rssi}")
            if tx or uptime:
                print(f"      Tx/Rx: {tx}/{rx} Mbps  uptime: {uptime}{via_node}")

    if offline_clients:
        print(f"\n  Recently seen, now offline ({len(offline_clients)}):")
        for c in sorted(offline_clients, key=lambda x: x.get("rssi", "0")):
            name = c.get("nickName") or c.get("name") or c.get("mac")
            rssi = format_rssi(c.get("rssi"))
            band = WL_BAND.get(c.get("isWL", ""), "?")
            print(f"    {name:30s} {band:8s} last RSSI={rssi}")

    # Per-band station RSSI (live)
    print("\n── Live Station RSSI (from radio) ──")
    for band_key, band_name in [
        ("wl_sta_list_2g", "2.4 GHz"),
        ("wl_sta_list_5g", "5 GHz-1"),
        ("wl_sta_list_5g_2", "5 GHz-2 (backhaul)"),
    ]:
        stations = data["stations"].get(band_key, {})
        if stations:
            print(f"  {band_name}:")
            for mac, info in stations.items():
                name = mac
                # Try to find name from client list
                if mac in clients_data and isinstance(clients_data[mac], dict):
                    name = clients_data[mac].get("nickName") or clients_data[mac].get("name") or mac
                rssi = format_rssi(info.get("rssi"))
                print(f"    {name:30s} {mac}  RSSI={rssi}")
        else:
            print(f"  {band_name}: (no stations)")

    # Port status
    print("\n── Port Status ──")
    ports = data["ports"].get("get_wan_lan_status", {}).get("portSpeed", {})
    for port, speed in ports.items():
        status = {"G": "1 Gbps", "M": "100 Mbps", "X": "disconnected"}.get(speed, speed)
        print(f"  {port}: {status}")

    print()


def main():
    parser = argparse.ArgumentParser(description="ASUS router network status")
    parser.add_argument("--host", default="192.168.50.1", help="Router IP (default: 192.168.50.1)")
    parser.add_argument("--username", "-u", required=True, help="Admin username")
    parser.add_argument("--password", "-p", help="Admin password (will prompt if not provided)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of report")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Router password: ")
    token = login(args.host, args.username, password)
    try:
        data = fetch_all(args.host, token)
        if args.json:
            json.dump(data, sys.stdout, indent=2)
            print()
        else:
            print_report(data)
    finally:
        logout(args.host, token)


if __name__ == "__main__":
    main()
