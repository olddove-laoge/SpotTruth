#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Dict, Tuple


def load_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_status_distribution(status_codes: Dict[str, int]) -> Tuple[int, int, float]:
    total = 0
    success = 0
    for code, cnt in status_codes.items():
        n = int(cnt)
        total += n
        if str(code).startswith("2"):
            success += n
    rate = (success / total) if total > 0 else 0.0
    return total, success, rate


def level_from_metrics(success_rate: float, p95_ms: float) -> str:
    if success_rate >= 0.995 and p95_ms <= 30:
        return "A"
    if success_rate >= 0.99 and p95_ms <= 80:
        return "B"
    if success_rate >= 0.97 and p95_ms <= 150:
        return "C"
    return "D"


def calc_metric_delta(before: Dict, after: Dict, key: str) -> int:
    try:
        return int(after.get(key, 0)) - int(before.get(key, 0))
    except Exception:
        return 0


def render_report(summary: Dict[str, Dict], charts_dir: Path, metrics_before: Dict, metrics_after: Dict, title: str) -> str:
    scenarios = []
    for name, item in summary.items():
        status_codes = item.get("status_codes", {}) or {}
        total, success, success_rate = parse_status_distribution(status_codes)
        p95 = float(item.get("p95_ms", 0) or 0)
        p99 = float(item.get("p99_ms", 0) or 0)
        avg = float(item.get("avg_ms", 0) or 0)
        rps = float(item.get("rps", 0) or 0)
        level = level_from_metrics(success_rate, p95)

        scenarios.append(
            {
                "name": name,
                "count": int(item.get("count", 0) or 0),
                "avg_ms": avg,
                "p95_ms": p95,
                "p99_ms": p99,
                "rps": rps,
                "status_codes": status_codes,
                "success_rate": success_rate,
                "level": level,
            }
        )

    scenarios.sort(key=lambda x: x["name"])

    total_requests = sum(x["count"] for x in scenarios)
    avg_success_rate = (sum(x["success_rate"] for x in scenarios) / len(scenarios)) if scenarios else 0.0
    best_rps = max(scenarios, key=lambda x: x["rps"]) if scenarios else None
    worst_p99 = max(scenarios, key=lambda x: x["p99_ms"]) if scenarios else None

    req_delta = calc_metric_delta(metrics_before, metrics_after, "requests_total")
    rejected_delta = calc_metric_delta(metrics_before, metrics_after, "limiter_rejected_total")
    degraded_delta = calc_metric_delta(metrics_before, metrics_after, "circuit_degraded_total")
    status5xx_delta = calc_metric_delta(metrics_before, metrics_after, "status_5xx_total")

    overall = []
    if avg_success_rate >= 0.99:
        overall.append("压测阶段整体成功率高，网关稳定性满足比赛演示要求。")
    else:
        overall.append("压测阶段存在明显失败请求，建议先排查上游可用性与鉴权参数。")

    if degraded_delta > 0:
        overall.append("观测到熔断降级计数上升，说明网关保护机制已生效。")
    else:
        overall.append("未观测到熔断降级增量，本轮压测主要体现基础吞吐与延迟表现。")

    if rejected_delta > 0:
        overall.append("限流命中计数上升，说明高并发下已触发保护阈值。")
    else:
        overall.append("未观测到限流命中增量，当前压测参数仍处于可承受区间。")

    scenario_cards = []
    for s in scenarios:
        scenario = escape(s["name"])
        img_hist = f"charts/{scenario}.latency_hist.png"
        img_timeline = f"charts/{scenario}.latency_timeline.png"
        img_status = f"charts/{scenario}.status_codes.png"

        status_text = escape(json.dumps(s["status_codes"], ensure_ascii=False))

        card = f"""
        <section class=\"card\">
          <div class=\"card-head\">
            <h3>{scenario}</h3>
            <span class=\"badge level-{s['level']}\">等级 {s['level']}</span>
          </div>
          <div class=\"metrics\">
            <div><span>请求数</span><strong>{s['count']}</strong></div>
            <div><span>平均延迟</span><strong>{s['avg_ms']:.3f} ms</strong></div>
            <div><span>P95</span><strong>{s['p95_ms']:.3f} ms</strong></div>
            <div><span>P99</span><strong>{s['p99_ms']:.3f} ms</strong></div>
            <div><span>吞吐</span><strong>{s['rps']:.3f} req/s</strong></div>
            <div><span>成功率</span><strong>{s['success_rate'] * 100:.2f}%</strong></div>
          </div>
          <p class=\"status\">状态码分布：{status_text}</p>
          <div class=\"images\">
            <figure><img src=\"{img_hist}\" alt=\"{scenario} latency hist\"><figcaption>延迟直方图</figcaption></figure>
            <figure><img src=\"{img_timeline}\" alt=\"{scenario} latency timeline\"><figcaption>延迟时序图</figcaption></figure>
            <figure><img src=\"{img_status}\" alt=\"{scenario} status codes\"><figcaption>状态码分布</figcaption></figure>
          </div>
        </section>
        """
        scenario_cards.append(card)

    best_rps_line = (
        f"最佳吞吐场景：{escape(best_rps['name'])}（{best_rps['rps']:.3f} req/s）" if best_rps else "最佳吞吐场景：无数据"
    )
    worst_p99_line = (
        f"最高 P99 场景：{escape(worst_p99['name'])}（{worst_p99['p99_ms']:.3f} ms）" if worst_p99 else "最高 P99 场景：无数据"
    )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: #e5e7eb;
      --primary: #0f766e;
      --warn: #b45309;
      --danger: #b91c1c;
      --ok: #166534;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: "PingFang SC", "Microsoft YaHei", sans-serif; background: var(--bg); color: var(--text); }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    .hero {{ background: linear-gradient(135deg, #115e59, #1d4ed8); color: #fff; padding: 20px 24px; border-radius: 14px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: 28px; }}
    .hero p {{ margin: 0; opacity: 0.92; }}
    .grid {{ margin-top: 16px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
    .kpi {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px; }}
    .kpi .label {{ color: var(--muted); font-size: 12px; }}
    .kpi .value {{ margin-top: 6px; font-size: 22px; font-weight: 700; }}
    .section {{ margin-top: 16px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 16px; }}
    .section h2 {{ margin: 0 0 10px; font-size: 18px; }}
    .section ul {{ margin: 0; padding-left: 20px; line-height: 1.8; }}
    .card {{ margin-top: 14px; border: 1px solid var(--line); border-radius: 12px; padding: 14px; background: #fff; }}
    .card-head {{ display: flex; justify-content: space-between; align-items: center; }}
    .card-head h3 {{ margin: 0; font-size: 18px; }}
    .badge {{ font-size: 12px; padding: 4px 10px; border-radius: 999px; color: #fff; }}
    .level-A {{ background: var(--ok); }}
    .level-B {{ background: var(--primary); }}
    .level-C {{ background: var(--warn); }}
    .level-D {{ background: var(--danger); }}
    .metrics {{ margin-top: 10px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }}
    .metrics div {{ border: 1px solid var(--line); border-radius: 8px; padding: 8px; }}
    .metrics span {{ display: block; font-size: 12px; color: var(--muted); }}
    .metrics strong {{ display: block; margin-top: 4px; font-size: 16px; }}
    .status {{ margin-top: 10px; color: var(--muted); font-size: 13px; }}
    .images {{ margin-top: 10px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }}
    figure {{ margin: 0; border: 1px solid var(--line); border-radius: 8px; padding: 8px; background: #fafafa; }}
    figure img {{ width: 100%; height: auto; border-radius: 6px; }}
    figcaption {{ margin-top: 6px; font-size: 12px; color: var(--muted); text-align: center; }}
    .foot {{ margin-top: 18px; color: var(--muted); font-size: 12px; text-align: right; }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: repeat(2, 1fr); }}
      .metrics {{ grid-template-columns: repeat(2, 1fr); }}
      .images {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class=\"container\">
    <header class=\"hero\">
      <h1>{escape(title)}</h1>
      <p>自动读取 combined.summary.json 生成 | 生成时间：{generated_at}</p>
    </header>

    <section class=\"grid\">
      <div class=\"kpi\"><div class=\"label\">总请求量（全部场景）</div><div class=\"value\">{total_requests}</div></div>
      <div class=\"kpi\"><div class=\"label\">平均成功率（场景均值）</div><div class=\"value\">{avg_success_rate * 100:.2f}%</div></div>
      <div class=\"kpi\"><div class=\"label\">requests_total 增量</div><div class=\"value\">{req_delta}</div></div>
      <div class=\"kpi\"><div class=\"label\">5xx 增量</div><div class=\"value\">{status5xx_delta}</div></div>
    </section>

    <section class=\"section\">
      <h2>一页结论</h2>
      <ul>
        <li>{escape(best_rps_line)}</li>
        <li>{escape(worst_p99_line)}</li>
        <li>限流命中增量：{rejected_delta}</li>
        <li>熔断降级增量：{degraded_delta}</li>
        {''.join(f'<li>{escape(line)}</li>' for line in overall)}
      </ul>
    </section>

    <section class=\"section\">
      <h2>场景明细</h2>
      {''.join(scenario_cards)}
    </section>

    <div class=\"foot\">数据来源：charts/combined.summary.json + metrics.before/after.json</div>
  </div>
</body>
</html>
"""
    return html


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate one-page HTML report from combined.summary.json")
    parser.add_argument("--summary-json", required=True, help="Path to charts/combined.summary.json")
    parser.add_argument("--charts-dir", required=True, help="Directory that contains scenario chart png files")
    parser.add_argument("--metrics-before", required=False, default="", help="Path to metrics.before.json")
    parser.add_argument("--metrics-after", required=False, default="", help="Path to metrics.after.json")
    parser.add_argument("--output-html", required=True, help="Output html path")
    parser.add_argument("--title", required=False, default="SpotTruth 网关压测比赛汇报", help="Report title")
    args = parser.parse_args()

    summary_path = Path(args.summary_json)
    charts_dir = Path(args.charts_dir)
    output_html = Path(args.output_html)

    summary = load_json(summary_path)
    if not summary:
        raise SystemExit(f"invalid or empty summary json: {summary_path}")

    metrics_before = load_json(Path(args.metrics_before)) if args.metrics_before else {}
    metrics_after = load_json(Path(args.metrics_after)) if args.metrics_after else {}

    html = render_report(summary, charts_dir, metrics_before, metrics_after, args.title)
    output_html.write_text(html, encoding="utf-8")
    print(f"done: report page generated -> {output_html}")


if __name__ == "__main__":
    main()
