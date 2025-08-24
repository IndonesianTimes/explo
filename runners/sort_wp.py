import subprocess
from pathlib import Path
from .common import ROOT, cfg, bin_path, timestamp, write_lines, alias_copy, read_lines

def sort_wordpress(input_file: Path):
    c = cfg()
    httpx = bin_path("httpx")
    ts = timestamp()
    out_dir = ROOT / c["outputs"]["out_dir"]
    tmp_dir = ROOT / c["outputs"]["tmp_dir"]
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # normalize to https://
    raw = read_lines(input_file)
    norm = []
    for s in raw:
        s = s.strip()
        if not s: continue
        if "://" not in s: s = "https://" + s
        norm.append(s)
    norm_file = tmp_dir / f"norm_{ts}.txt"
    write_lines(norm_file, norm)

    # detect via /wp-login.php and /wp-json/
    hits_file = tmp_dir / f"wp_hits_{ts}.txt"
    args_common = [
        httpx, "-l", str(norm_file), "-silent", "-follow-redirects",
        "-threads", str(c["httpx"]["threads"]), "-timeout", str(c["httpx"]["timeout"]),
        "-mc", ",".join(str(x) for x in c["httpx"]["mc"])
    ]
    # /wp-login.php
    args1 = args_common + ["-path", "/wp-login.php"]
    with open(hits_file, "ab") as fh:
        subprocess.call(args1, stdout=fh, stderr=subprocess.STDOUT)
    # /wp-json/
    args2 = args_common + ["-path", "/wp-json/"]
    with open(hits_file, "ab") as fh:
        subprocess.call(args2, stdout=fh, stderr=subprocess.STDOUT)

    # dedup + strip paths
    hits = read_lines(hits_file)
    base = []
    seen = set()
    for h in hits:
        u = h.split("/wp-login.php")[0].split("/wp-json/")[0]
        if u not in seen:
            seen.add(u)
            base.append(u)
    outwp = out_dir / "cms" / f"{ts}_wordpress.txt"
    write_lines(outwp, base)
    alias = out_dir / "cms" / "wordpress.txt"
    alias_copy(outwp, alias)
    return outwp, alias, len(base)
