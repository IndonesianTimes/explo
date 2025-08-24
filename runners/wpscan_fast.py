import os, re, csv, tempfile, subprocess
from pathlib import Path
from .common import ROOT, cfg, bin_path, timestamp, write_lines, read_lines, url_host

def _ensure_db(log_file: Path):
    # first time update; fallback with TLS disable if needed
    with open(log_file, "ab") as fh:
        rc = subprocess.call(["ruby","-S","wpscan","--update"], stdout=fh, stderr=subprocess.STDOUT)
        if rc != 0:
            subprocess.call(["ruby","-S","wpscan","--update","--disable-tls-checks"], stdout=fh, stderr=subprocess.STDOUT)

def _normalize_via_httpx(lines):
    httpx = bin_path("httpx")
    tmp_in = Path(tempfile.mkstemp(prefix="wps_")[1])
    write_lines(tmp_in, lines)
    tmp_out = Path(str(tmp_in)+".live.txt")
    subprocess.call([httpx,"-l",str(tmp_in),"-silent","-follow-redirects","-threads","60","-timeout","8"], stdout=open(tmp_out,"wb"))
    out_lines = read_lines(tmp_out)
    try:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)
    except: pass
    return out_lines

def _load_sources(source_file: Path):
    if source_file.suffix.lower()==".csv":
        import csv, re
        urls=[]
        for row in csv.reader(source_file.open("r",encoding="utf-8",errors="ignore")):
            joined=",".join(row)
            m=re.search(r"(https?://[^\s,;]+)", joined, re.I)
            if m: urls.append(m.group(1))
        return urls
    else:
        return read_lines(source_file)

def wpscan_fast(source_file: Path):
    c = cfg()
    out_dir = ROOT / c["outputs"]["out_dir"]
    logs = ROOT / c["outputs"]["logs_dir"]
    logs.mkdir(parents=True, exist_ok=True)
    logf = logs / "wp_scan.log"
    _ensure_db(logf)

    # load + normalize
    raw = _load_sources(source_file)
    norm=[]
    seen=set()
    for s in raw:
        s=s.strip()
        if not s: continue
        if "://" not in s: s="https://"+s
        if s not in seen:
            seen.add(s); norm.append(s)

    # verify via httpx
    norm = _normalize_via_httpx(norm)

    ts = timestamp()
    for url in norm:
        host = url_host(url)
        outj = out_dir / "wpscan" / "raw" / f"{ts}_{host}.json"
        cmd = [
            "ruby","-S","wpscan",
            "--url", url,
            "--no-update","--force","--random-user-agent"
        ]
        if c["wp"]["tls_disable_checks"]:
            cmd.append("--disable-tls-checks")
        cmd += [
            "--plugins-detection","passive",
            "--themes-detection","passive",
            "--enumerate","vp,vt,tt,cb",
            "--max-threads", str(c["wp"]["wpscan_max_threads"]),
            "--request-timeout", str(c["wp"]["request_timeout"]),
            "--connect-timeout", str(c["wp"]["connect_timeout"]),
            "--format","json",
            "--output", str(outj)
        ]
        with open(logf,"ab") as fh:
            subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
