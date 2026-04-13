#!/usr/bin/env python3
import argparse
import csv
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import matplotlib.pyplot as plt
except Exception as exc:
    raise SystemExit(
        "matplotlib is required. Install with: pip install matplotlib\n"
        f"import error: {exc}"
    )


def percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    idx = (len(values) - 1) * p
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[lo]
    return values[lo] + (values[hi] - values[lo]) * (idx - lo)


def normalize_field_name(name: str) -> str:
    s = (name or "").strip().lower().replace("-", "_")
    s = s.replace(" ", "_")
    return "".join(ch for ch in s if ch.isalnum() or ch == "_")


def parse_float_value(raw: str) -> float:
    text = (raw or "").strip().strip('"')
    if not text:
        raise ValueError("empty number")

    # 兼容 0,123（小数逗号）与 1,234.56（千位分隔）两种格式。
    if text.count(",") == 1 and text.count(".") == 0:
        text = text.replace(",", ".")
    else:
        text = text.replace(",", "")

    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if not match:
        raise ValueError(f"invalid number: {raw}")
    return float(match.group(0))


def read_text_with_bom_support(path: Path) -> str:
    if not path.exists():
        return ""

    try:
        data = path.read_bytes()
    except Exception:
        return ""

    if data.startswith(b"\xff\xfe"):
        return data.decode("utf-16", errors="ignore")
    if data.startswith(b"\xfe\xff"):
        return data.decode("utf-16-be", errors="ignore")
    return data.decode("utf-8", errors="ignore")


def parse_duration_from_raw_txt(raw_txt_path: Path) -> float:
    if not raw_txt_path.exists():
        return 0.0

    text = read_text_with_bom_support(raw_txt_path)
    if not text:
        return 0.0

    for line in text.splitlines():
        # hey 常见输出：Total:\t1.2345 secs
        m = re.search(r"^\s*Total(?:\s*time)?\s*:\s*([0-9][0-9.,eE+-]*)", line, re.IGNORECASE)
        if not m:
            continue
        try:
            return max(parse_float_value(m.group(1)), 0.0)
        except Exception:
            continue

    return 0.0


def parse_rps_from_raw_txt(raw_txt_path: Path) -> float:
    if not raw_txt_path.exists():
        return 0.0

    text = read_text_with_bom_support(raw_txt_path)
    if not text:
        return 0.0

    for line in text.splitlines():
        m = re.search(r"^\s*Requests\s*/\s*sec\s*:\s*([0-9][0-9.,eE+-]*)", line, re.IGNORECASE)
        if not m:
            continue
        try:
            return max(parse_float_value(m.group(1)), 0.0)
        except Exception:
            continue

    return 0.0


def parse_hey_csv(csv_path: Path) -> Tuple[List[float], List[float], Counter]:
    latencies_ms: List[float] = []
    offsets: List[float] = []
    status_counter: Counter = Counter()

    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        field_map = {normalize_field_name(k): k for k in fields}

        latency_key = (
            field_map.get("response_time")
            or field_map.get("latency")
            or (fields[0] if fields else "")
        )
        offset_key = (
            field_map.get("offset")
            or field_map.get("total")
            or field_map.get("elapsed")
            or ""
        )
        status_key = (
            field_map.get("status_code")
            or field_map.get("status")
            or ""
        )

        for row in reader:
            if not latency_key or latency_key not in row:
                continue
            try:
                lat_ms = parse_float_value(row[latency_key]) * 1000.0
                latencies_ms.append(lat_ms)
            except Exception:
                continue

            if offset_key and offset_key in row:
                try:
                    offsets.append(parse_float_value(row[offset_key]))
                except Exception:
                    offsets.append(0.0)
            else:
                offsets.append(0.0)

            if status_key and status_key in row:
                code_raw = row[status_key].strip()
                if code_raw:
                    try:
                        code = str(int(parse_float_value(code_raw)))
                    except Exception:
                        code = code_raw
                    status_counter[code] += 1

    return latencies_ms, offsets, status_counter


def summarize(
    latencies_ms: List[float],
    offsets: List[float],
    status_counter: Counter,
    duration_hint: float = 0.0,
    rps_hint: float = 0.0,
) -> Dict:
    if not latencies_ms:
        return {
            "count": 0,
            "avg_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
            "p50_ms": 0.0,
            "p90_ms": 0.0,
            "p95_ms": 0.0,
            "p99_ms": 0.0,
            "duration_s": 0.0,
            "rps": 0.0,
            "status_codes": {},
        }

    sorted_vals = sorted(latencies_ms)
    duration_s = 0.0
    if offsets:
        off_max = max(offsets)
        off_min = min(offsets)
        off_span = off_max - off_min

        if off_max > 0:
            duration_s = off_max
        elif off_span > 0:
            # 某些环境下 hey 的 offset 为负值，用跨度作为有效总时长。
            duration_s = off_span

    if duration_s <= 0 and duration_hint > 0:
        duration_s = duration_hint

    rps = rps_hint if rps_hint > 0 else ((len(latencies_ms) / duration_s) if duration_s > 0 else 0.0)

    return {
        "count": len(latencies_ms),
        "avg_ms": round(sum(latencies_ms) / len(latencies_ms), 3),
        "min_ms": round(sorted_vals[0], 3),
        "max_ms": round(sorted_vals[-1], 3),
        "p50_ms": round(percentile(sorted_vals, 0.50), 3),
        "p90_ms": round(percentile(sorted_vals, 0.90), 3),
        "p95_ms": round(percentile(sorted_vals, 0.95), 3),
        "p99_ms": round(percentile(sorted_vals, 0.99), 3),
        "duration_s": round(duration_s, 3),
        "rps": round(rps, 3),
        "status_codes": dict(sorted(status_counter.items())),
    }


def plot_latency_hist(latencies_ms: List[float], title: str, output_path: Path) -> None:
    plt.figure(figsize=(10, 5))
    bins = min(60, max(10, int(len(latencies_ms) ** 0.5)))
    plt.hist(latencies_ms, bins=bins, color="#1f77b4", alpha=0.85, edgecolor="black", linewidth=0.3)
    plt.title(f"{title} - Latency Histogram")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Count")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_latency_timeline(offsets: List[float], latencies_ms: List[float], title: str, output_path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.scatter(offsets, latencies_ms, s=8, alpha=0.5, color="#ff7f0e")
    plt.title(f"{title} - Latency Timeline")
    plt.xlabel("Offset (s)")
    plt.ylabel("Latency (ms)")
    plt.grid(alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def plot_status_codes(status_counter: Counter, title: str, output_path: Path) -> None:
    if not status_counter:
        return
    labels = list(status_counter.keys())
    values = [status_counter[k] for k in labels]

    plt.figure(figsize=(8, 5))
    plt.bar(labels, values, color="#2ca02c")
    plt.title(f"{title} - Status Codes")
    plt.xlabel("HTTP Status")
    plt.ylabel("Count")
    plt.grid(axis="y", alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def write_markdown_summary(combined: Dict[str, Dict], output_md: Path) -> None:
    lines = [
        "# Gateway Load Test Summary",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
    ]

    for name, item in combined.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(f"- requests: {item['count']}")
        lines.append(f"- avg_ms: {item['avg_ms']}")
        lines.append(f"- p50_ms: {item['p50_ms']}")
        lines.append(f"- p90_ms: {item['p90_ms']}")
        lines.append(f"- p95_ms: {item['p95_ms']}")
        lines.append(f"- p99_ms: {item['p99_ms']}")
        lines.append(f"- max_ms: {item['max_ms']}")
        lines.append(f"- duration_s: {item['duration_s']}")
        lines.append(f"- rps: {item['rps']}")
        lines.append(f"- status_codes: {json.dumps(item['status_codes'], ensure_ascii=False)}")
        lines.append("")

    output_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot hey CSV results and generate summaries")
    parser.add_argument("--input-dir", required=True, help="Directory containing *.raw.csv files")
    parser.add_argument("--output-dir", required=True, help="Directory to place charts and summary")
    parser.add_argument("--title-prefix", default="SpotTruth Gateway", help="Chart title prefix")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("*.raw.csv"))
    if not csv_files:
        raise SystemExit(f"No *.raw.csv files found in {input_dir}")

    combined_summary: Dict[str, Dict] = {}

    for csv_file in csv_files:
        scenario = csv_file.name.replace(".raw.csv", "")
        latencies_ms, offsets, status_counter = parse_hey_csv(csv_file)
        raw_txt = input_dir / f"{scenario}.raw.txt"
        duration_hint = parse_duration_from_raw_txt(raw_txt)
        rps_hint = parse_rps_from_raw_txt(raw_txt)
        summary = summarize(latencies_ms, offsets, status_counter, duration_hint=duration_hint, rps_hint=rps_hint)
        combined_summary[scenario] = summary

        summary_path = output_dir / f"{scenario}.summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

        if summary["count"] == 0:
            continue

        plot_latency_hist(
            latencies_ms,
            f"{args.title_prefix} / {scenario}",
            output_dir / f"{scenario}.latency_hist.png",
        )
        plot_latency_timeline(
            offsets,
            latencies_ms,
            f"{args.title_prefix} / {scenario}",
            output_dir / f"{scenario}.latency_timeline.png",
        )
        plot_status_codes(
            status_counter,
            f"{args.title_prefix} / {scenario}",
            output_dir / f"{scenario}.status_codes.png",
        )

    (output_dir / "combined.summary.json").write_text(
        json.dumps(combined_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_markdown_summary(combined_summary, output_dir / "combined.summary.md")

    print(f"done: charts and summary written to {output_dir}")


if __name__ == "__main__":
    main()
