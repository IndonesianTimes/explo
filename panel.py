#!/usr/bin/env python3
import sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    ensure_dirs()
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        print("===== Recon & Vulnerability Panel (Python) =====")
        print("  [1] Sort Domain \u2192 CMS (WordPress)")
        print("  [2] Live Domain Test (httpx)")
        print("  [3] WPScan (fast, JSON)")
        print("  [4] Recon Takeover/Upload (nuclei, sharded)")
        print("  [X] Exit")
        ch = input("\nSelect option: ").strip().lower()
        if ch == "1": task_sort_wp()
        elif ch == "2": task_httpx_live()
        elif ch == "3": task_wpscan()
        elif ch == "4": task_recon()
        elif ch == "x": sys.exit(0)

def ensure_dirs():
    for p in [
        ROOT/"out","out/cms","out/live","out/wpscan/raw",
        "out/nuclei-project","out/logs","tmp","domain","wordpress"
    ]:
        Path(p).mkdir(parents=True, exist_ok=True)

def pick_file(dirpath: Path, exts=(".txt",)):
    items = [p for p in dirpath.glob("*") if p.suffix.lower() in exts]
    if not items:
        print(f"[!] No input files under {dirpath}")
        input("Enter to return...")
        return None
    print(f"\nAvailable in {dirpath}:")
    for i,p in enumerate(items,1):
        print(f"  [{i}] {p.name}")
    try:
        idx = int(input("Pick number: ").strip())
        return items[idx-1]
    except Exception:
        print("[!] Invalid selection.")
        input("Enter to return...")
        return None

def task_sort_wp():
    from runners.sort_wp import sort_wordpress
    f = pick_file(ROOT/"domain", (".txt",))
    if not f: return
    out_file, alias, count = sort_wordpress(input_file=f)
    print(f"\n[OK] WordPress targets: {count}\n -> {out_file}\n -> alias: {alias}")
    input("\nEnter to menu...")

def task_httpx_live():
    from runners.httpx_live import run_httpx_live
    f = pick_file(ROOT/"domain", (".txt",))
    if not f: return
    live_file, jsonl, count = run_httpx_live(input_file=f)
    print(f"\n[OK] Live endpoints: {count}\n -> {live_file}\n -> JSON: {jsonl}")
    input("\nEnter to menu...")

def task_wpscan():
    from runners.wpscan_fast import wpscan_fast
    src = ROOT/"out/cms/wordpress.txt"
    if not src.exists():
        alt = pick_file(ROOT/"wordpress", (".txt",".csv"))
        if not alt: return
        src = alt
    wpscan_fast(source_file=src)
    print("\n[OK] WPScan finished. Raw JSON -> out/wpscan/raw/ ; Log -> out/logs/wp_scan.log")
    input("\nEnter to menu...")

def task_recon():
    from runners.recon_nuclei import recon_pipeline
    recon_pipeline()
    print("\n[OK] Recon completed.")
    print(" -> out\\nuclei-findings.jsonl")
    print(" -> out\\nuclei-findings.txt")
    print(" -> out\\summary.txt")
    input("\nEnter to menu...")

if __name__ == "__main__":
    main()
