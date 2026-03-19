#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


APPLE_SCRIPT = r"""
set fieldSep to ASCII character 31
set outLines to {}
tell application "Terminal"
  set winIndex to 0
  repeat with w in windows
    set winIndex to winIndex + 1
    set tabIndex to 0
    repeat with t in tabs of w
      set tabIndex to tabIndex + 1
      set tabTitle to ""
      try
        set tabTitle to custom title of t
      end try
      if tabTitle is missing value then set tabTitle to ""
      set end of outLines to (winIndex as text) & fieldSep & (tabIndex as text) & fieldSep & (tty of t) & fieldSep & (busy of t as text) & fieldSep & tabTitle
    end repeat
  end repeat
end tell
set AppleScript's text item delimiters to linefeed
return outLines as text
"""

TERMINAL_APP_MARKERS = (
    "/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal",
    "/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal",
)

SESSION_HELPERS = {
    "login",
    "sh",
    "-sh",
    "bash",
    "-bash",
    "zsh",
    "-zsh",
    "fish",
    "-fish",
    "ksh",
    "-ksh",
    "tcsh",
    "-tcsh",
}


@dataclass
class ProcessInfo:
    pid: int
    ppid: int
    tty: str
    rss_kb: int
    comm: str
    args: str
    owner_tty: Optional[str] = None

    @property
    def display_name(self) -> str:
        token = ""
        args = self.args.strip()
        if args:
            try:
                token = shlex.split(args)[0]
            except ValueError:
                token = args.split()[0]
        if not token:
            token = self.comm
        name = os.path.basename(token) or os.path.basename(self.comm) or self.comm
        return name.lstrip("-") or self.comm.lstrip("-") or self.comm

    @property
    def is_helper(self) -> bool:
        return self.display_name in {name.lstrip("-") for name in SESSION_HELPERS}

    def short_command(self, limit: int = 72) -> str:
        text = self.args.strip() or self.comm.strip()
        return shorten(text, limit)


@dataclass
class SessionInfo:
    tty: str
    window: int
    tab: int
    title: str
    busy: bool
    attached_processes: List[ProcessInfo] = field(default_factory=list)
    tree_processes: List[ProcessInfo] = field(default_factory=list)

    @property
    def attached_rss_kb(self) -> int:
        return sum(proc.rss_kb for proc in self.attached_processes)

    @property
    def tree_rss_kb(self) -> int:
        return sum(proc.rss_kb for proc in self.tree_processes)

    @property
    def detached_rss_kb(self) -> int:
        return self.tree_rss_kb - self.attached_rss_kb

    @property
    def helper_rss_kb(self) -> int:
        return sum(proc.rss_kb for proc in self.tree_processes if proc.is_helper)

    @property
    def workload_rss_kb(self) -> int:
        return self.tree_rss_kb - self.helper_rss_kb

    @property
    def workload_processes(self) -> List[ProcessInfo]:
        return [proc for proc in self.tree_processes if not proc.is_helper]

    @property
    def top_processes(self) -> List[ProcessInfo]:
        return sorted(self.tree_processes, key=lambda proc: proc.rss_kb, reverse=True)

    @property
    def status(self) -> str:
        if self.workload_rss_kb == 0:
            return "idle"
        if self.busy:
            return "busy"
        if self.detached_rss_kb > 0:
            return "detached"
        return "active"

    def label(self) -> str:
        if self.title and self.title != "Terminal":
            return self.title
        for proc in self.top_processes:
            if not proc.is_helper:
                return proc.short_command(40)
        return "Shell"


def shorten(text: str, limit: int) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 3:
        return cleaned[:limit]
    return cleaned[: limit - 3] + "..."


def human_kib(kib: int) -> str:
    value = float(kib)
    units = ["KiB", "MiB", "GiB", "TiB"]
    unit = units[0]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            break
        value /= 1024.0
    if value >= 100:
        return f"{value:,.0f} {unit}"
    if value >= 10:
        return f"{value:,.1f} {unit}"
    return f"{value:,.2f} {unit}"


def pct(value: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(100.0 * value / total):4.1f}%"


def ascii_bar(value: int, total: int, width: int) -> str:
    if width <= 0:
        return ""
    if total <= 0 or value <= 0:
        return "-" * width
    filled = int(round((value / total) * width))
    filled = max(0, min(width, filled))
    return "#" * filled + "-" * (width - filled)


def run_command(argv: List[str], stdin: Optional[str] = None) -> str:
    try:
        result = subprocess.run(
            argv,
            input=stdin,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required command not found: {argv[0]}") from exc
    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown error"
        raise RuntimeError(f"{argv[0]} failed: {stderr}")
    return result.stdout


def collect_tabs() -> Dict[str, SessionInfo]:
    raw = run_command(["osascript"], stdin=APPLE_SCRIPT)
    sessions: Dict[str, SessionInfo] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f")
        if len(parts) < 5:
            continue
        window_text, tab_text, tty_text, busy_text, title = parts[:5]
        tty = tty_text.strip().replace("/dev/", "")
        if not tty:
            continue
        session = SessionInfo(
            tty=tty,
            window=int(window_text),
            tab=int(tab_text),
            title=title.strip() or "Terminal",
            busy=busy_text.strip().lower() == "true",
        )
        sessions[tty] = session
    return sessions


def parse_ps_line(line: str) -> Optional[ProcessInfo]:
    parts = line.split(None, 5)
    if len(parts) < 5:
        return None
    if len(parts) == 5:
        pid_text, ppid_text, tty, rss_text, comm = parts
        args = comm
    else:
        pid_text, ppid_text, tty, rss_text, comm, args = parts
    try:
        return ProcessInfo(
            pid=int(pid_text),
            ppid=int(ppid_text),
            tty=tty.strip(),
            rss_kb=int(rss_text),
            comm=comm.strip(),
            args=args.rstrip(),
        )
    except ValueError:
        return None


def collect_processes() -> Dict[int, ProcessInfo]:
    raw = run_command(["ps", "-axo", "pid=,ppid=,tty=,rss=,comm=,args="])
    processes: Dict[int, ProcessInfo] = {}
    for line in raw.splitlines():
        proc = parse_ps_line(line)
        if proc is not None:
            processes[proc.pid] = proc
    return processes


def build_children_map(processes: Dict[int, ProcessInfo]) -> Dict[int, List[int]]:
    children: Dict[int, List[int]] = defaultdict(list)
    for proc in processes.values():
        children[proc.ppid].append(proc.pid)
    return children


def walk_descendants(root_pids: Iterable[int], children_map: Dict[int, List[int]]) -> List[int]:
    seen = set()
    stack = list(root_pids)
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        stack.extend(children_map.get(pid, []))
    return list(seen)


def attribute_owner_tty(
    pid: int,
    processes: Dict[int, ProcessInfo],
    terminal_ttys: set[str],
    cache: Dict[int, Optional[str]],
    trail: Optional[set[int]] = None,
) -> Optional[str]:
    if pid in cache:
        return cache[pid]
    proc = processes.get(pid)
    if proc is None:
        cache[pid] = None
        return None
    if proc.tty in terminal_ttys:
        cache[pid] = proc.tty
        return proc.tty
    if proc.ppid <= 0 or proc.ppid == pid:
        cache[pid] = None
        return None
    if trail is None:
        trail = set()
    if pid in trail:
        cache[pid] = None
        return None
    trail.add(pid)
    owner = attribute_owner_tty(proc.ppid, processes, terminal_ttys, cache, trail)
    cache[pid] = owner
    return owner


def collect_report(include_self: bool = False) -> dict:
    sessions = collect_tabs()
    terminal_ttys = set(sessions.keys())
    processes = collect_processes()
    children_map = build_children_map(processes)
    self_tree = set(walk_descendants([os.getpid()], children_map))

    terminal_app_processes = [
        proc
        for proc in processes.values()
        if any(marker in proc.args for marker in TERMINAL_APP_MARKERS)
    ]

    attached_pids = {proc.pid for proc in processes.values() if proc.tty in terminal_ttys}
    tree_pids = set(walk_descendants(attached_pids, children_map))
    if not include_self:
        attached_pids -= self_tree
        tree_pids -= self_tree
    detached_pids = tree_pids - attached_pids

    owner_cache: Dict[int, Optional[str]] = {}
    for pid in tree_pids:
        owner_tty = attribute_owner_tty(pid, processes, terminal_ttys, owner_cache)
        processes[pid].owner_tty = owner_tty
        if owner_tty and owner_tty not in sessions:
            sessions[owner_tty] = SessionInfo(
                tty=owner_tty,
                window=0,
                tab=0,
                title="Terminal",
                busy=False,
            )

    for pid in attached_pids:
        proc = processes[pid]
        if proc.tty in sessions:
            sessions[proc.tty].attached_processes.append(proc)

    for pid in tree_pids:
        proc = processes[pid]
        if proc.owner_tty and proc.owner_tty in sessions:
            sessions[proc.owner_tty].tree_processes.append(proc)

    session_list = sorted(
        sessions.values(),
        key=lambda session: session.tree_rss_kb,
        reverse=True,
    )

    command_totals: Dict[str, dict] = {}
    for pid in tree_pids:
        proc = processes[pid]
        if proc.is_helper:
            continue
        command_key = proc.display_name.lower()
        entry = command_totals.setdefault(
            command_key,
            {
                "name": proc.display_name,
                "rss_kb": 0,
                "count": 0,
                "ttys": set(),
            },
        )
        entry["rss_kb"] += proc.rss_kb
        entry["count"] += 1
        if proc.owner_tty:
            entry["ttys"].add(proc.owner_tty)

    top_commands = sorted(
        (
            {
                "name": entry["name"],
                "rss_kb": entry["rss_kb"],
                "count": entry["count"],
                "tabs": len(entry["ttys"]),
            }
            for entry in command_totals.values()
        ),
        key=lambda item: item["rss_kb"],
        reverse=True,
    )

    top_processes = sorted(
        (processes[pid] for pid in tree_pids if not processes[pid].is_helper),
        key=lambda proc: proc.rss_kb,
        reverse=True,
    )

    tree_rss_kb = sum(processes[pid].rss_kb for pid in tree_pids)
    attached_rss_kb = sum(processes[pid].rss_kb for pid in attached_pids)
    detached_rss_kb = tree_rss_kb - attached_rss_kb
    terminal_app_rss_kb = sum(proc.rss_kb for proc in terminal_app_processes)
    combined_rss_kb = tree_rss_kb + terminal_app_rss_kb

    helper_rss_kb = sum(session.helper_rss_kb for session in session_list)
    workload_rss_kb = sum(session.workload_rss_kb for session in session_list)

    idle_sessions = [session for session in session_list if session.workload_rss_kb == 0]
    busy_sessions = [session for session in session_list if session.busy]

    return {
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "sessions": session_list,
        "top_commands": top_commands,
        "top_processes": top_processes,
        "terminal_app_processes": terminal_app_processes,
        "totals": {
            "tabs": len(session_list),
            "busy_tabs": len(busy_sessions),
            "idle_tabs": len(idle_sessions),
            "attached_processes": len(attached_pids),
            "tree_processes": len(tree_pids),
            "detached_processes": len(detached_pids),
            "attached_rss_kb": attached_rss_kb,
            "tree_rss_kb": tree_rss_kb,
            "detached_rss_kb": detached_rss_kb,
            "helper_rss_kb": helper_rss_kb,
            "workload_rss_kb": workload_rss_kb,
            "terminal_app_rss_kb": terminal_app_rss_kb,
            "combined_rss_kb": combined_rss_kb,
            "idle_rss_kb": sum(session.tree_rss_kb for session in idle_sessions),
            "busy_rss_kb": sum(session.tree_rss_kb for session in busy_sessions),
        },
    }


def render_summary(report: dict) -> List[str]:
    totals = report["totals"]
    lines = [
        f"Terminal Memory Report on {report['hostname']}",
        f"Generated: {report['generated_at']}",
        "",
        "Summary",
        f"  Tabs seen:              {totals['tabs']}",
        f"  Busy tabs:              {totals['busy_tabs']}",
        f"  Idle shell tabs:        {totals['idle_tabs']}",
        f"  Processes on TTYs:      {totals['attached_processes']}",
        f"  Total process tree:     {totals['tree_processes']}",
        f"  Detached descendants:   {totals['detached_processes']}",
        f"  Terminal.app RSS:       {human_kib(totals['terminal_app_rss_kb'])}",
        f"  Attached session RSS:   {human_kib(totals['attached_rss_kb'])}",
        f"  Full session tree RSS:  {human_kib(totals['tree_rss_kb'])}",
        f"  Combined total RSS:     {human_kib(totals['combined_rss_kb'])}",
        "",
    ]
    return lines


def render_breakdown(report: dict, width: int) -> List[str]:
    totals = report["totals"]
    combined = totals["combined_rss_kb"]
    tree_total = totals["tree_rss_kb"]
    bar_width = min(32, max(10, width - 48))

    rows = [
        ("Workload processes", totals["workload_rss_kb"], combined),
        ("Shell/login overhead", totals["helper_rss_kb"], combined),
        ("Terminal.app UI", totals["terminal_app_rss_kb"], combined),
    ]
    lines = ["Memory Breakdown"]
    for label, value, total in rows:
        lines.append(
            f"  {label:<20} {human_kib(value):>10} [{ascii_bar(value, total, bar_width)}] {pct(value, total)}"
        )
    if totals["detached_rss_kb"] > 0:
        lines.append(
            f"  {'Detached child RSS':<20} {human_kib(totals['detached_rss_kb']):>10} [{ascii_bar(totals['detached_rss_kb'], tree_total, bar_width)}] {pct(totals['detached_rss_kb'], tree_total)} of session tree"
        )
    lines.append(
        f"  {'Idle shell tabs':<20} {human_kib(totals['idle_rss_kb']):>10} [{ascii_bar(totals['idle_rss_kb'], tree_total, bar_width)}] {pct(totals['idle_rss_kb'], tree_total)} of session tree"
    )
    lines.append("")
    return lines


def render_sessions(report: dict, width: int, limit: int) -> List[str]:
    sessions: List[SessionInfo] = report["sessions"][:limit]
    tree_total = report["totals"]["tree_rss_kb"]
    bar_width = min(28, max(10, width - 68))
    lines = ["Top Tabs"]
    for session in sessions:
        slot = f"W{session.window:03d}/T{session.tab:02d}" if session.window else "W???/T??"
        label = shorten(session.label(), 34)
        lines.append(
            f"  {slot} {session.tty:<7} {human_kib(session.tree_rss_kb):>9} [{ascii_bar(session.tree_rss_kb, tree_total, bar_width)}] {pct(session.tree_rss_kb, tree_total)} {session.status:<8} {label}"
        )
        top_bits = [
            f"{proc.display_name} {human_kib(proc.rss_kb)}"
            for proc in session.top_processes[:3]
        ]
        if top_bits:
            lines.append(f"    top: {' | '.join(top_bits)}")
        if session.detached_rss_kb > 0:
            lines.append(
                f"    split: attached {human_kib(session.attached_rss_kb)}, detached {human_kib(session.detached_rss_kb)}"
            )
    lines.append("")
    return lines


def render_commands(report: dict, width: int, limit: int) -> List[str]:
    commands = report["top_commands"][:limit]
    total = report["totals"]["workload_rss_kb"]
    bar_width = min(28, max(10, width - 56))
    lines = ["Top Commands"]
    for item in commands:
        lines.append(
            f"  {item['name']:<16} {human_kib(item['rss_kb']):>9} [{ascii_bar(item['rss_kb'], total, bar_width)}] {pct(item['rss_kb'], total)}  {item['count']:>3} procs  {item['tabs']:>3} tabs"
        )
    lines.append("")
    return lines


def render_processes(report: dict, limit: int) -> List[str]:
    processes: List[ProcessInfo] = report["top_processes"][:limit]
    lines = ["Top Processes"]
    for proc in processes:
        owner = proc.owner_tty or "?"
        lines.append(
            f"  PID {proc.pid:<6} {human_kib(proc.rss_kb):>9}  {owner:<7}  {shorten(proc.short_command(88), 88)}"
        )
    lines.append("")
    return lines


def session_to_dict(session: SessionInfo) -> dict:
    return {
        "tty": session.tty,
        "window": session.window,
        "tab": session.tab,
        "title": session.title,
        "busy": session.busy,
        "status": session.status,
        "attached_rss_kb": session.attached_rss_kb,
        "tree_rss_kb": session.tree_rss_kb,
        "detached_rss_kb": session.detached_rss_kb,
        "helper_rss_kb": session.helper_rss_kb,
        "workload_rss_kb": session.workload_rss_kb,
        "top_processes": [
            {
                "pid": proc.pid,
                "rss_kb": proc.rss_kb,
                "display_name": proc.display_name,
                "command": proc.args or proc.comm,
            }
            for proc in session.top_processes[:5]
        ],
    }


def process_to_dict(proc: ProcessInfo) -> dict:
    return {
        "pid": proc.pid,
        "ppid": proc.ppid,
        "tty": proc.tty,
        "owner_tty": proc.owner_tty,
        "rss_kb": proc.rss_kb,
        "display_name": proc.display_name,
        "command": proc.args or proc.comm,
    }


def render_json(report: dict, top_sessions: int, top_commands: int, top_processes: int) -> str:
    payload = {
        "generated_at": report["generated_at"],
        "hostname": report["hostname"],
        "totals": report["totals"],
        "sessions": [session_to_dict(session) for session in report["sessions"][:top_sessions]],
        "top_commands": report["top_commands"][:top_commands],
        "top_processes": [process_to_dict(proc) for proc in report["top_processes"][:top_processes]],
        "terminal_app_processes": [process_to_dict(proc) for proc in report["terminal_app_processes"]],
    }
    return json.dumps(payload, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect Terminal.app tabs and report their RAM usage.",
    )
    parser.add_argument("--top-sessions", type=int, default=12, help="How many tabs to show.")
    parser.add_argument("--top-commands", type=int, default=10, help="How many command groups to show.")
    parser.add_argument("--top-processes", type=int, default=12, help="How many individual processes to show.")
    parser.add_argument("--include-self", action="store_true", help="Include the report process itself in the totals.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of the text report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = collect_report(include_self=args.include_self)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(render_json(report, args.top_sessions, args.top_commands, args.top_processes))
        return 0

    width = shutil.get_terminal_size((120, 24)).columns
    lines: List[str] = []
    lines.extend(render_summary(report))
    lines.extend(render_breakdown(report, width))
    lines.extend(render_sessions(report, width, args.top_sessions))
    lines.extend(render_commands(report, width, args.top_commands))
    lines.extend(render_processes(report, args.top_processes))
    print("\n".join(lines).rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
