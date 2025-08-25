from pathlib import Path
from .common import ROOT, cfg, bin_path, run_cmd, read_lines


def run_httpx_live(input_file: Path, job_dir: Path, base: str):
    c = cfg()
    httpx = bin_path("httpx")
    live_one = job_dir / f"{base}.live.txt"
    httpx_jsonl = job_dir / f"{base}.httpx.jsonl"

    args_base = [
        httpx,
        "-l",
        str(input_file),
        "-silent",
        "-follow-redirects",
        "-threads",
        str(c["httpx"]["threads"]),
        "-timeout",
        str(c["httpx"]["timeout"]),
        "-retries",
        str(c["httpx"]["retries"]),
        "-mc",
        ",".join(str(x) for x in c["httpx"]["mc"]),
    ]
    run_cmd(args_base, stdout_file=str(live_one), append=False)
    args_json = args_base + ["-json", "-o", str(httpx_jsonl)]
    run_cmd(args_json)

    lines = read_lines(live_one)
    return live_one, httpx_jsonl, len(lines)
