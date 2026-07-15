"""
Streamlit dashboard for the eval pipeline.

Run with: streamlit run dashboard/app.py

Pages: Overview / Runs / Cases / Compare Runs / Drift Monitor / Settings
"""
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import storage
from src.config import settings
from src.comparison import compare_runs
from src.drift import check_drift
from src.explain import explain_failure, explain_verdict

st.set_page_config(page_title="LLM Regression Detector", page_icon="📊", layout="wide")

storage.init_db()

# ---------------------------------------------------------------- Styling
st.markdown("""
<style>
.metric-card {
    background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.14); border-radius: 12px;
    padding: 16px 18px; text-align: left;
}
.metric-card .label { font-size: 12px; color: #9ca3af !important; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; }
.metric-card .value { font-size: 28px; font-weight: 700; line-height: 1.1; color: #f3f4f6 !important; }
.metric-card .delta-up { color: #4ade80 !important; font-size: 13px; font-weight: 600; }
.metric-card .delta-down { color: #f87171 !important; font-size: 13px; font-weight: 600; }
.metric-card .delta-flat { color: #9ca3af !important; font-size: 13px; }
.badge { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.badge-pass { background: #dcfce7; color: #15803d; }
.badge-warning { background: #fef3c7; color: #b45309; }
.badge-fail { background: #fee2e2; color: #b91c1c; }
.badge-version { background: #eef2ff; color: #4338ca; }
.badge-mode { background: #fef3c7; color: #92400e; padding: 4px 12px; border-radius: 999px; font-weight: 700; font-size: 12px; }
.badge-mode-live { background: #dcfce7; color: #15803d; }
[data-testid="stDataFrame"] div[role="columnheader"] { position: sticky; top: 0; z-index: 1; background: white; }
</style>
""", unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str | None = None, delta_positive: bool | None = None, icon: str = ""):
    delta_html = ""
    if delta:
        cls = "delta-flat" if delta_positive is None else ("delta-up" if delta_positive else "delta-down")
        arrow = "" if delta_positive is None else ("↑ " if delta_positive else "↓ ")
        delta_html = f'<div class="{cls}">{arrow}{delta}</div>'
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{icon} {label}</div>
        <div class="value">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def status_badge(status: str) -> str:
    cls = {"PASS": "badge-pass", "WARNING": "badge-warning", "FAIL": "badge-fail"}.get(status, "badge-pass")
    icon = {"PASS": "🟢", "WARNING": "🟡", "FAIL": "🔴"}.get(status, "⚪")
    return f'<span class="badge {cls}">{icon} {status}</span>'


def version_badge(version: str) -> str:
    return f'<span class="badge badge-version">{version}</span>'


def time_ago(iso_ts: str) -> str:
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - ts
        mins = int(delta.total_seconds() // 60)
        if mins < 1:
            return "just now"
        if mins < 60:
            return f"{mins} min ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        return f"{hours // 24}d ago"
    except Exception:
        return iso_ts


# ---------------------------------------------------------------- Load data
runs = storage.get_all_runs(limit=1000)

with st.sidebar:
    st.markdown("### 📊 LLM Regression Detector")
    st.caption("CI/CD for LLM-powered features")
    mode_cls = "badge-mode" if (settings.mock_mode or not settings.openai_api_key) else "badge-mode badge-mode-live"
    mode_label = "🟡 Demo Mode" if (settings.mock_mode or not settings.openai_api_key) else "🟢 Live Mode"
    st.markdown(f'<span class="{mode_cls}">{mode_label}</span>', unsafe_allow_html=True)
    st.write("")
    page = st.radio("Navigation", [
        "🏠 Overview", "📋 Runs", "🔍 Cases", "⚖️ Compare Runs", "📈 Drift Monitor", "⚙️ Settings",
    ], label_visibility="collapsed")
    st.divider()
    if runs:
        st.caption(f"Last evaluated: {time_ago(runs[-1].timestamp)}")
    st.caption(f"{len(runs)} runs recorded")

if not runs:
    st.title("No eval runs yet")
    st.info(
        "Run the pipeline first:\n\n"
        "```bash\npython -m src.cli --prompt prompts/v7.yaml\n"
        "python -m src.cli --prompt prompts/v8.yaml\n```"
    )
    st.stop()

latest = runs[-1]
baseline = runs[-2] if len(runs) > 1 else None
latest_cases = storage.get_case_results(latest.run_id)
baseline_cases = storage.get_case_results(baseline.run_id) if baseline else None
comparison = compare_runs(latest_cases, baseline_cases) if baseline else None
drift = check_drift(runs)
baseline_cases_by_id = {c.case_id: c for c in baseline_cases} if baseline_cases else {}


# ==================================================================== Overview
if page == "🏠 Overview":
    st.title("🏠 Overview")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Current Status", latest.status, icon="")
        st.markdown(status_badge(latest.status), unsafe_allow_html=True)
    with c2:
        delta = comparison.overall_accuracy_delta if comparison else None
        metric_card("Overall Accuracy", f"{latest.overall_accuracy:.0f}%",
                     delta=f"{delta:+.0f}%" if delta is not None else None,
                     delta_positive=(delta >= 0) if delta is not None else None, icon="🎯")
    with c3:
        prev_reg = baseline.regressions if baseline else 0
        reg_delta = None
        if baseline is not None:
            reg_delta = "no change" if latest.regressions == prev_reg else f"{latest.regressions - prev_reg:+d} vs last run"
        metric_card("Regressions", str(latest.regressions),
                     delta=reg_delta, delta_positive=(latest.regressions <= prev_reg) if baseline else None, icon="⚠️")
    with c4:
        if drift:
            metric_card(f"{drift.window}-Run Avg Accuracy", f"{drift.current_moving_avg:.0f}%",
                         delta="drifting" if drift.is_drifting else "stable",
                         delta_positive=not drift.is_drifting, icon="📈")
        else:
            metric_card("Runs Recorded", str(len(runs)), icon="🗂️")

    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Accuracy Trend")
        df = pd.DataFrame({
            "version": [r.prompt_version for r in runs],
            "accuracy": [r.overall_accuracy for r in runs],
        })
        window = min(settings.drift_window, len(df))
        df["moving_avg"] = df["accuracy"].rolling(window, min_periods=1).mean()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["version"], y=df["accuracy"], mode="lines+markers", name="Overall Accuracy"))
        fig.add_trace(go.Scatter(x=df["version"], y=df["moving_avg"], mode="lines", name=f"{window}-Run Moving Avg", line=dict(dash="dot")))
        fig.update_layout(yaxis_title="Accuracy %", margin=dict(t=10, l=10, r=10, b=10), height=340)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Category Accuracy (latest run)")
        cat_df = pd.DataFrame({
            "category": list(latest.category_accuracy.keys()),
            "accuracy": list(latest.category_accuracy.values()),
        })
        fig2 = go.Figure(go.Bar(x=cat_df["category"], y=cat_df["accuracy"]))
        fig2.update_layout(yaxis_title="Accuracy %", margin=dict(t=10, l=10, r=10, b=10), height=340)
        st.plotly_chart(fig2, use_container_width=True)

    st.write("")
    st.subheader(f"Regression Diff Viewer — {latest.prompt_version} vs {baseline.prompt_version if baseline else 'N/A'}")

    if not comparison or not comparison.regressions:
        st.success("✅ No regressions detected between this run and the baseline.")
    else:
        for c in comparison.regressions:
            with st.expander(f"🔴 Regression: {c.case_id} — expected `{c.expected_category}`"):
                base_case = baseline_cases_by_id.get(c.case_id)
                cur_case = next((cc for cc in latest_cases if cc.case_id == c.case_id), None)
                colA, colB = st.columns(2)
                with colA:
                    st.markdown(f"**Baseline ({baseline.prompt_version})**")
                    st.write(f"Category: `{c.previous_category or '—'}`")
                    st.caption(base_case.actual_summary if base_case else "—")
                with colB:
                    st.markdown(f"**New Version ({latest.prompt_version})**")
                    st.write(f"Category: `{c.new_category or 'no output'}`")
                    st.caption(cur_case.actual_summary if cur_case else "—")
                st.divider()
                st.markdown("**Judge Verdict**")
                if cur_case:
                    st.info(explain_verdict(base_case, cur_case))

    if comparison and comparison.improvements:
        st.subheader(f"🟢 {len(comparison.improvements)} Improved Cases")
        imp_df = pd.DataFrame([{
            "Case ID": c.case_id,
            "Email": c.input[:70] + ("…" if len(c.input) > 70 else ""),
            "Expected": c.expected_category,
            "Previous → New": f"{c.previous_category or '—'} → {c.new_category}",
        } for c in comparison.improvements])
        st.dataframe(imp_df, use_container_width=True, hide_index=True)


# ==================================================================== Runs
elif page == "📋 Runs":
    st.title("📋 Runs")

    search = st.text_input("🔎 Search runs by version or run ID", "")

    df = pd.DataFrame([{
        "Run ID": r.run_id,
        "Version": r.prompt_version,
        "Model": r.model,
        "Status": r.status,
        "Accuracy": r.overall_accuracy,
        "Regressions": r.regressions,
        "Improvements": r.improvements,
        "p-value": f"{r.p_value:.3f}" if r.p_value is not None else "—",
        "Timestamp": r.timestamp,
    } for r in reversed(runs)])

    if search:
        mask = df["Run ID"].str.contains(search, case=False) | df["Version"].str.contains(search, case=False)
        df = df[mask]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Accuracy": st.column_config.ProgressColumn(
                "Accuracy", format="%.1f%%", min_value=0, max_value=100,
            ),
            "Status": st.column_config.TextColumn("Status", help="🟢 PASS  🟡 WARNING  🔴 FAIL"),
            "p-value": st.column_config.TextColumn(
                "p-value",
                help="Two-proportion z-test p-value vs the previous run. < 0.05 means the "
                     "accuracy change is unlikely to be random noise. '—' means no baseline yet.",
            ),
        },
    )

    st.divider()
    st.subheader("Inspect a run")
    run_ids = [r.run_id for r in reversed(runs)]
    id_to_label = {r.run_id: f"{r.run_id}  ·  {r.prompt_version}" for r in runs}
    selected_id = st.selectbox("Run ID", run_ids, format_func=lambda rid: id_to_label.get(rid, rid))
    selected_run = next(r for r in runs if r.run_id == selected_id)

    st.markdown(f"{version_badge(selected_run.prompt_version)} {version_badge(selected_run.provider)} {status_badge(selected_run.status)}", unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("**Overview**")
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Accuracy", f"{selected_run.overall_accuracy:.1f}%", icon="🎯")
        with c2:
            metric_card("Regressions", str(selected_run.regressions), icon="🔴")
        with c3:
            metric_card("Improvements", str(selected_run.improvements), icon="🟢")
        st.write("")
        st.write(f"**Model:** {selected_run.model}")
        st.write(f"**Timestamp:** {selected_run.timestamp} ({time_ago(selected_run.timestamp)})")
        if selected_run.p_value is not None:
            sig_text = ("Yes" if selected_run.statistically_significant else "No")
            st.write(f"**Statistical significance:** {sig_text} (p = {selected_run.p_value:.3f})")
            st.caption("ℹ️ p < 0.05 means this run's accuracy change vs its baseline is unlikely to be random noise.")

    with st.container(border=True):
        st.markdown("**Metrics**")
        m1, m2, m3 = st.columns(3)
        with m1:
            metric_card("Avg Latency", f"{selected_run.avg_latency_ms:.0f} ms", icon="⏱️")
        with m2:
            metric_card("Avg Tokens", f"{selected_run.avg_tokens:.0f}", icon="🔢")
        with m3:
            metric_card("Avg Summary Relevance", f"{selected_run.avg_summary_relevance:.1f} / 5", icon="⚖️")
        st.write("")
        cat_df = pd.DataFrame({
            "category": list(selected_run.category_accuracy.keys()),
            "accuracy": list(selected_run.category_accuracy.values()),
        })
        fig = go.Figure(go.Bar(x=cat_df["category"], y=cat_df["accuracy"]))
        fig.update_layout(yaxis_title="Accuracy %", height=300, margin=dict(t=10, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw JSON"):
        st.json(selected_run.model_dump())


# ==================================================================== Cases
elif page == "🔍 Cases":
    st.title("🔍 Cases")
    run_id = st.selectbox("Select run", [r.run_id for r in reversed(runs)])
    cases = storage.get_case_results(run_id)

    search = st.text_input("🔎 Search cases by ID or email content", "")

    df = pd.DataFrame([{
        "Case ID": c.case_id,
        "Email": c.input[:60] + ("…" if len(c.input) > 60 else ""),
        "Expected": c.expected_category.value,
        "Actual": c.actual_category.value if c.actual_category else "ERROR",
        "Match": "✅" if c.category_match else "❌",
        "Summary Score": c.summary_score,
        "Confidence": c.confidence,
        "Passed": "✅" if c.passed else "❌",
        "Latency (ms)": round(c.latency_ms, 1),
        "Tokens": c.tokens_used,
    } for c in cases])

    colf1, colf2 = st.columns(2)
    only_failures = colf1.checkbox("Show only failures")
    category_filter = colf2.multiselect("Filter by expected category", sorted(df["Expected"].unique()))

    view = df.copy()
    if search:
        view = view[view["Case ID"].str.contains(search, case=False) | view["Email"].str.contains(search, case=False)]
    if only_failures:
        view = view[view["Passed"] == "❌"]
    if category_filter:
        view = view[view["Expected"].isin(category_filter)]

    def latency_display(ms):
        return f"⚠️ {ms:.0f}ms" if ms > 200 else f"{ms:.0f}ms"

    view = view.copy()
    view["Latency (ms)"] = view["Latency (ms)"].apply(latency_display)

    st.dataframe(
        view, use_container_width=True, hide_index=True,
        column_config={
            "Match": st.column_config.TextColumn("Match", help="✅ category correct  ❌ category mismatch"),
            "Passed": st.column_config.TextColumn("Passed", help="✅ passed  ❌ failed"),
            "Confidence": st.column_config.ProgressColumn("Confidence", format="%.0f%%", min_value=0, max_value=100),
            "Latency (ms)": st.column_config.TextColumn("Latency (ms)", help="⚠️ flagged when above 200ms"),
        },
    )
    st.caption("⚠️ Latency flagged when above 200ms")

    st.divider()
    st.subheader("Case detail")
    if view.empty:
        st.info("No cases match the current filters.")
    else:
        case_id = st.selectbox("Case ID", view["Case ID"].tolist())
        case = next(c for c in cases if c.case_id == case_id)

        result_badge = status_badge("PASS") if case.passed else status_badge("FAIL")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;margin:4px 0 16px 0;">'
            f'<span class="mono" style="color:#6b7280;">{case.case_id}</span>{result_badge}'
            f'</div>', unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.markdown("**📧 Input Email**")
            st.markdown(
                f'<div style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.14);border-radius:8px;'
                f'padding:12px 14px;font-family:ui-monospace,monospace;font-size:13px;'
                f'color:#e5e7eb;margin-top:6px;">{case.input}</div>',
                unsafe_allow_html=True,
            )

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("**🎯 Expected**")
                st.markdown(f'<span class="badge badge-version">{case.expected_category.value}</span>',
                            unsafe_allow_html=True)
                st.write("")
                st.caption("Summary")
                st.write(case.expected_summary)

        with col2:
            with st.container(border=True):
                match_icon = "✅" if case.category_match else "❌"
                st.markdown(f"**🤖 Predicted** {match_icon}")
                pred_cat = case.actual_category.value if case.actual_category else "no output"
                cat_badge_cls = "badge-pass" if case.category_match else "badge-fail"
                st.markdown(f'<span class="badge {cat_badge_cls}">{pred_cat}</span>', unsafe_allow_html=True)
                st.write("")
                st.caption(f"Summary  ·  {case.confidence:.0f}% confidence")
                st.write(case.actual_summary or "—")

        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                metric_card("Judge Score", f"{case.summary_score}/5", icon="⚖️")
            with m2:
                metric_card("Confidence", f"{case.confidence:.0f}%", icon="🎯")
            with m3:
                metric_card("Latency", f"{case.latency_ms:.0f}ms", icon="⏱️")
            with m4:
                metric_card("Tokens", str(case.tokens_used), icon="🔢")

        with st.container(border=True):
            st.markdown("**🔍 Reason for Failure / Verdict**")
            if case.passed:
                st.success(explain_failure(case))
            else:
                st.error(explain_failure(case))
            if case.error:
                st.exception(case.error)


# ==================================================================== Compare Runs
elif page == "⚖️ Compare Runs":
    st.title("⚖️ Compare Runs")
    st.caption("Pick any two runs to see a head-to-head diff — handy for release notes or interview talking points.")

    run_ids = [r.run_id for r in reversed(runs)]
    labels = {r.run_id: f"{r.prompt_version} · {r.run_id}" for r in runs}
    col1, col2 = st.columns(2)
    left_id = col1.selectbox("Run A (before)", run_ids, index=min(1, len(run_ids) - 1), format_func=lambda x: labels[x])
    right_id = col2.selectbox("Run B (after)", run_ids, index=0, format_func=lambda x: labels[x])

    left = next(r for r in runs if r.run_id == left_id)
    right = next(r for r in runs if r.run_id == right_id)
    left_cases = storage.get_case_results(left_id)
    right_cases = storage.get_case_results(right_id)
    cmp = compare_runs(right_cases, left_cases)

    st.markdown(f"### {version_badge(left.prompt_version)} ({left.provider}) → {version_badge(right.prompt_version)} ({right.provider})", unsafe_allow_html=True)

    def compare_row(label, before, after, fmt="{:.1f}", higher_is_better=True):
        delta = after - before
        positive = (delta >= 0) if higher_is_better else (delta <= 0)
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        color = "#16a34a" if positive or delta == 0 else "#dc2626"
        st.markdown(
            f"""<div style="display:flex;justify-content:space-between;padding:10px 4px;border-bottom:1px solid #e5e7eb;">
            <div style="color:#6b7280;">{label}</div>
            <div><b>{fmt.format(before)}</b> &nbsp;→&nbsp; <b>{fmt.format(after)}</b>
            &nbsp;<span style="color:{color};font-weight:700;">{arrow} {fmt.format(abs(delta))}</span></div>
            </div>""",
            unsafe_allow_html=True,
        )

    compare_row("Accuracy", left.overall_accuracy, right.overall_accuracy, "{:.1f}%")
    compare_row("Avg Latency", left.avg_latency_ms, right.avg_latency_ms, "{:.0f}ms", higher_is_better=False)
    compare_row("Avg Tokens", left.avg_tokens, right.avg_tokens, "{:.0f}", higher_is_better=False)
    compare_row("Summary Relevance", left.avg_summary_relevance, right.avg_summary_relevance, "{:.1f}/5")
    for cat in sorted(set(left.category_accuracy) | set(right.category_accuracy)):
        compare_row(f"{cat.capitalize()} accuracy",
                    left.category_accuracy.get(cat, 0.0), right.category_accuracy.get(cat, 0.0), "{:.0f}%")

    st.markdown('<div style="height:28px;"></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("Regressions (A→B)", str(len(cmp.regressions)),
                     delta=None if not cmp.regressions else "review needed",
                     delta_positive=(len(cmp.regressions) == 0), icon="🔴")
    with c2:
        metric_card("Improvements (A→B)", str(len(cmp.improvements)), icon="🟢")
    with c3:
        sig = cmp.statistically_significant
        metric_card("Statistically Significant", "Yes" if sig else "No",
                     delta=f"p = {cmp.p_value:.3f}" if cmp.p_value is not None else None,
                     delta_positive=None, icon="📐")


# ==================================================================== Drift
elif page == "📈 Drift Monitor":
    st.title("📈 Drift Monitor")
    if drift is None:
        st.info(f"Need at least {settings.drift_window} runs to compute a moving average. Currently have {len(runs)}.")
    else:
        status = "🔴 DRIFTING" if drift.is_drifting else "🟢 STABLE"
        c1, c2, c3 = st.columns(3)
        with c1:
            metric_card("Drift Status", status)
        with c2:
            metric_card("Current Moving Avg", f"{drift.current_moving_avg:.1f}%")
        with c3:
            metric_card("Delta vs Reference", f"{drift.delta_pct:+.1f} pts")
        st.caption(drift.message)

        st.write("")
        tabs = st.tabs(["Accuracy", "Latency", "Token Usage", "Summary Quality"])
        window = drift.window

        def trend_chart(values, name, yaxis_title, dash_color="orange"):
            df = pd.DataFrame({"version": [r.prompt_version for r in runs], "value": values})
            df["moving_avg"] = df["value"].rolling(window, min_periods=1).mean()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["version"], y=df["value"], mode="lines+markers", name=name))
            fig.add_trace(go.Scatter(x=df["version"], y=df["moving_avg"], mode="lines",
                                      name=f"{window}-Run Moving Avg", line=dict(dash="dot", color=dash_color)))
            fig.update_layout(yaxis_title=yaxis_title, height=360, margin=dict(t=10, l=10, r=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with tabs[0]:
            trend_chart([r.overall_accuracy for r in runs], "Accuracy", "Accuracy %")
        with tabs[1]:
            trend_chart([r.avg_latency_ms for r in runs], "Latency", "ms")
        with tabs[2]:
            trend_chart([r.avg_tokens for r in runs], "Tokens", "avg tokens/case")
        with tabs[3]:
            trend_chart([r.avg_summary_relevance for r in runs], "Summary Relevance", "score / 5")


# ==================================================================== Settings
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    is_mock = settings.mock_mode or not settings.openai_api_key
    if is_mock:
        st.info("Running in 🟡 Demo Mode — threshold controls below are shown but disabled. "
                "Set `MOCK_MODE=false` and a real `OPENAI_API_KEY` in `.env` to edit these live.")

    tab_controls, tab_raw = st.tabs(["Controls", "Raw JSON"])

    with tab_controls:
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Judge Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
                         index=0, disabled=is_mock,
                         help="Model used for LLM-as-judge summary scoring.")
            st.number_input("Warning Threshold (%)", value=settings.warning_threshold_pct,
                             disabled=is_mock, help="Accuracy drop that triggers a WARNING status.")
            st.number_input("Drift Window (runs)", value=settings.drift_window,
                             disabled=is_mock, help="Number of runs in the rolling moving average.")
        with c2:
            st.selectbox("LLM Model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
                         index=0, disabled=is_mock,
                         help="Model used for the feature under test.")
            st.number_input("Critical Threshold (%)", value=settings.critical_threshold_pct,
                             disabled=is_mock, help="Accuracy drop that triggers a FAIL and blocks merge.")
            st.number_input("Drift Threshold (%)", value=settings.drift_threshold_pct,
                             disabled=is_mock, help="Moving-average drop that triggers a slow-drift alert.")
        st.caption("Edit `.env` directly and restart the app to change these for real — this panel mirrors "
                   "current config for visibility.")

    with tab_raw:
        st.json({
            "mock_mode": settings.mock_mode,
            "llm_model": settings.llm_model,
            "judge_model": settings.judge_model,
            "warning_threshold_pct": settings.warning_threshold_pct,
            "critical_threshold_pct": settings.critical_threshold_pct,
            "drift_window": settings.drift_window,
            "drift_threshold_pct": settings.drift_threshold_pct,
            "slack_configured": bool(settings.slack_webhook_url),
            "db_path": settings.db_path,
            "dataset_path": settings.dataset_path,
        })

    st.divider()
    st.subheader("Run a new eval from here")
    prompt_files = sorted(str(p) for p in Path("prompts").glob("*.yaml"))
    chosen = st.selectbox("Prompt version", prompt_files)
    if st.button("Run eval"):
        with st.spinner(f"Running eval against {chosen}..."):
            result = subprocess.run(
                ["python", "-m", "src.cli", "--prompt", chosen, "--no-slack"],
                capture_output=True, text=True,
            )
        st.code(result.stdout + "\n" + result.stderr)
        if result.returncode == 0:
            st.success("✅ Run completed with PASS status — refresh the page to see it.")
        else:
            st.warning("⚠️ Run completed but flagged WARNING/FAIL against thresholds — this is the pipeline "
                       "correctly catching a regression, not a crash. See the log above and check the Runs page.")
