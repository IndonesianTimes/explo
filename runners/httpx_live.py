from pathlib import Path
from .common import ROOT, cfg, bin_path, timestamp, write_lines, alias_copy, run_cmd, read_lines

def run_httpx_live(input_file: Path):
    c = cfg()
    httpx = bin_path("httpx")
    ts = timestamp()
    out_dir = ROOT / c["outputs"]["out_dir"]
    live_one = out_dir / "live" / f"{ts}.txt"
    httpx_jsonl = out_dir / "httpx.jsonl"

    args_base = [
        httpx, "-l", str(input_file), "-silent",
        "-follow-redirects", "-threads", str(c["httpx"]["threads"]),
        "-timeout", str(c["httpx"]["timeout"]), "-retries", str(c["httpx"]["retries"]),
        "-mc", ",".join(str(x) for x in c["httpx"]["mc"])
    ]
    # plain list
    run_cmd(args_base, stdout_file=str(live_one), append=False)
    # jsonl alias
    args_json = args_base + ["-json", "-o", str(httpx_jsonl)]
    run_cmd(args_json)

    # alias: out/live.txt
    alias_copy(live_one, out_dir / "live.txt")
    lines = read_lines(live_one)
    return live_one, httpx_jsonl, len(lines)
