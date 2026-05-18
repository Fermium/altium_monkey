"""Probe the public Altium Viewer API to map designType / fileType / modules.

The public viewer at https://viewer.altium.com/ accepts a ZIP of Altium project
files and converts them for in-browser viewing. The conversion side-effect we
care about is the metadata Altium returns: which integer ``designType`` it
assigns, what ``fileType`` string it reports, and which renderer ``modules``
it activates. Uploading a curated corpus of single-file and full-project ZIPs
lets us recover Altium's own classification enum without parsing any binary.

Wire protocol, reverse-engineered from the public viewer SPA:

    POST https://viewer.altium.com/api/widget/set
        Header:  X-AUTH: anonymous
        Body (multipart/form-data):
            Files                (the ZIP, one or more allowed)
            Host                 (any string)
            Outputs              "None"
            Origin               (any string)
            HideSrc              "true"
            SourceType           "Fabrication"
            AppTypeId            "1"
            SrcStoredTemporarily "true"
        Returns JSON: designId, status="Progress", ...

    POST https://viewer.altium.com/api/widget/status/<designId>
        Header:  X-AUTH: anonymous
        Returns JSON: status="Complete"|..., designType, fileType, modules,
                      extendModulesData, faultCode, ...

This tool is read-only with respect to local files. It DOES upload sample
project files to Altium's public viewer service; uploads are marked
``SrcStoredTemporarily=true`` so Altium discards them after viewing.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = REPO_ROOT / "examples"

UPLOAD_URL = "https://viewer.altium.com/api/widget/set"
STATUS_URL = "https://viewer.altium.com/api/widget/status/{design_id}"
USER_AGENT = "altium-monkey-viewer-probe/0.1 (+research)"
POLL_INTERVAL_S = 2.0
POLL_TIMEOUT_S = 180.0
# After we see PartialComplete, the viewer's background steps usually
# advance to Complete within a few seconds. Poll a few more times to
# capture the terminal state for our records, but don't block forever.
POST_PARTIAL_EXTRA_POLLS = 6
INTER_PROBE_DELAY_S = 1.5


@dataclass
class Probe:
    """One named probe target."""

    name: str
    description: str
    # Either ``file`` (a single file to wrap in a zip at its basename) or
    # ``directory`` (whole tree zipped at root).
    file: Path | None = None
    directory: Path | None = None
    # If True, send a real zip of the file/dir. If False, send the raw file
    # bytes with .zip filename (lets us probe how Altium handles non-zip
    # payloads).
    wrap_zip: bool = True


@dataclass
class ProbeResult:
    name: str
    bytes_sent: int
    upload_http: int
    upload_json: dict | None = None
    status_http: int | None = None
    status_json: dict | None = None
    error: str | None = None
    elapsed_s: float = 0.0
    poll_count: int = 0


def build_corpus() -> list[Probe]:
    """Curated corpus that should probe every distinct file type / shape."""

    A = EXAMPLES / "assets"
    PRJ = A / "projects"

    return [
        Probe(
            name="lone_schdoc_blank",
            description="A blank input SchDoc (smallest valid schematic)",
            file=EXAMPLES / "schdoc_add_note" / "input" / "blank.SchDoc",
        ),
        Probe(
            name="lone_schdoc_real",
            description="A large real-world schematic sheet",
            file=PRJ / "loz-old-man" / "Microprocessor1.SchDoc",
        ),
        Probe(
            name="lone_pcbdoc",
            description="A real-world PCB document",
            file=PRJ / "m2_emmc" / "m2_emmc.PcbDoc",
        ),
        Probe(
            name="lone_schlib",
            description="A real-world schematic library",
            file=A / "schlib" / "SN74AHCT1G125DBVR.SchLib",
        ),
        Probe(
            name="lone_pcblib",
            description="A real-world PCB library",
            file=A / "pcblib" / "SB0037A.PcbLib",
        ),
        Probe(
            name="lone_intlib",
            description="A real-world integrated library",
            file=PRJ / "rt_super_c1" / "RT_SUPER_C1.IntLib",
        ),
        Probe(
            name="lone_harness",
            description="A standalone Harness file",
            file=PRJ / "hydroscope" / "CPU.Harness",
        ),
        Probe(
            name="lone_outjob",
            description="A standalone OutJob file",
            file=PRJ / "rt_super_c1" / "reference_gen.OutJob",
        ),
        Probe(
            name="lone_prjpcb_xml",
            description="A PrjPcb (XML-ish project text) by itself, no referenced files",
            file=PRJ / "m2_emmc" / "m2_emmc.PrjPcb",
        ),
        Probe(
            name="project_m2_emmc",
            description="Small complete project: PrjPcb + SchDoc + PcbDoc",
            directory=PRJ / "m2_emmc",
        ),
        Probe(
            name="project_simple_hierarchical",
            description="Hierarchical project: PrjPCB + parent/child SchDocs + SchLib (no PCB)",
            directory=PRJ / "simple_hierchical",
        ),
        Probe(
            name="project_rt_super_c1",
            description="Full project: PrjPcb + SchDoc + PCBdoc + IntLib + OutJob",
            directory=PRJ / "rt_super_c1",
        ),
        Probe(
            name="non_altium_text",
            description="Plain text file in a zip (negative control)",
            file=REPO_ROOT / "README.md",
        ),
    ]


def make_zip_bytes(probe: Probe) -> bytes:
    """Produce the bytes to upload for one probe.

    Files are placed at the root of the zip with their basename. Directories
    are zipped recursively, preserving their relative structure.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if probe.file is not None:
            if not probe.file.exists():
                raise FileNotFoundError(probe.file)
            zf.write(probe.file, arcname=probe.file.name)
        elif probe.directory is not None:
            root = probe.directory
            if not root.exists():
                raise FileNotFoundError(root)
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=str(path.relative_to(root)))
        else:
            raise ValueError(f"probe {probe.name} has neither file nor directory")
    return buf.getvalue()


def build_multipart(zip_bytes: bytes, zip_filename: str) -> tuple[bytes, str]:
    """Build a multipart/form-data body matching the viewer SPA's upload."""

    boundary = "----altiumMonkeyProbe" + uuid.uuid4().hex
    fields = [
        ("Host", "www.altium.com"),
        ("Outputs", "None"),
        ("Origin", "https://www.altium.com"),
        ("HideSrc", "true"),
        ("SourceType", "Fabrication"),
        ("AppTypeId", "1"),
        ("SrcStoredTemporarily", "true"),
    ]
    chunks: list[bytes] = []
    for key, val in fields:
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        )
        chunks.append(val.encode())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(
        f'Content-Disposition: form-data; name="Files"; filename="{zip_filename}"\r\n'.encode()
    )
    chunks.append(b"Content-Type: application/zip\r\n\r\n")
    chunks.append(zip_bytes)
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    body = b"".join(chunks)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def http_post(url: str, body: bytes | None, headers: dict[str, str], timeout: float):
    req = urllib.request.Request(url, data=body if body is not None else b"", method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def upload(zip_bytes: bytes, name: str) -> tuple[int, dict | None]:
    body, content_type = build_multipart(zip_bytes, f"{name}.zip")
    code, raw = http_post(
        UPLOAD_URL,
        body,
        headers={
            "X-AUTH": "anonymous",
            "User-Agent": USER_AGENT,
            "Content-Type": content_type,
            "Origin": "https://www.altium.com",
            "Referer": "https://www.altium.com/viewer/",
        },
        timeout=60.0,
    )
    try:
        data = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        data = None
    return code, data


def _status_once(design_id: str) -> tuple[int, dict | None]:
    code, raw = http_post(
        STATUS_URL.format(design_id=design_id),
        None,
        headers={
            "X-AUTH": "anonymous",
            "User-Agent": USER_AGENT,
            "Origin": "https://www.altium.com",
            "Referer": "https://www.altium.com/viewer/",
        },
        timeout=30.0,
    )
    try:
        return code, (json.loads(raw) if raw else None)
    except json.JSONDecodeError:
        return code, None


def poll_status(design_id: str) -> tuple[int, dict | None, int]:
    """Poll until status leaves ``Progress``, then a few more times to try
    to capture the eventual ``Complete``. Returns (http, json, count).

    Terminal states observed from the public viewer:
        Progress         - background conversion in flight
        PartialComplete  - renderable; final post-processing still running
        Complete         - everything finished
        Error            - rejected (see ``faultCode`` and ``details``)
    """
    deadline = time.monotonic() + POLL_TIMEOUT_S
    n = 0
    last_code = 0
    last_json: dict | None = None
    while time.monotonic() < deadline:
        last_code, last_json = _status_once(design_id)
        n += 1
        status = (last_json or {}).get("status")
        if status and status != "Progress":
            break
        time.sleep(POLL_INTERVAL_S)
    # Optionally try to advance PartialComplete -> Complete.
    for _ in range(POST_PARTIAL_EXTRA_POLLS):
        if (last_json or {}).get("status") != "PartialComplete":
            break
        time.sleep(POLL_INTERVAL_S)
        last_code, last_json = _status_once(design_id)
        n += 1
    return last_code, last_json, n


def run_probe(probe: Probe) -> ProbeResult:
    t0 = time.monotonic()
    res = ProbeResult(name=probe.name, bytes_sent=0, upload_http=0)
    try:
        zip_bytes = make_zip_bytes(probe)
        res.bytes_sent = len(zip_bytes)
        code, data = upload(zip_bytes, probe.name)
        res.upload_http = code
        res.upload_json = data
        if code != 200 or not data:
            res.error = f"upload returned http {code}"
            return res
        design_id = data.get("designId")
        if not design_id:
            res.error = "upload response missing designId"
            return res
        s_code, s_data, n = poll_status(design_id)
        res.status_http = s_code
        res.status_json = s_data
        res.poll_count = n
        if (s_data or {}).get("status") == "Progress":
            res.error = "polling timed out (still Progress)"
    except FileNotFoundError as e:
        res.error = f"missing source: {e}"
    except (urllib.error.URLError, TimeoutError) as e:
        res.error = f"network error: {e}"
    finally:
        res.elapsed_s = time.monotonic() - t0
    return res


def _short_detail(d: dict) -> str:
    """Pick a short Altium-side diagnostic if present (truncated)."""
    text = d.get("details") or d.get("message") or ""
    text = " ".join(text.split())
    if len(text) > 80:
        text = text[:77] + "..."
    return text


def summarize(results: list[ProbeResult]) -> str:
    lines: list[str] = []
    lines.append(
        "| probe | bytes | http | status | designType | fileType | faultCode | polls | altium detail / error |"
    )
    lines.append("|---|---:|---:|---|---:|---|---:|---:|---|")
    for r in results:
        d = r.status_json or r.upload_json or {}
        status = d.get("status", "")
        design_type = d.get("designType", "")
        file_type = d.get("fileType", "")
        fault = d.get("faultCode", "")
        detail = r.error or _short_detail(d)
        lines.append(
            f"| {r.name} | {r.bytes_sent} | {r.upload_http} | {status} | "
            f"{design_type} | {file_type} | {fault} | {r.poll_count} | {detail} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--list", action="store_true", help="list corpus and exit")
    p.add_argument(
        "--only",
        action="append",
        default=[],
        help="probe name to run (repeatable); default = all",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "tools" / "altium_viewer_probe_out",
        help="output directory for raw responses and summary",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="show what would be uploaded without making any network calls",
    )
    args = p.parse_args(argv)

    corpus = build_corpus()
    if args.only:
        wanted = set(args.only)
        corpus = [c for c in corpus if c.name in wanted]
        missing = wanted - {c.name for c in corpus}
        if missing:
            print(f"unknown probe(s): {sorted(missing)}", file=sys.stderr)
            return 2

    if args.list:
        for c in corpus:
            target = c.file or c.directory
            print(f"{c.name:32s} {target}")
            print(f"{'':32s}   {c.description}")
        return 0

    if args.dry_run:
        for c in corpus:
            target = c.file or c.directory
            exists = "ok" if target and target.exists() else "MISSING"
            print(f"[{exists}] {c.name}: {target}")
        return 0

    run_dir = args.out / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results: list[ProbeResult] = []
    for i, probe in enumerate(corpus):
        print(f"[{i+1}/{len(corpus)}] {probe.name} ...", flush=True)
        res = run_probe(probe)
        results.append(res)
        d = res.status_json or res.upload_json or {}
        print(
            f"    -> http={res.upload_http} status={d.get('status','?')} "
            f"designType={d.get('designType','?')} fileType={d.get('fileType','?')} "
            f"elapsed={res.elapsed_s:.1f}s polls={res.poll_count}"
            + (f"  err={res.error}" if res.error else "")
        )
        (raw_dir / f"{probe.name}.json").write_text(
            json.dumps(
                {
                    "name": probe.name,
                    "bytes_sent": res.bytes_sent,
                    "upload_http": res.upload_http,
                    "upload_json": res.upload_json,
                    "status_http": res.status_http,
                    "status_json": res.status_json,
                    "error": res.error,
                    "elapsed_s": res.elapsed_s,
                    "poll_count": res.poll_count,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        if i < len(corpus) - 1:
            time.sleep(INTER_PROBE_DELAY_S)

    summary = summarize(results)
    print()
    print(summary)
    (run_dir / "summary.md").write_text(summary + "\n", encoding="utf-8")
    print()
    print(f"raw responses + summary written under: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
