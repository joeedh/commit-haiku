#!/usr/bin/env python3
"""Submit a prompt to Google's Veo via the Gemini API, poll, download the MP4.

Usage:
    python generate_video.py --prompt "..." [--model ...] [--output ...]

API key resolution order (first hit wins):
    1. --api-key <KEY>
    2. --api-key-file <PATH>
    3. $GEMINI_API_KEY
    4. $GOOGLE_API_KEY
    5. ~/.claude/skills/commit-haiku/.api-key
    6. ./gemini.txt  (legacy)
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_BASE = "https://generativelanguage.googleapis.com/v1beta"


USER_KEY_FILE = Path.home() / ".claude" / "skills" / "commit-haiku" / ".api-key"
LEGACY_KEY_FILE = Path("./gemini.txt")


def _read_key_file(path: Path, *, required: bool) -> str:
    if not path.exists():
        if required:
            sys.exit(f"error: --api-key-file not found: {path}")
        return ""
    key = path.read_text(encoding="utf-8").strip()
    if not key and required:
        sys.exit(f"error: --api-key-file is empty: {path}")
    return key


def _missing_key_message() -> str:
    return (
        "error: no Gemini API key found. Checked, in order:\n"
        "  1. --api-key flag\n"
        "  2. --api-key-file flag\n"
        "  3. $GEMINI_API_KEY env var\n"
        "  4. $GOOGLE_API_KEY env var\n"
        f"  5. {USER_KEY_FILE}\n"
        f"  6. {LEGACY_KEY_FILE.resolve()}  (legacy)\n"
        "\n"
        "Get a key at https://aistudio.google.com/apikey, then set it once with EITHER:\n"
        "\n"
        "  # PowerShell — persisted env var (recommended)\n"
        '  [Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "<KEY>", "User")\n'
        "\n"
        "  # OR user-level file (no shell restart needed)\n"
        f'  New-Item -ItemType Directory -Force "{USER_KEY_FILE.parent}" | Out-Null\n'
        f'  "<KEY>" | Out-File -Encoding ascii -NoNewline "{USER_KEY_FILE}"'
    )


def resolve_api_key(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key.strip()
    if args.api_key_file:
        return _read_key_file(Path(args.api_key_file), required=True)
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.environ.get(var, "").strip()
        if v:
            return v
    for path in (USER_KEY_FILE, LEGACY_KEY_FILE):
        key = _read_key_file(path, required=False)
        if key:
            return key
    sys.exit(_missing_key_message())


def http_json(method: str, url: str, api_key: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"error: {method} {url} -> HTTP {e.code}\n{detail}")


def submit(prompt: str, model: str, aspect_ratio: str, api_key: str) -> str:
    url = f"{API_BASE}/models/{model}:predictLongRunning"
    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {"aspectRatio": aspect_ratio},
    }
    op = http_json("POST", url, api_key, body)
    name = op.get("name")
    if not name:
        sys.exit(f"error: no operation name in response:\n{json.dumps(op, indent=2)}")
    return name


def poll_until_done(op_name: str, api_key: str, poll_seconds: int, timeout_seconds: int) -> dict:
    url = f"{API_BASE}/{op_name}"
    start = time.time()
    while True:
        elapsed = int(time.time() - start)
        if elapsed > timeout_seconds:
            sys.exit(f"error: timed out after {elapsed}s waiting for {op_name}")
        op = http_json("GET", url, api_key)
        if op.get("done"):
            print(f"[t={elapsed}s] done", flush=True)
            return op
        print(f"[t={elapsed}s] still generating...", flush=True)
        time.sleep(poll_seconds)


def extract_video_uri(op: dict) -> str:
    if "error" in op:
        sys.exit(f"error: Veo returned an error:\n{json.dumps(op['error'], indent=2)}")
    resp = op.get("response", {})
    # Veo nests the result under different keys across model revs. Walk known shapes.
    candidates = [
        resp.get("generateVideoResponse", {}).get("generatedSamples"),
        resp.get("generateVideoResponse", {}).get("generated_samples"),
        resp.get("generatedSamples"),
        resp.get("generated_samples"),
        resp.get("videos"),
    ]
    samples = next((c for c in candidates if c), None)
    if not samples:
        sys.exit(f"error: no video samples in response:\n{json.dumps(op, indent=2)}")
    sample = samples[0]
    video = sample.get("video") or sample
    uri = video.get("uri") or video.get("videoUri") or video.get("file_uri")
    if not uri:
        sys.exit(f"error: no URI on sample:\n{json.dumps(sample, indent=2)}")
    return uri


def download(uri: str, api_key: str, out_path: Path) -> None:
    # The Files API returns absolute URLs. Append ?alt=media if not already present.
    parsed = urllib.parse.urlparse(uri)
    q = urllib.parse.parse_qs(parsed.query)
    if "alt" not in q:
        q["alt"] = ["media"]
    new_query = urllib.parse.urlencode({k: v[0] for k, v in q.items()})
    full = urllib.parse.urlunparse(parsed._replace(query=new_query))

    req = urllib.request.Request(full, headers={"x-goog-api-key": api_key})
    try:
        with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        sys.exit(f"error: download {full} -> HTTP {e.code}\n{detail}")


def main() -> None:
    p = argparse.ArgumentParser(description="Generate a video with Veo via the Gemini API.")
    p.add_argument("--prompt", required=True, help="Full Veo prompt (may contain quoted dialogue).")
    p.add_argument("--model", default="veo-3.0-fast-generate-001", help="Veo model ID.")
    p.add_argument("--output", default="./haiku.mp4", help="Where to write the MP4.")
    p.add_argument("--api-key", default=None, help="Gemini API key (overrides all other sources).")
    p.add_argument("--api-key-file", default=None, help="File containing the Gemini API key (overrides env vars and default file locations).")
    p.add_argument("--poll-seconds", type=int, default=10)
    p.add_argument("--timeout-seconds", type=int, default=900)
    p.add_argument("--aspect-ratio", default="16:9")
    args = p.parse_args()

    api_key = resolve_api_key(args)
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"submitting to {args.model} (aspect {args.aspect_ratio})...", flush=True)
    op_name = submit(args.prompt, args.model, args.aspect_ratio, api_key)
    print(f"operation: {op_name}", flush=True)

    op = poll_until_done(op_name, api_key, args.poll_seconds, args.timeout_seconds)
    uri = extract_video_uri(op)
    print(f"downloading {uri} -> {out_path}", flush=True)
    download(uri, api_key, out_path)
    print(f"saved: {out_path}", flush=True)


if __name__ == "__main__":
    main()
