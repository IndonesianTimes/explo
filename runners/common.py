import os, sys, json, re, csv, shutil, subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "defaults.yaml"

def load_yaml(path: Path):
    # Minimal YAML loader (no pyyaml): nested dicts + inline lists [a,b,c]
    data = {}
    cur = data
    stack = [(-1, data)]
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip())
            line = raw.strip()
            while stack and indent <= stack[-1][0]:
                stack.pop()
                cur = stack[-1][1]
            if line.endswith(":"):
                key = line[:-1]
                cur[key] = {}
                stack.append((indent, cur[key]))
                cur = cur[key]
            elif ": [" in line and line.endswith("]"):
                k, v = line.split(": [",1)
                v = v[:-1]
                cur[k] = [cast_scalar(x.strip()) for x in v.split(",") if x.strip()]
            elif ": " in line:
                k, v = line.split(": ",1)
                cur[k] = cast_scalar(v.strip())
    return data

def cast_scalar(v):
    vl = v.lower()
    if vl in ("true","false"): return vl=="true"
    if re.fullmatch(r"-?\d+", v): return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v): return float(v)
    return v.strip('"').strip("'")

def cfg():
    if CONFIG.exists():
        return load_yaml(CONFIG)
    return {
        "tools_dir":"tools",
        "nuclei_templates":"tools/nuclei-templates",
        "httpx":{"threads":120,"timeout":8,"retries":1,"mc":[200,301,302,401,403]},
        "nuclei":{"shards":6,"concurrency":100,"rate_limit":600,"timeout":12,"retries":0,
                  "bulk_size":25,"use_interactsh":False,"enable_extra_tags":False,
                  "tags_base":["takeovers","file-upload"],"tags_extra":["rce","cve"],
                  "exclude_tags":["code"],"severity":["critical","high"]},
        "wp":{"wpscan_max_threads":10,"request_timeout":12,"connect_timeout":5,"tls_disable_checks":True},
        "outputs":{"out_dir":"out","logs_dir":"out/logs","tmp_dir":"tmp"},
        "routes":{
            "input":{
                "domain_dir":"domain",
                "wordpress_dir":"wordpress",
                "subs_fallbacks":["subs.txt","output/subs.txt","out/subs.txt"]
            },
            "output":{
                "job_dir":"out/jobs/current"
            }
        },
        "naming":{"suggest_timestamp":True},
        "persist":{"remember_last":True,"file":"config/last_routes.json"},
    }

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def ensure_dirs():
    c = cfg()
    paths = [
        ROOT / c["outputs"]["out_dir"],
        ROOT / c["outputs"]["logs_dir"],
        ROOT / c["outputs"]["tmp_dir"],
        ROOT / c["routes"]["input"]["domain_dir"],
        ROOT / c["routes"]["input"]["wordpress_dir"],
        ROOT / c["routes"]["output"]["job_dir"],
        ROOT / "out" / "nuclei-project",
    ]
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)

def sanitize_base(name: str) -> str:
    name = name.replace(" ", "_")
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)

def exe_name(base):
    return base + ".exe" if os.name == "nt" else base

def bin_path(tool):
    td = ROOT / cfg()["tools_dir"]
    candidates = [td/exe_name(tool), td/tool]
    for p in candidates:
        if p.exists():
            return str(p)
    return tool  # fallback to PATH

def run_cmd(args, stdout_file=None, append=False, cwd=None):
    if stdout_file:
        mode = "ab" if append else "wb"
        with open(stdout_file, mode) as fh:
            proc = subprocess.Popen(args, stdout=fh, stderr=subprocess.STDOUT, cwd=cwd)
            return proc.wait()
    else:
        return subprocess.call(args, cwd=cwd)

def write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def read_lines(path: Path):
    return [x.strip() for x in path.read_text(encoding="utf-8", errors="ignore").splitlines() if x.strip()]

def write_lines(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

def normalize_url(s: str) -> str:
    s = s.strip()
    if not s: return s
    if "://" not in s:
        s = "https://" + s
    return s

def alias_copy(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

def url_host(url: str) -> str:
    m = re.match(r"^[a-z]+://([^/]+)", url, re.I)
    return m.group(1) if m else url

SEV_ORDER = {"critical":0,"high":1,"medium":2,"low":3,"info":4,"unknown":9}

def parse_nuclei_jsonl(path: Path):
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line=line.strip()
        if not line: continue
        try:
            obj=json.loads(line)
            yield obj
        except:
            continue
