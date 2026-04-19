"""
The Hartford India — LinkedIn Competitive Intelligence Dashboard
Material Design 3 · Dark Theme · Zero external dependencies (inline SVG icons)

Launch: python -m streamlit run app.py
"""

import sys, os, io, re
from datetime import datetime, timedelta, timezone

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import streamlit as st
import plotly.express as px
import pandas as pd

try:
    import openpyxl
    _EXCEL_OK = True
except ImportError:
    _EXCEL_OK = False

import asyncio
import collections
from services.intelligence import draft_counter_post
from services.storage import (
    init_db, get_all_posts, get_stored_companies, get_all_analyses,
)

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LinkedIn Intelligence — The Hartford India",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Inline SVG Icon Helper ────────────────────────────────────────────────────

def icon(path_d, size=14, color="currentColor", style=""):
    """Render a reliable inline SVG icon — no CDN, no fonts."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="{color}" '
        f'style="vertical-align:middle;flex-shrink:0;{style}">'
        f'<path d="{path_d}"/></svg>'
    )

# Material Design SVG paths
P_BUILDING  = "M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V5h2v2zm10 12h-8V9h8v10zm-2-8h-4v2h4v-2zm0 4h-4v2h4v-2z"
P_CLOCK     = "M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67V7z"
P_BELL      = "M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6V11c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C9.63 5.36 8 7.92 8 11v5l-2 2v1h16v-1l-2-2z"
P_WARNING   = "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"
P_CHECK     = "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"
P_TREND     = "M16 6l2.29 2.29-4.88 4.88-4-4L2 16.59 3.41 18l6-6 4 4 6.3-6.29L22 12V6h-6z"
P_CHART     = "M5 9.2h3V19H5zM10.6 5h2.8v14h-2.8zm5.6 8H19v6h-2.8z"
P_DOWNLOAD  = "M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"
P_SEARCH    = "M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"
P_THUMB     = "M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"
P_CHAT      = "M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"
P_REPEAT    = "M7 7h10v3l4-4-4-4v3H5v6h2V7zm10 10H7v-3l-4 4 4 4v-3h12v-6h-2v4z"
P_BOLT      = "M7 2v11h3v9l7-12h-4l4-8z"
P_CHECKLIST = "M3 5h2v2H3zm0 4h2v2H3zm0 4h2v2H3zm4-8h14v2H7zm0 4h14v2H7zm0 4h14v2H7z"

# ── CSS ───────────────────────────────────────────────────────────────────────

st.html("""
<style>
:root {
  --bg:          #080B12;
  --surf-1:      #161B27;
  --surf-2:      #1C2234;
  --surf-3:      #222A40;
  --primary:     #5B8AF0;
  --primary-dim: rgba(91,138,240,0.12);
  --primary-med: rgba(91,138,240,0.20);
  --success:     #10B981;
  --warning:     #F59E0B;
  --error:       #EF4444;
  --on-surf:     #E2E8F0;
  --on-var:      #8892A8;
  --border:      rgba(255,255,255,0.07);
  --border-med:  rgba(255,255,255,0.13);
}

html, body, [class*="css"], p, div, label, button {
  font-family: -apple-system, 'Segoe UI', Roboto, system-ui, sans-serif !important;
}
.main { background: var(--bg) !important; }
.main .block-container {
  padding-top: 0 !important;
  padding-bottom: 2rem !important;
  padding-left: 2.5rem !important;
  padding-right: 2.5rem !important;
  max-width: 1280px !important;
}

/* App bar */
.app-bar {
  display: flex; align-items: center; gap: 14px;
  padding: 20px 0 16px 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}
.app-logo {
  width: 40px; height: 40px;
  background: linear-gradient(135deg, #5B8AF0, #7C5CFC);
  border-radius: 11px;
  display: flex; align-items: center; justify-content: center;
  font-size: 0.95rem; font-weight: 700; color: #fff;
  flex-shrink: 0; letter-spacing: -0.5px;
  box-shadow: 0 4px 14px rgba(91,138,240,0.3);
}
.app-title { font-size: 1.05rem; font-weight: 700; color: var(--on-surf); }
.app-sub   { font-size: 0.73rem; color: var(--on-var); margin-top: 2px; }
.app-spacer { flex: 1; }
.app-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--surf-1); border: 1px solid var(--border-med);
  border-radius: 20px; padding: 5px 14px;
  font-size: 0.72rem; color: var(--on-var); font-variant-numeric: tabular-nums;
}

/* KPI cards */
.kpi-card {
  background: var(--surf-1); border: 1px solid var(--border);
  border-radius: 18px; padding: 20px 22px;
  display: flex; flex-direction: column; gap: 8px;
  transition: all 0.22s ease; position: relative; overflow: hidden;
}
.kpi-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: var(--kc); border-radius: 18px 18px 0 0;
}
.kpi-card:hover {
  border-color: var(--border-med); transform: translateY(-2px);
  box-shadow: 0 10px 32px rgba(0,0,0,0.35);
}
.kpi-icon {
  width: 36px; height: 36px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  background: var(--kb);
}
.kpi-val {
  font-size: 2rem; font-weight: 700; color: var(--on-surf);
  line-height: 1; letter-spacing: -1px;
}
.kpi-lbl {
  font-size: 0.68rem; font-weight: 600; color: var(--on-var);
  text-transform: uppercase; letter-spacing: 1.1px;
}

/* Section headers */
.sec-hdr {
  display: flex; align-items: center; gap: 10px;
  margin: 30px 0 14px 0;
}
.sec-accent {
  width: 3px; height: 18px; background: var(--primary);
  border-radius: 2px; flex-shrink: 0;
}
.sec-title {
  font-size: 0.72rem; font-weight: 700; color: var(--on-var);
  text-transform: uppercase; letter-spacing: 1.6px;
  display: flex; align-items: center; gap: 7px;
}
.sec-line { flex: 1; height: 1px; background: var(--border); }

/* Bordered container */
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--surf-1) !important;
  border: 1px solid var(--border-med) !important;
  border-radius: 18px !important;
}

/* Preview badge */
.prev-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--primary-dim); color: #93C5FD;
  border: 1px solid rgba(91,138,240,0.22);
  border-radius: 24px; padding: 4px 14px;
  font-size: 0.73rem; font-weight: 500; margin-bottom: 12px;
}

/* Post cards */
.post-card {
  background: var(--surf-1); border: 1px solid var(--border);
  border-radius: 16px; padding: 18px 22px; margin-bottom: 10px;
  transition: all 0.2s ease;
}
.post-card:hover {
  border-color: var(--border-med); background: var(--surf-2);
  box-shadow: 0 6px 28px rgba(0,0,0,0.32); transform: translateY(-1px);
}
.card-hdr {
  display: flex; align-items: center; gap: 7px;
  flex-wrap: wrap; margin-bottom: 10px;
}
.card-company { font-size: 0.9rem; font-weight: 600; color: var(--on-surf); }
.card-date    { font-size: 0.72rem; color: var(--on-var); margin-left: auto; white-space: nowrap; }
.chip {
  display: inline-flex; align-items: center;
  padding: 2px 9px; border-radius: 8px;
  font-size: 0.67rem; font-weight: 600; letter-spacing: 0.3px; white-space: nowrap;
}
.ch-high { background:rgba(239,68,68,0.13);  color:#FCA5A5; border:1px solid rgba(239,68,68,0.22); }
.ch-med  { background:rgba(245,158,11,0.13); color:#FCD34D; border:1px solid rgba(245,158,11,0.22); }
.ch-low  { background:rgba(16,185,129,0.12); color:#6EE7B7; border:1px solid rgba(16,185,129,0.2); }
.ch-type { background:rgba(124,92,252,0.12); color:#C4B5FD; border:1px solid rgba(124,92,252,0.2); }
.ch-cls  { background:rgba(91,138,240,0.10); color:#93C5FD; border:1px solid rgba(91,138,240,0.18); }

.card-snap { font-size: 0.88rem; color: #CBD5E1; line-height: 1.6; margin-bottom: 10px; }

.card-action {
  display: flex; gap: 8px; align-items: flex-start;
  background: rgba(16,185,129,0.07); border-left: 2px solid var(--success);
  border-radius: 0 8px 8px 0; padding: 8px 12px; margin-bottom: 12px;
}
.action-body { font-size: 0.81rem; color: #A7F3D0; line-height: 1.55; }

.card-foot {
  display: flex; align-items: center; gap: 16px;
  padding-top: 10px; border-top: 1px solid var(--border);
}
.stat { display: flex; align-items: center; gap: 5px; font-size: 0.77rem; color: var(--on-var); }
.eng-pill {
  margin-left: auto; background: var(--primary-dim); color: var(--primary);
  border-radius: 8px; padding: 2px 10px; font-size: 0.72rem; font-weight: 500;
  font-variant-numeric: tabular-nums;
}

/* Pagination */
.page-info {
  text-align: center; color: var(--on-var); font-size: 0.8rem;
  display: flex; align-items: center; justify-content: center; gap: 8px; padding: 4px 0;
}

/* Streamlit overrides */
label[data-testid="stWidgetLabel"] p {
  color: var(--on-var) !important; font-size: 0.71rem !important;
  font-weight: 600 !important; text-transform: uppercase !important; letter-spacing: 0.9px !important;
}
div[data-baseweb="select"] > div {
  background: var(--surf-2) !important; border: 1px solid var(--border-med) !important;
  border-radius: 12px !important;
}
div[data-baseweb="select"] > div:focus-within { border-color: var(--primary) !important; }
div[data-baseweb="select"] span { color: var(--on-surf) !important; font-size: 0.85rem !important; }
div[data-baseweb="popover"] {
  background: var(--surf-2) !important; border: 1px solid var(--border-med) !important;
  border-radius: 12px !important;
}
li[role="option"] { color: var(--on-surf) !important; }
li[role="option"]:hover { background: var(--primary-dim) !important; }
div[data-testid="stRadio"] p { color: var(--on-surf) !important; font-size: 0.85rem !important; }
.stButton > button {
  background: var(--surf-2) !important; color: #93C5FD !important;
  border: 1px solid rgba(91,138,240,0.25) !important; border-radius: 12px !important;
  font-weight: 500 !important; font-size: 0.84rem !important; transition: all 0.2s !important;
}
.stButton > button:hover {
  background: var(--primary-med) !important; border-color: var(--primary) !important;
}
.stButton > button:disabled { opacity: 0.3 !important; }
.stDownloadButton > button {
  background: var(--primary-dim) !important; color: #93C5FD !important;
  border: 1px solid rgba(91,138,240,0.25) !important; border-radius: 12px !important;
  font-weight: 500 !important; font-size: 0.84rem !important; transition: all 0.2s !important;
}
.stDownloadButton > button:hover {
  background: var(--primary-med) !important; border-color: var(--primary) !important;
}
div[data-testid="stExpander"] > details {
  background: var(--surf-2) !important; border: 1px solid var(--border) !important;
  border-radius: 10px !important; margin-top: 6px !important;
}
div[data-testid="stExpander"] > details > summary {
  color: var(--on-var) !important; font-size: 0.79rem !important; padding: 10px 14px !important;
}
div[data-testid="stExpander"] > details > summary:hover { color: var(--on-surf) !important; }
div[data-testid="stDataFrame"] { border-radius: 12px !important; overflow: hidden !important; }
div.stAlert { border-radius: 12px !important; font-size: 0.85rem !important; }
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--surf-3); border-radius: 6px; }
</style>
""")

# ── Helpers ───────────────────────────────────────────────────────────────────

def sec_header(svg_path, title):
    st.markdown(
        f'<div class="sec-hdr">'
        f'<div class="sec-accent"></div>'
        f'<span class="sec-title">'
        f'{icon(svg_path, 13, "#5B8AF0")}&nbsp;{title}'
        f'</span>'
        f'<span class="sec-line"></span>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Init ──────────────────────────────────────────────────────────────────────

init_db()

# ── Cache helper ──────────────────────────────────────────────────────────────
# st.cache_data requires serializable (picklable) return values, so we convert
# SQLAlchemy ORM rows → plain dicts, then wrap in SimpleNamespace for the same
# attribute-access syntax the rest of the app uses. Supabase is only queried
# once per 5-minute TTL; every filter/pagination change works on in-memory data.

from types import SimpleNamespace

@st.cache_data(ttl=300, show_spinner="Loading intelligence data...")
def load_dashboard_data():
    """Load all posts + analyses in 2 DB queries and return as plain dicts."""
    raw_posts     = get_all_posts()
    raw_analyses  = get_all_analyses()   # dict[post_id -> AnalysisRow]
    raw_companies = get_stored_companies()

    posts_dicts = [p.to_dict() for p in raw_posts]

    analyses_dicts = {}
    for post_id, a in raw_analyses.items():
        analyses_dicts[post_id] = {
            "executive_snapshot":     a.executive_snapshot or "",
            "content_classification": a.content_classification or "",
            "strategic_intent":       a.strategic_intent or "",
            "engagement_analysis":    a.engagement_analysis or "",
            "creative_breakdown":     a.creative_breakdown or "",
            "competitive_insight":    a.competitive_insight or "",
            "recommended_action":     a.recommended_action or "",
            "alert_tag":              a.alert_tag or "LOW",
            "trend_signal":           a.trend_signal or "",
        }

    return posts_dicts, analyses_dicts, raw_companies

_posts_raw, _analyses_raw, companies = load_dashboard_data()

# Wrap as SimpleNamespace so attribute access (post.company, analysis.alert_tag)
# works identically to before — zero changes needed in the rest of the file.
# Timestamps come back as ISO strings from to_dict(); parse them back to datetime.
def _to_post_ns(d: dict) -> SimpleNamespace:
    ns = SimpleNamespace(**d)
    ts = d.get("timestamp", "")
    if ts:
        try:
            ns.timestamp = datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            ns.timestamp = None
    else:
        ns.timestamp = None
    return ns

posts    = [_to_post_ns(p) for p in _posts_raw]
analyses = {pid: SimpleNamespace(**a) for pid, a in _analyses_raw.items()}

if not companies:
    st.info("No data yet. Run: python main.py --analyze --count 5  then refresh.")
    st.stop()

def sort_key(post):
    a = analyses.get(post.id)
    order = {"HIGH PRIORITY": 0, "MEDIUM": 1, "LOW": 2}
    return (order.get(a.alert_tag if a else "LOW", 2), -post.engagement_score)

sorted_posts = sorted(posts, key=sort_key)

# ─────────────────────────────────────────────────────────────────────────────
# APP BAR
# ─────────────────────────────────────────────────────────────────────────────

now_str = datetime.now().strftime("%d %b %Y, %H:%M")
st.markdown(f"""
<div class="app-bar">
  <div class="app-logo">TH</div>
  <div>
    <div class="app-title">The Hartford India</div>
    <div class="app-sub">LinkedIn Competitive Intelligence &mdash; Vanguard &middot; Chubb &middot; HCA Healthcare &middot; Lloyds &middot; Carelon</div>
  </div>
  <div class="app-spacer"></div>
  <div class="app-badge">
    {icon(P_CLOCK, 12, "#10B981")}
    {now_str}
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────

high_posts   = [p for p in posts if analyses.get(p.id) and analyses[p.id].alert_tag == "HIGH PRIORITY"]
medium_posts = [p for p in posts if analyses.get(p.id) and analyses[p.id].alert_tag == "MEDIUM"]
low_posts    = [p for p in posts if analyses.get(p.id) and analyses[p.id].alert_tag == "LOW"]
avg_eng      = int(sum(p.engagement_score for p in posts) / len(posts)) if posts else 0

kpis = [
    (P_BELL,    "#EF4444", "rgba(239,68,68,0.13)",   len(high_posts),  "Needs Action"),
    (P_WARNING, "#F59E0B", "rgba(245,158,11,0.13)",  len(medium_posts), "Watch"),
    (P_CHECK,   "#10B981", "rgba(16,185,129,0.12)",  len(low_posts),   "Routine"),
    (P_TREND,   "#5B8AF0", "rgba(91,138,240,0.13)",  f"{avg_eng:,}",   "Avg Engagement"),
]

cols = st.columns(4, gap="medium")
for col, (svg_path, color, bg, val, label) in zip(cols, kpis):
    with col:
        st.markdown(f"""
        <div class="kpi-card" style="--kc:{color}; --kb:{bg}">
          <div class="kpi-icon">{icon(svg_path, 16, color)}</div>
          <div class="kpi-val">{val}</div>
          <div class="kpi-lbl">{label}</div>
        </div>
        """, unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 — ENGAGEMENT BY COMPANY
# ═════════════════════════════════════════════════════════════════════════════

sec_header(P_CHART, "Engagement vs Themes")

with st.container(border=True):
    ch_col1, ch_col2 = st.columns(2, gap="large")
    
    with ch_col1:
        st.markdown("<p style='font-size:14px;color:#CBD5E1;margin-bottom:0;'>Avg Engagement by Company</p>", unsafe_allow_html=True)
        df = pd.DataFrame([{"Company": p.company, "Engagement": p.engagement_score} for p in posts])
        company_avg = df.groupby("Company")["Engagement"].mean().reset_index()
        company_avg.columns = ["Company", "Avg Engagement"]
        company_avg = company_avg.sort_values("Avg Engagement", ascending=True)

        fig = px.bar(
            company_avg, x="Avg Engagement", y="Company", orientation="h",
            color="Avg Engagement",
            color_continuous_scale=["#1C2234", "#5B8AF0", "#7C5CFC"],
            text=company_avg["Avg Engagement"].round(0).astype(int),
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="system-ui, sans-serif", color="#8892A8"),
            showlegend=False, coloraxis_showscale=False,
            height=260, margin=dict(l=0, r=50, t=20, b=8),
            xaxis=dict(showgrid=False, showticklabels=False, title=""),
            yaxis=dict(showgrid=False, title="", tickfont=dict(size=12, color="#CBD5E1")),
        )
        fig.update_traces(textposition="outside", textfont=dict(color="#8892A8", size=11), marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True)

    with ch_col2:
        st.markdown("<p style='font-size:14px;color:#CBD5E1;margin-bottom:0;'>Industry Share of Voice by Theme</p>", unsafe_allow_html=True)
        
        # Extract primary theme (before slash or plus)
        themes = []
        for pid, a in analyses.items():
            if a.content_classification and a.content_classification != "UNKNOWN":
                primary = re.split(r'[/+]', a.content_classification)[0].strip()
                themes.append(primary)
        
        if themes:
            theme_counts = collections.Counter(themes).most_common(6)
            theme_df = pd.DataFrame(theme_counts, columns=["Theme", "Count"])
            fig_pie = px.pie(
                theme_df, values='Count', names='Theme', hole=0.6,
                color_discrete_sequence=["#7C5CFC", "#5B8AF0", "#10B981", "#EF4444", "#F59E0B", "#8892A8"]
            )
            fig_pie.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="system-ui, sans-serif", color="#8892A8"),
                showlegend=False, height=260, margin=dict(l=0, r=0, t=30, b=0),
            )
            fig_pie.update_traces(
                textposition='inside', textinfo='percent+label',
                marker=dict(line=dict(color='#0F1423', width=2))
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No theme data available yet.", icon="📊")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 — DOWNLOAD CENTER
# ═════════════════════════════════════════════════════════════════════════════

sec_header(P_DOWNLOAD, "Download Center")

with st.container(border=True):
    st.markdown(
        "<p style='font-size:0.78rem;color:#8892A8;margin:0 0 14px 0;'>"
        "Export post data as CSV or Excel — filter by company, post count, or date range.</p>",
        unsafe_allow_html=True,
    )

    dl_c1, dl_c2, dl_c3 = st.columns([2, 2, 2], gap="medium")
    with dl_c1:
        dl_company = st.selectbox("Company", ["All Companies"] + sorted(companies), key="dl_co")
    with dl_c2:
        filter_mode = st.radio("Filter by", ["Past N posts", "Past N days"], horizontal=True, key="dl_mode")
    with dl_c3:
        if filter_mode == "Past N posts":
            n_posts_dl = st.selectbox("Posts", [10, 25, 50, 100, 250, "All"], index=2, key="dl_np")
        else:
            n_days_dl = st.selectbox("Time window", [7, 14, 30, 60, 90, 180], index=2, key="dl_nd",
                                     format_func=lambda d: f"Past {d} days")

    sel_co = None if dl_company == "All Companies" else dl_company
    if filter_mode == "Past N posts":
        pool_dl = [p for p in sorted_posts if sel_co is None or p.company == sel_co]
        ep      = pool_dl if n_posts_dl == "All" else pool_dl[:int(n_posts_dl)]
        flbl    = f"last {n_posts_dl} posts" if n_posts_dl != "All" else "all posts"
    else:
        cutoff_dl = datetime.now(timezone.utc) - timedelta(days=n_days_dl)
        ep = [
            p for p in sorted_posts
            if (sel_co is None or p.company == sel_co) and p.timestamp is not None
            and p.timestamp.replace(
                tzinfo=timezone.utc if p.timestamp.tzinfo is None else p.timestamp.tzinfo
            ) >= cutoff_dl
        ]
        flbl = f"past {n_days_dl} days"

    rows = []
    for p in ep:
        a  = analyses.get(p.id)
        ht = p.hashtags or []
        rows.append({
            "Company":                p.company,
            "Date":                   p.timestamp.strftime("%Y-%m-%d %H:%M") if p.timestamp else "",
            "Post Description":       (p.text or "").replace("\n", " ").strip(),
            "Content Classification": a.content_classification if a else "",
            "Engagement Score":       p.engagement_score,
            "Hashtags":               " ".join(f"#{h}" for h in ht) if ht else "No hashtags",
            "Post URL":               p.post_url or "",
        })
    exp_df = pd.DataFrame(rows)

    st.markdown(
        f'<div class="prev-badge">'
        f'{icon(P_CHECKLIST, 12, "#93C5FD")}'
        f'&nbsp;{len(exp_df)} posts &nbsp;&middot;&nbsp; {flbl}</div>',
        unsafe_allow_html=True,
    )

    if not exp_df.empty:
        st.dataframe(exp_df, use_container_width=True, height=160, hide_index=True)
        base_nm = f"linkedin_posts_{dl_company.replace(' ','_')}_{datetime.now().strftime('%Y%m%d')}"
        b1, b2  = st.columns(2, gap="small")
        with b1:
            st.download_button("Download CSV", exp_df.to_csv(index=False).encode("utf-8-sig"),
                               f"{base_nm}.csv", "text/csv", use_container_width=True, key="dl_csv")
        with b2:
            if _EXCEL_OK:
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as w:
                    exp_df.to_excel(w, index=False, sheet_name="Posts")
                    ws = w.sheets["Posts"]
                    for cc in ws.columns:
                        ws.column_dimensions[cc[0].column_letter].width = min(
                            max(len(str(c.value or "")) for c in cc) + 4, 60)
                buf.seek(0)
                st.download_button("Download Excel", buf, f"{base_nm}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True, key="dl_xl")
            else:
                st.info("pip install openpyxl to enable Excel export")
    else:
        st.warning("No posts match. Try widening the filter.")

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 — INTELLIGENCE FEED
# ═════════════════════════════════════════════════════════════════════════════

sec_header(P_SEARCH, "Intelligence Feed")

# Filters
with st.container(border=True):
    f1, f2, f3, f4 = st.columns([2, 2, 2, 2], gap="medium")
    with f1:
        feed_co = st.selectbox("Company",
                               ["All Companies"] + sorted(set(p.company for p in posts)), key="f_co")
    with f2:
        feed_al = st.selectbox("Alert Level",
                               ["All Alerts", "HIGH PRIORITY", "MEDIUM", "LOW"], key="f_al")
    with f3:
        feed_ty = st.selectbox("Post Type",
                               ["All Types"] + sorted(set(p.post_type for p in posts if p.post_type)), key="f_ty")
    with f4:
        date_map    = {"All Time": None, "Last 7 days": 7, "Last 14 days": 14,
                       "Last 30 days": 30, "Last 90 days": 90}
        feed_dt_lbl = st.selectbox("Date Range", list(date_map.keys()), key="f_dt")
        feed_days   = date_map[feed_dt_lbl]

# Apply filters
pool = sorted_posts[:]
if feed_co != "All Companies":  pool = [p for p in pool if p.company == feed_co]
if feed_al != "All Alerts":     pool = [p for p in pool if analyses.get(p.id) and analyses[p.id].alert_tag == feed_al]
if feed_ty != "All Types":      pool = [p for p in pool if p.post_type == feed_ty]
if feed_days:
    cutoff_f = datetime.now(timezone.utc) - timedelta(days=feed_days)
    pool = [p for p in pool if p.timestamp and
            p.timestamp.replace(tzinfo=timezone.utc if p.timestamp.tzinfo is None else p.timestamp.tzinfo) >= cutoff_f]

# Pagination
PER_PAGE = 5
total    = len(pool)
pages    = max(1, (total + PER_PAGE - 1) // PER_PAGE)

if "fp"   not in st.session_state: st.session_state.fp   = 1
if "fsig" not in st.session_state: st.session_state.fsig = None

fsig = (feed_co, feed_al, feed_ty, feed_dt_lbl)
if st.session_state.fsig != fsig:
    st.session_state.fp   = 1
    st.session_state.fsig = fsig

cur_pg     = max(1, min(st.session_state.fp, pages))
page_items = pool[(cur_pg - 1) * PER_PAGE: cur_pg * PER_PAGE]

# Card renderer
def render_card(post, analysis):
    tag      = analysis.alert_tag if analysis else "LOW"
    chip_cls = {"HIGH PRIORITY": "ch-high", "MEDIUM": "ch-med"}.get(tag, "ch-low")
    date_str = post.timestamp.strftime("%d %b %Y") if post.timestamp else "—"
    cls_txt  = analysis.content_classification if analysis else ""

    snap = (analysis.executive_snapshot or "").strip() if analysis else ""
    if not snap:
        snap = (post.text or "")[:160].replace("\n", " ").strip() + "..."
    
    # Clean up any AI-generated markdown asterisks from the snapshot
    snap = snap.replace('*', '')

    action = ""
    if analysis and analysis.recommended_action:
        action = analysis.recommended_action.strip()
        # Ensure bullet points and numbered lists break to a new line
        action = re.sub(r'\n', '<br>', action)
        action = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', action)
        action = re.sub(r'\*(.*?)\*', r'<i>\1</i>', action)

    action_html = (
        f'<div class="card-action">'
        f'{icon(P_BOLT, 13, "#10B981", "margin-top:3px;flex-shrink:0")}'
        f'<span class="action-body">&nbsp;{action}</span>'
        f'</div>'
    ) if action else ""

    cls_html  = f'<span class="chip ch-cls">{cls_txt}</span>'  if cls_txt      else ""
    type_html = f'<span class="chip ch-type">{post.post_type}</span>' if post.post_type else ""

    st.markdown(f"""
    <div class="post-card">
      <div class="card-hdr">
        <span class="card-company">{post.company}</span>
        <span class="chip {chip_cls}">{tag}</span>
        {cls_html}
        {type_html}
        <span class="card-date">{date_str}</span>
      </div>
      <div class="card-snap">{snap}</div>
      {action_html}
      <div class="card-foot">
        <span class="stat">
          {icon(P_THUMB, 13, "#8892A8")} {post.likes:,}
        </span>
        <span class="stat">
          {icon(P_CHAT, 13, "#8892A8")} {post.comments:,}
        </span>
        <span class="stat">
          {icon(P_REPEAT, 13, "#8892A8")} {post.shares:,}
        </span>
        <span class="eng-pill">Eng {post.engagement_score:,}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_exp, col_btn = st.columns([4, 1], vertical_alignment="center")
    with col_exp:
        with st.expander("View Detailed Intelligence", expanded=False):
            ca, cb = st.columns([2, 1])
            with ca:
                if analysis:
                    st.markdown(f"**Strategic Intent:** {analysis.strategic_intent}")
                    st.markdown(f"**Competitive Insight:** {analysis.competitive_insight}")
                    st.markdown(f"**Trend Signal:** {analysis.trend_signal}")
            with cb:
                st.markdown(f"**Engagement Rate:** {post.engagement_rate:.2f}%")
                st.markdown(f"**Post Type:** {post.post_type}")
                if post.hashtags:
                    st.markdown(f"**Hashtags:** #{' #'.join(post.hashtags[:5])}")
                if post.post_url:
                    st.markdown(f"[View on LinkedIn →]({post.post_url})")

    gen_post_result = False
    with col_btn:
        if st.button("Draft Counter-Post", key=f"draft_{post.id}", icon=":material/edit:"):
            gen_post_result = True
            
    if gen_post_result:
        with st.spinner("Mistral AI is drafting a counter-post..."):
            gen_post = asyncio.run(draft_counter_post(
                {"company": post.company, "text": post.text},
                analysis
            ))
        st.success("Draft Generated for The Hartford India!")
        st.info(gen_post)

# Render
if not pool:
    st.info("No posts match the selected filters. Try widening the criteria.")
else:
    for post in page_items:
        render_card(post, analyses.get(post.id))

    pl, pc, pr = st.columns([1, 3, 1])
    with pl:
        if st.button("Previous", disabled=(cur_pg <= 1), use_container_width=True, key="fp_prev"):
            st.session_state.fp = cur_pg - 1
            st.rerun()
    with pc:
        st.markdown(
            f'<div class="page-info">'
            f'Page {cur_pg} of {pages} &nbsp;&middot;&nbsp; {total} post{"s" if total != 1 else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with pr:
        if st.button("Next", disabled=(cur_pg >= pages), use_container_width=True, key="fp_next"):
            st.session_state.fp = cur_pg + 1
            st.rerun()

# Footer
st.markdown(
    f'<div style="text-align:center;color:#2D3748;font-size:0.7rem;'
    f'letter-spacing:0.6px;padding:28px 0 8px;">'
    f'{len(posts)} posts &nbsp;&middot;&nbsp; {len(analyses)} analyzed &nbsp;&middot;&nbsp; '
    f'{len(companies)} competitors</div>',
    unsafe_allow_html=True,
)
