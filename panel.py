#!/usr/bin/env python3
import os, sys, json
from pathlib import Path
from datetime import datetime
from runners.common import ROOT, cfg, ensure_dirs, sanitize_base, timestamp, read_lines

CONFIG = cfg()
ROUTES = CONFIG["routes"]
JOB_DIR = ROOT / ROUTES["output"]["job_dir"]
PERSIST = CONFIG.get("persist", {})
LAST_FILE = ROOT / PERSIST.get("file", "")


def load_last():
    if PERSIST.get("remember_last") and LAST_FILE.exists():
        try:
            return json.loads(LAST_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_last(data):
    if not PERSIST.get("remember_last"):
        return
    LAST_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAST_FILE.write_text(json.dumps(data, indent=2))


LAST = load_last()


def choose_file(options, default_path=None):
    uniq = []
    seen = set()
    for p in options:
        if p not in seen:
            uniq.append(p)
            seen.add(p)
    for idx, p in enumerate(uniq, 1):
        print(f"  [{idx}] {p}")
    while True:
        prompt = "Select file"
        if default_path:
            prompt += f" [{default_path}]"
        prompt += ": "
        val = input(prompt).strip()
        if not val and default_path:
            p = Path(default_path)
            if p.exists():
                return p
        if val.isdigit() and 1 <= int(val) <= len(uniq):
            return uniq[int(val) - 1]
        p = Path(val)
        if p.exists():
            return p
        print("[!] Invalid selection.")


def prompt_base(input_file: Path, task_key: str, mapping_func):
    last_base = LAST.get(task_key, {}).get("base")
    if last_base:
        default = last_base
    else:
        base = sanitize_base(input_file.stem)
        if CONFIG.get("naming", {}).get("suggest_timestamp", False):
            base = f"{base}_{timestamp()}"
        default = base
    while True:
        val = input(f"Base name [{default}]: ").strip() or default
        val = sanitize_base(val)
        paths = mapping_func(val)
        print("Will create:")
        for p in paths:
            print(f"  - {p}")
        if input("Proceed? [y/N]: ").strip().lower() == "y":
            return val


def task_sort_wp():
    from runners.sort_wp import sort_wordpress
    domain_dir = ROOT / ROUTES["input"]["domain_dir"]
    files = sorted(domain_dir.glob("*.txt"))
    default = LAST.get("sort_wp", {}).get("input")
    f = choose_file(files, default)
    base = prompt_base(f, "sort_wp", lambda b: [JOB_DIR / f"{b}.cms_wordpress.txt"])
    out_file = sort_wordpress(f, JOB_DIR, base)
    count = len(read_lines(out_file))
    print(f"\n[OK] WordPress targets: {count}\n -> {out_file}")
    LAST["sort_wp"] = {"input": str(f), "base": base}
    save_last(LAST)
    input("\nEnter to menu...")


def task_httpx_live():
    from runners.httpx_live import run_httpx_live
    domain_dir = ROOT / ROUTES["input"]["domain_dir"]
    files = sorted(domain_dir.glob("*.txt"))
    default = LAST.get("httpx_live", {}).get("input")
    f = choose_file(files, default)
    base = prompt_base(
        f,
        "httpx_live",
        lambda b: [JOB_DIR / f"{b}.live.txt", JOB_DIR / f"{b}.httpx.jsonl"],
    )
    live_file, jsonl, count = run_httpx_live(f, JOB_DIR, base)
    print(f"\n[OK] Live endpoints: {count}\n -> {live_file}\n -> JSON: {jsonl}")
    LAST["httpx_live"] = {"input": str(f), "base": base}
    save_last(LAST)
    input("\nEnter to menu...")


def task_wpscan():
    from runners.wpscan_fast import wpscan_fast
    job_files = list(JOB_DIR.glob("*.txt"))
    wp_dir = ROOT / ROUTES["input"]["wordpress_dir"]
    files = job_files + list(wp_dir.glob("*.txt")) + list(wp_dir.glob("*.csv"))
    default = LAST.get("wpscan", {}).get("input")
    f = choose_file(files, default)
    base = prompt_base(
        f,
        "wpscan",
        lambda b: [JOB_DIR / "wpscan_raw" / f"{b}.<host>.wpscan.json"],
    )
    run_raw_dir = wpscan_fast(f, JOB_DIR, base)
    print(
        f"\n[OK] WPScan finished. Raw JSON -> {run_raw_dir}\n Log -> {CONFIG['outputs']['logs_dir']}/wp_scan.log"
    )
    LAST["wpscan"] = {"input": str(f), "base": base}
    save_last(LAST)
    input("\nEnter to menu...")


def task_recon():
    from runners.recon_nuclei import recon_pipeline
    default = LAST.get("recon", {}).get("input")
    subs = None
    if default:
        subs = Path(default)
    else:
        for rel in ROUTES["input"]["subs_fallbacks"]:
            p = ROOT / rel
            if p.exists():
                subs = p
                break
    while True:
        prompt = f"Subs file [{subs}]: " if subs else "Subs file: "
        val = input(prompt).strip()
        if not val:
            if subs and subs.exists():
                f = subs
                break
        else:
            p = Path(val)
            if p.exists():
                f = p
                break
        print("[!] Invalid path.")
    base = prompt_base(
        f,
        "recon",
        lambda b: [
            JOB_DIR / f"{b}.nuclei-findings.jsonl",
            JOB_DIR / f"{b}.nuclei-findings.txt",
            JOB_DIR / f"{b}.summary.txt",
            JOB_DIR / f"{b}.wp-live.txt",
            JOB_DIR / f"{b}.nuclei-findings-wp.jsonl",
            JOB_DIR / f"{b}.nuclei-findings-wp.txt",
            JOB_DIR / f"{b}.summary-wp.txt",
        ],
    )
    paths = recon_pipeline(f, JOB_DIR, base)
    print(f"\n[OK] Recon completed.\n -> {paths['findings_jsonl']}\n -> {paths['findings_txt']}\n -> {paths['summary']}")
    LAST["recon"] = {"input": str(f), "base": base}
    save_last(LAST)
    input("\nEnter to menu...")


def main():
    ensure_dirs()
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("===== Recon & Vulnerability Panel (Python) =====")
        print("  [1] Sort Domain → CMS (WordPress)")
        print("  [2] Live Domain Test (httpx)")
        print("  [3] WPScan (fast, JSON)")
        print("  [4] Recon Takeover/Upload (nuclei, sharded)")
        print("  [X] Exit")
        ch = input("\nSelect option: ").strip().lower()
        if ch == "1":
            task_sort_wp()
        elif ch == "2":
            task_httpx_live()
        elif ch == "3":
            task_wpscan()
        elif ch == "4":
            task_recon()
        elif ch == "x":
            sys.exit(0)


if __name__ == "__main__":
    main()
