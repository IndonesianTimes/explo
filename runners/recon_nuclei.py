import subprocess, threading
from pathlib import Path
from .common import ROOT, cfg, bin_path, timestamp, write_lines, read_lines, parse_nuclei_jsonl, SEV_ORDER, ensure_dirs


def recon_pipeline(input_subs: Path, job_dir: Path, base: str):
    ensure_dirs()
    c = cfg()
    tmp_dir = ROOT / c["outputs"]["tmp_dir"]
    logs_dir = ROOT / c["outputs"]["logs_dir"]
    tmp_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    from .httpx_live import run_httpx_live
    live_file, httpx_jsonl, live_count = run_httpx_live(input_subs, job_dir, base)

    shards = int(c["nuclei"]["shards"])
    live = read_lines(live_file)
    shard_paths = []
    for i in range(shards):
        p = tmp_dir / f"{timestamp()}_shard_{i}.txt"
        shard_paths.append(p)
        write_lines(p, [])
    for idx, u in enumerate(live):
        sp = shard_paths[idx % shards]
        with sp.open("a", encoding="utf-8") as fh:
            fh.write(u + "\n")

    threads = []
    for i, sp in enumerate(shard_paths):
        outj = tmp_dir / f"nuclei_shard_{i}.jsonl"
        t = threading.Thread(target=_nuclei_one, args=(sp, outj))
        t.start()
        threads.append((t, outj))
    for t, _ in threads:
        t.join()

    merged = job_dir / f"{base}.nuclei-findings.jsonl"
    with merged.open("w", encoding="utf-8") as outfh:
        for _, outj in threads:
            if outj.exists():
                outfh.write(outj.read_text(encoding="utf-8", errors="ignore"))
    human = job_dir / f"{base}.nuclei-findings.txt"
    summary = job_dir / f"{base}.summary.txt"
    _make_summaries(merged, human, summary)

    wp_live = job_dir / f"{base}.wp-live.txt"
    _derive_wp_live(live_file, wp_live)
    wp_paths = {}
    if wp_live.exists() and wp_live.stat().st_size > 0:
        wp_paths = _nuclei_wp(wp_live, job_dir, base)

    return {
        "live": live_file,
        "httpx_jsonl": httpx_jsonl,
        "findings_jsonl": merged,
        "findings_txt": human,
        "summary": summary,
        **wp_paths,
    }


def _nuclei_one(shard_file: Path, out_jsonl: Path):
    c = cfg()
    nuclei = bin_path("nuclei")
    config_yaml = str((ROOT / "nuclei-config-takeover.yaml").resolve())
    prj = (ROOT / "out" / "nuclei-project").resolve()
    args = [
        nuclei,
        "-l",
        str(shard_file),
        "-config",
        config_yaml,
        "-severity",
        ",".join(c["nuclei"]["severity"]),
        "-exclude-tags",
        ",".join(c["nuclei"]["exclude_tags"]),
        "-c",
        str(c["nuclei"]["concurrency"]),
        "-rl",
        str(c["nuclei"]["rate_limit"]),
        "-timeout",
        str(c["nuclei"]["timeout"]),
        "-retries",
        str(c["nuclei"]["retries"]),
        "-bulk-size",
        str(c["nuclei"]["bulk_size"]),
        "-project",
        "-project-path",
        str(prj),
        "-jsonl",
        "-o",
        str(out_jsonl),
        "-silent",
        "-stats",
    ]
    tags = list(c["nuclei"]["tags_base"])
    if c["nuclei"]["enable_extra_tags"]:
        tags += c["nuclei"]["tags_extra"]
    args += ["-tags", ",".join(tags)]
    if not c["nuclei"]["use_interactsh"]:
        args += ["-ni"]
    subprocess.call(args)


def _derive_wp_live(live_file: Path, wp_out: Path):
    from .common import cfg, bin_path, read_lines, write_lines

    c = cfg()
    httpx = bin_path("httpx")
    args = [
        httpx,
        "-l",
        str(live_file),
        "-silent",
        "-follow-redirects",
        "-threads",
        str(c["httpx"]["threads"]),
        "-timeout",
        str(c["httpx"]["timeout"]),
        "-mc",
        ",".join(str(x) for x in c["httpx"]["mc"]),
        "-path",
        "/wp-login.php",
    ]
    import tempfile

    tmp = Path(tempfile.mkstemp(prefix="wplive_")[1])
    with open(tmp, "wb") as fh:
        subprocess.call(args, stdout=fh, stderr=subprocess.STDOUT)
    lines = []
    for h in read_lines(tmp):
        lines.append(h.split("/wp-login.php")[0])
    write_lines(wp_out, sorted(set(lines)))
    try:
        tmp.unlink(missing_ok=True)
    except:
        pass


def _nuclei_wp(wp_list: Path, job_dir: Path, base: str):
    tmp_out = job_dir / f"{base}.nuclei-findings-wp.jsonl"
    _nuclei_one(wp_list, tmp_out)
    human = job_dir / f"{base}.nuclei-findings-wp.txt"
    summary = job_dir / f"{base}.summary-wp.txt"
    _make_summaries(tmp_out, human, summary)
    return {
        "wp_live": wp_list,
        "wp_jsonl": tmp_out,
        "wp_txt": human,
        "wp_summary": summary,
    }


def _make_summaries(jsonl_path: Path, human_txt: Path, summary_txt: Path):
    if not jsonl_path.exists() or jsonl_path.stat().st_size == 0:
        human_txt.write_text("", encoding="utf-8")
        summary_txt.write_text("No findings.\n", encoding="utf-8")
        return
    findings = []
    counts = {}
    for obj in parse_nuclei_jsonl(jsonl_path):
        info = obj.get("info") or {}
        sev = (info.get("severity") or "unknown").lower()
        tid = obj.get("template-id", "")
        host = obj.get("host") or obj.get("matched-at") or obj.get("matched") or ""
        findings.append((sev, tid, host))
        counts[sev] = counts.get(sev, 0) + 1

    lines = []
    for sev, tid, host in sorted(findings, key=lambda x: (SEV_ORDER.get(x[0], 9), x[1], x[2]))[:1000]:
        lines.append(f"[{sev.upper():8}] {tid:40} {host}")
    human_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    from collections import Counter

    pair = Counter((sev, tid) for sev, tid, _ in findings)
    top = pair.most_common(30)
    s = []
    s.append("Totals:")
    for k in ["critical", "high", "medium", "low", "info"]:
        if k in counts:
            s.append(f"  {k}: {counts[k]}")
    s.append("\nTop 30 (severity|template-id|count):")
    for (sev, tid), cnt in top:
        s.append(f"  {sev}|{tid}|{cnt}")
    summary_txt.write_text("\n".join(s) + "\n", encoding="utf-8")

