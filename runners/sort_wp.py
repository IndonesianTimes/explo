import subprocess
from pathlib import Path
from .common import ROOT, cfg, bin_path, write_lines, read_lines


def sort_wordpress(input_file: Path, job_dir: Path, base: str):
    c = cfg()
    httpx = bin_path("httpx")
    tmp_dir = ROOT / c["outputs"]["tmp_dir"]
    tmp_dir.mkdir(parents=True, exist_ok=True)

    raw = read_lines(input_file)
    norm = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        if "://" not in s:
            s = "https://" + s
        norm.append(s)
    norm_file = tmp_dir / f"norm_{base}.txt"
    write_lines(norm_file, norm)

    hits_file = tmp_dir / f"wp_hits_{base}.txt"
    args_common = [
        httpx,
        "-l",
        str(norm_file),
        "-silent",
        "-follow-redirects",
        "-threads",
        str(c["httpx"]["threads"]),
        "-timeout",
        str(c["httpx"]["timeout"]),
        "-mc",
        ",".join(str(x) for x in c["httpx"]["mc"]),
    ]
    args1 = args_common + ["-path", "/wp-login.php"]
    with open(hits_file, "ab") as fh:
        subprocess.call(args1, stdout=fh, stderr=subprocess.STDOUT)
    args2 = args_common + ["-path", "/wp-json/"]
    with open(hits_file, "ab") as fh:
        subprocess.call(args2, stdout=fh, stderr=subprocess.STDOUT)

    hits = read_lines(hits_file)
    base_urls = []
    seen = set()
    for h in hits:
        u = h.split("/wp-login.php")[0].split("/wp-json/")[0]
        if u not in seen:
            seen.add(u)
            base_urls.append(u)
    out_file = job_dir / f"{base}.cms_wordpress.txt"
    write_lines(out_file, base_urls)
    return out_file
