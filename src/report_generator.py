"""
Generates the standalone HTML diff report: metadata bar, 6-metric scorecard,
accuracy trend + result summary, category accuracy vs baseline, accuracy by
difficulty, a 3-panel trends strip (regressions/latency/tokens over the last
7 runs), a slow-drift callout, and full Failed / Regressed / Improved case
tables. Single self-contained file (inline CSS + Plotly via CDN) so it can
be uploaded as a CI artifact and opened directly with no server needed.
"""
from __future__ import annotations
import json as _json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, BaseLoader

from src.config import settings
from src.models import EvalRun, CaseResult
from src.comparison import ComparisonResult
from src.drift import DriftStatus
from src.explain import short_reason, explain_verdict

DIFFICULTY_COLOR = {"easy": "#16a34a", "medium": "#d97706", "hard": "#dc2626"}
DIFFICULTY_ORDER = ["easy", "medium", "hard"]

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Eval Report — {{ run.prompt_version }}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
  :root {
    --pass: #16a34a; --warn: #d97706; --fail: #dc2626;
    --bg: #f4f5f7; --card: #ffffff; --text: #1f2430; --muted: #6b7280;
    --border: #e5e7eb; --accent: #4f46e5;
  }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         background: var(--bg); color: var(--text); margin: 0; padding: 32px; }
  .container { max-width: 1180px; margin: 0 auto; }
  .header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
  h1 { font-size: 22px; margin: 0; display: flex; align-items: center; gap: 10px; }
  .run-id { color: var(--muted); font-size: 12px; }
  .subtitle { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
  .subtitle b { color: var(--text); }
  .status-badge { display: inline-block; padding: 4px 12px; border-radius: 999px;
                  font-weight: 600; font-size: 12px; color: white; }
  .status-PASS { background: var(--pass); }
  .status-WARNING { background: var(--warn); }
  .status-FAIL { background: var(--fail); }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
          padding: 18px 20px; margin-bottom: 20px; }
  .scorecard { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
               gap: 14px; }
  .metric { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
            padding: 14px 16px; }
  .metric .label { font-size: 11px; color: var(--muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: .02em; }
  .metric .value { font-size: 22px; font-weight: 700; }
  .metric .delta-up { color: var(--pass); font-size: 12px; }
  .metric .delta-down { color: var(--fail); font-size: 12px; }
  .metric .delta-flat { color: var(--muted); font-size: 12px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
  th { color: var(--muted); font-weight: 600; font-size: 11px; text-transform: uppercase; }
  tr:nth-child(odd) td { background: #fff8f2; }
  .tag-regression { color: var(--fail); font-weight: 600; }
  .tag-improvement { color: var(--pass); font-weight: 600; }
  .check-ok { color: var(--pass); font-weight: 700; }
  .check-bad { color: var(--fail); font-weight: 700; }
  .section-title { font-size: 15px; font-weight: 700; margin: 0 0 12px 0; }
  .section-caption { font-size: 12px; color: var(--muted); margin-top: 8px; }
  .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
  .drift-ok { color: var(--pass); }
  .drift-callout { background: #fef2f2; border: 1px solid #fecaca; border-radius: 10px;
                    padding: 14px 18px; margin-bottom: 20px; display: flex; gap: 12px; }
  .drift-callout .label { color: var(--fail); font-weight: 700; white-space: nowrap; }
  .drift-callout.ok { background: #f0fdf4; border-color: #bbf7d0; }
  .drift-callout.ok .label { color: var(--pass); }
  .bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
  .bar-label { width: 90px; font-size: 13px; color: var(--muted); flex-shrink: 0; }
  .bar-track { flex: 1; background: #eef0f3; border-radius: 6px; height: 16px; position: relative; overflow: hidden; }
  .bar-track.baseline { height: 8px; margin-bottom: 2px; }
  .bar-fill { height: 100%; border-radius: 6px; background: var(--accent); }
  .bar-fill.baseline-fill { background: #c7cbf5; }
  .bar-pct { width: 46px; text-align: right; font-size: 13px; font-weight: 600; flex-shrink: 0; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
  @media (max-width: 900px) { .grid-2, .grid-3 { grid-template-columns: 1fr; } }
  .mini-chart { width: 100%; height: 220px; }
  #trendChart { width: 100%; height: 320px; }
  .empty-state { text-align: center; color: var(--muted); font-style: italic; padding: 20px; }
  .footer { text-align: center; color: var(--muted); font-size: 12px; margin-top: 24px; }
</style>
</head>
<body>
<div class="container">
  <div class="header-row">
    <h1>📄 Evaluation Report
      <span class="status-badge status-{{ run.status }}">{{ run.status }}{% if run.status != 'PASS' %} (Regressions Detected){% endif %}</span>
    </h1>
    <div class="run-id">Run ID: {{ run.run_id }}</div>
  </div>
  <div class="subtitle">
    Prompt Version: <b>{{ run.prompt_version }}</b> &nbsp;·&nbsp;
    Model: <b>{{ run.model }}</b> &nbsp;·&nbsp;
    Dataset: <b>{{ dataset_label }}</b> &nbsp;·&nbsp;
    Baseline: <b>{{ baseline_run.run_id if baseline_run else "N/A (first run)" }}</b> &nbsp;·&nbsp;
    Date: <b>{{ formatted_date }}</b>
  </div>

  <div class="section-title" style="margin-bottom:10px;">Scorecard</div>
  <div class="scorecard" style="margin-bottom:20px;">
    <div class="metric">
      <div class="label">Overall Accuracy</div>
      <div class="value">{{ "%.0f"|format(run.overall_accuracy) }}%</div>
      {% if comparison %}<div class="{{ 'delta-up' if comparison.overall_accuracy_delta >= 0 else 'delta-down' }}">
        {{ "%+.0f"|format(comparison.overall_accuracy_delta) }}% (was {{ "%.0f"|format(run.overall_accuracy - comparison.overall_accuracy_delta) }}%)</div>{% endif %}
    </div>
    <div class="metric">
      <div class="label">Category Accuracy</div>
      <div class="value">{{ "%.0f"|format(avg_category_accuracy) }}%</div>
      {% if baseline_run %}<div class="{{ 'delta-up' if avg_category_accuracy >= avg_baseline_category_accuracy else 'delta-down' }}">
        {{ "%+.0f"|format(avg_category_accuracy - avg_baseline_category_accuracy) }}% (was {{ "%.0f"|format(avg_baseline_category_accuracy) }}%)</div>{% endif %}
    </div>
    <div class="metric">
      <div class="label">Summary Relevance (Avg)</div>
      <div class="value">{{ "%.1f"|format(run.avg_summary_relevance) }} / 5</div>
      {% if baseline_run %}<div class="{{ 'delta-up' if run.avg_summary_relevance >= baseline_run.avg_summary_relevance else 'delta-down' }}">
        {{ "%+.1f"|format(run.avg_summary_relevance - baseline_run.avg_summary_relevance) }} (was {{ "%.1f"|format(baseline_run.avg_summary_relevance) }})</div>{% endif %}
    </div>
    <div class="metric">
      <div class="label">Avg Latency</div>
      <div class="value">{{ "%.2f"|format(run.avg_latency_ms / 1000) }}s</div>
      {% if baseline_run %}<div class="{{ 'delta-up' if run.avg_latency_ms <= baseline_run.avg_latency_ms else 'delta-down' }}">
        {{ "%+.2f"|format((run.avg_latency_ms - baseline_run.avg_latency_ms) / 1000) }}s (was {{ "%.2f"|format(baseline_run.avg_latency_ms / 1000) }}s)</div>{% endif %}
    </div>
    <div class="metric">
      <div class="label">Total Tokens (Avg)</div>
      <div class="value">{{ "%.0f"|format(run.avg_tokens) }}</div>
      {% if baseline_run %}<div class="{{ 'delta-up' if run.avg_tokens <= baseline_run.avg_tokens else 'delta-down' }}">
        {{ "%+.0f"|format(run.avg_tokens - baseline_run.avg_tokens) }} (was {{ "%.0f"|format(baseline_run.avg_tokens) }})</div>{% endif %}
    </div>
    <div class="metric">
      <div class="label">Cost per Run</div>
      <div class="value">${{ "%.4f"|format(run.avg_cost_usd) }}</div>
      {% if baseline_run %}<div class="{{ 'delta-up' if run.avg_cost_usd <= baseline_run.avg_cost_usd else 'delta-down' }}">
        {{ "%+.4f"|format(run.avg_cost_usd - baseline_run.avg_cost_usd) }} (was ${{ "%.4f"|format(baseline_run.avg_cost_usd) }})</div>{% endif %}
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="section-title">Accuracy Over Time</div>
      <div id="trendChart"></div>
    </div>
    <div class="card">
      <div class="section-title">Result Summary</div>
      <table>
        <tr><td>Total Test Cases</td><td><b>{{ run.total_cases }}</b></td></tr>
        <tr><td>Passed</td><td class="tag-improvement">{{ run.total_cases - failed_count }}</td></tr>
        <tr><td>Failed</td><td class="tag-regression">{{ failed_count }}</td></tr>
        <tr><td>Regressions</td><td class="tag-regression">{{ run.regressions }}</td></tr>
        <tr><td>Improvements</td><td class="tag-improvement">{{ run.improvements }}</td></tr>
        <tr><td>No Change</td><td>{{ run.no_change }}</td></tr>
        <tr><td>Statistical Significance</td>
            <td>{{ "Yes" if run.statistically_significant else "No" }}
                {% if run.p_value is not none %}(p = {{ "%.3f"|format(run.p_value) }} {{ '<' if run.statistically_significant else '≥' }} 0.05){% endif %}</td></tr>
      </table>
    </div>
  </div>

  <div class="grid-2">
    <div class="card">
      <div class="section-title">Category Accuracy — Current vs. Baseline</div>
      {% for cat, cur_pct in category_rows %}
      <div class="bar-row">
        <div class="bar-label">{{ cat.capitalize() }}</div>
        <div style="flex:1;">
          <div class="bar-track baseline"><div class="bar-fill baseline-fill" style="width:{{ baseline_category.get(cat, 0)|round(0) }}%;"></div></div>
          <div class="bar-track"><div class="bar-fill" style="width:{{ cur_pct|round(0) }}%;"></div></div>
        </div>
        <div class="bar-pct">{{ "%.0f"|format(cur_pct) }}%</div>
      </div>
      {% endfor %}
    </div>
    <div class="card">
      <div class="section-title">Accuracy by Difficulty</div>
      {% for tier, stats in difficulty_rows %}
      <div class="bar-row">
        <div class="bar-label">{{ tier.capitalize() }} ({{ stats.passed }}/{{ stats.total }})</div>
        <div class="bar-track" style="height:14px;"><div class="bar-fill" style="width:{{ stats.pct|round(0) }}%; background:{{ stats.color }};"></div></div>
        <div class="bar-pct">{{ "%.0f"|format(stats.pct) }}%</div>
      </div>
      {% endfor %}
      <div class="section-caption">Hard cases are intentionally ambiguous/adversarial — see golden_dataset notes</div>
    </div>
  </div>

  <div class="section-title" style="margin: 4px 0 12px 2px;">Trends (Last {{ trend_json_window }} Runs)</div>
  <div class="grid-3">
    <div class="card">
      <div class="section-title">Regression Trend</div>
      <div id="regressionTrend" class="mini-chart"></div>
      <div class="section-caption">Regressions found vs. the immediately prior run</div>
    </div>
    <div class="card">
      <div class="section-title">Latency Trend</div>
      <div id="latencyTrend" class="mini-chart"></div>
      <div class="section-caption">Avg latency per case, per run</div>
    </div>
    <div class="card">
      <div class="section-title">Token Usage Trend</div>
      <div id="tokenTrend" class="mini-chart"></div>
      <div class="section-caption">Avg tokens per case, per run</div>
    </div>
  </div>

  {% if drift %}
  <div class="drift-callout {{ 'ok' if not drift.is_drifting else '' }}">
    <div class="label">{{ "Slow drift check:" if drift.is_drifting else "Drift check:" }}</div>
    <div>{{ drift.message }}</div>
  </div>
  {% endif %}

  <div class="card">
    <div class="section-title">Failed Cases — This Run ({{ failed_count }})</div>
    {% if failed_cases %}
    <table>
      <tr><th>ID</th><th>Email (short)</th><th>Expected</th><th>Predicted</th><th>Failure Reason</th><th>Summary Score</th></tr>
      {% for c in failed_cases %}
      <tr>
        <td class="mono">{{ c.case_id }}</td>
        <td>{{ c.input[:70] }}{% if c.input|length > 70 %}…{% endif %}</td>
        <td>{{ c.expected_category.value }}</td>
        <td>{{ c.actual_category.value if c.actual_category else "no output" }}
            {% if c.category_match %}<span class="check-ok">✓</span>{% else %}<span class="check-bad">✗</span>{% endif %}</td>
        <td>{{ short_reason(c) }}</td>
        <td>{{ c.summary_score }}/5</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="empty-state">🎉 All cases passed — nothing to show here.</div>
    {% endif %}
  </div>

  <div class="card">
    <div class="section-title">Regressed Cases ({{ regression_count }})</div>
    {% if comparison and comparison.regressions %}
    <table>
      <tr><th>ID</th><th>Email (short)</th><th>Expected Category</th><th>Previous Output</th><th>New Output</th><th>Summary Score</th></tr>
      {% for c in comparison.regressions %}
      <tr>
        <td class="mono">{{ c.case_id }}</td>
        <td>{{ c.input[:60] }}{% if c.input|length > 60 %}…{% endif %}</td>
        <td>{{ c.expected_category }}</td>
        <td>{{ c.previous_category or "—" }}
            {% if c.previous_category == c.expected_category %}<span class="check-ok">✓</span>{% else %}<span class="check-bad">✗</span>{% endif %}</td>
        <td>{{ c.new_category or "no output" }}
            {% if c.new_category == c.expected_category %}<span class="check-ok">✓</span>{% else %}<span class="check-bad">✗</span>{% endif %}</td>
        <td>{{ "%.1f"|format(c.previous_summary_score or 0) }} → {{ "%.1f"|format(c.new_summary_score) }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="empty-state">✅ No regressions detected in this run.</div>
    {% endif %}
  </div>

  <div class="card">
    <div class="section-title">Improved Cases ({{ improvement_count }})</div>
    {% if comparison and comparison.improvements %}
    <table>
      <tr><th>ID</th><th>Email (short)</th><th>Expected Category</th><th>Previous Output</th><th>New Output</th><th>Summary Score</th></tr>
      {% for c in comparison.improvements %}
      <tr>
        <td class="mono">{{ c.case_id }}</td>
        <td>{{ c.input[:60] }}{% if c.input|length > 60 %}…{% endif %}</td>
        <td>{{ c.expected_category }}</td>
        <td>{{ c.previous_category or "no output" }}
            {% if c.previous_category == c.expected_category %}<span class="check-ok">✓</span>{% else %}<span class="check-bad">✗</span>{% endif %}</td>
        <td>{{ c.new_category or "—" }}
            {% if c.new_category == c.expected_category %}<span class="check-ok">✓</span>{% else %}<span class="check-bad">✗</span>{% endif %}</td>
        <td>{{ "%.1f"|format(c.previous_summary_score or 0) }} → {{ "%.1f"|format(c.new_summary_score) }}</td>
      </tr>
      {% endfor %}
    </table>
    {% else %}
    <div class="empty-state">No improvements in this run.</div>
    {% endif %}
  </div>

  <div class="footer">
    model-regression-detector · thresholds: warn ≥{{ "%.1f"|format(warning_threshold) }}pp, critical ≥{{ "%.1f"|format(critical_threshold) }}pp ·
    significance: two-proportion z-test, α=0.05
  </div>
</div>

<script>
  const trend = {{ trend_json|safe }};
  Plotly.newPlot('trendChart', [
    {x: trend.versions, y: trend.accuracies, type: 'scatter', mode: 'lines+markers',
     name: 'Overall Accuracy', line: {color: '#4f46e5'}},
    {x: trend.versions, y: trend.moving_avg, type: 'scatter', mode: 'lines',
     name: 'Moving Avg', line: {color: '#d97706', dash: 'dot'}}
  ], {
    margin: {t: 10, r: 10, l: 40, b: 40},
    yaxis: {title: 'Accuracy %', rangemode: 'tozero'},
    legend: {orientation: 'h', y: -0.2}
  }, {displayModeBar: false});

  Plotly.newPlot('regressionTrend', [
    {x: trend.versions, y: trend.regressions, type: 'bar', marker: {color: '#dc2626'}}
  ], {margin: {t: 10, r: 10, l: 30, b: 30}, showlegend: false}, {displayModeBar: false});

  Plotly.newPlot('latencyTrend', [
    {x: trend.versions, y: trend.latencies, type: 'scatter', mode: 'lines+markers', line: {color: '#4f46e5'}}
  ], {margin: {t: 10, r: 10, l: 40, b: 30}, showlegend: false}, {displayModeBar: false});

  Plotly.newPlot('tokenTrend', [
    {x: trend.versions, y: trend.tokens, type: 'bar', marker: {color: '#7c3aed'}}
  ], {margin: {t: 10, r: 10, l: 40, b: 30}, showlegend: false}, {displayModeBar: false});
</script>
</body>
</html>
"""


def _format_date(iso_ts: str) -> str:
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return ts.strftime("%b %d, %Y %H:%M UTC")
    except Exception:
        return iso_ts


def generate_report(
    run: EvalRun,
    baseline_run: EvalRun | None,
    current_cases: list[CaseResult],
    comparison: ComparisonResult | None,
    drift: DriftStatus | None,
    trend_data: dict,
    dataset_version: str = "v1",
) -> str:
    env = Environment(loader=BaseLoader())
    env.globals["short_reason"] = short_reason
    template = env.from_string(TEMPLATE)

    failed_cases = [c for c in current_cases if not c.passed]
    category_rows = sorted(run.category_accuracy.items())
    baseline_category = baseline_run.category_accuracy if baseline_run else {}
    avg_category_accuracy = (
        sum(run.category_accuracy.values()) / len(run.category_accuracy)
        if run.category_accuracy else 0.0
    )
    avg_baseline_category_accuracy = (
        sum(baseline_category.values()) / len(baseline_category)
        if baseline_category else 0.0
    )

    difficulty_rows = []
    for tier in DIFFICULTY_ORDER:
        stats = run.difficulty_breakdown.get(tier)
        if not stats or stats.get("total", 0) == 0:
            continue
        pct = (stats["passed"] / stats["total"]) * 100
        difficulty_rows.append((tier, {
            "passed": stats["passed"], "total": stats["total"],
            "pct": pct, "color": DIFFICULTY_COLOR.get(tier, "#4f46e5"),
        }))

    dataset_label = Path(dataset_version).stem if dataset_version else "v1"

    html = template.render(
        run=run,
        baseline_run=baseline_run,
        comparison=comparison,
        drift=drift,
        dataset_label=dataset_label,
        formatted_date=_format_date(run.timestamp),
        failed_cases=failed_cases,
        failed_count=len(failed_cases),
        regression_count=len(comparison.regressions) if comparison else 0,
        improvement_count=len(comparison.improvements) if comparison else 0,
        category_rows=category_rows,
        baseline_category=baseline_category,
        avg_category_accuracy=avg_category_accuracy,
        avg_baseline_category_accuracy=avg_baseline_category_accuracy,
        difficulty_rows=difficulty_rows,
        trend_json_window=len(trend_data.get("versions", [])),
        trend_json=_json.dumps(trend_data),
        warning_threshold=settings.warning_threshold_pct,
        critical_threshold=settings.critical_threshold_pct,
    )
    return html


def save_report(html: str, run_id: str) -> Path:
    out_dir = Path(settings.reports_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{run_id}.html"
    out_path.write_text(html, encoding="utf-8")
    # Also write a stable "latest.html" pointer for convenience.
    (out_dir / "latest.html").write_text(html, encoding="utf-8")
    return out_path
