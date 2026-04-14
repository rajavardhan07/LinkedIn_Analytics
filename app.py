"""
The Hartford India — LinkedIn Competitive Intelligence Dashboard

Clean, executive-focused view. Shows only what matters:
  - Alert summary at a glance
  - One chart for engagement comparison
  - Compact intelligence cards (snapshot + action only)

Launch: python -m streamlit run app.py
"""

import sys
import os

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import streamlit as st
import plotly.express as px
import pandas as pd

from services.storage import (
    init_db,
    get_all_posts,
    get_company_baseline,
    get_stored_companies,
    get_post_count,
    get_analysis_for_post,
)

# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="The Hartford India — Competitive Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main .block-container {
        padding-top: 1rem;
        max-width: 1200px;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #8892b0 !important;
        font-size: 0.8rem !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #e6f1ff !important;
        font-size: 1.5rem !important;
    }

    /* Alert cards */
    .intel-card {
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 10px;
        border-left: 4px solid;
    }
    .intel-high {
        background: linear-gradient(135deg, #2d0a0a 0%, #3d1515 100%);
        border-left-color: #ff4444;
    }
    .intel-medium {
        background: linear-gradient(135deg, #2d2a0a 0%, #3d3515 100%);
        border-left-color: #ffbb33;
    }
    .intel-low {
        background: linear-gradient(135deg, #0a1a2d 0%, #15253d 100%);
        border-left-color: #4488ff;
    }
    .intel-card .company {
        font-size: 0.75rem;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .intel-card .snapshot {
        font-size: 0.95rem;
        color: #ccd6f6;
        margin: 6px 0;
        line-height: 1.4;
    }
    .intel-card .action {
        font-size: 0.85rem;
        color: #64ffda;
        margin-top: 6px;
    }
    .intel-card .meta {
        font-size: 0.75rem;
        color: #5a6e8a;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ── Init ─────────────────────────────────────────────────────────────────────

init_db()
companies = get_stored_companies()

if not companies:
    st.markdown("# 🏢 The Hartford India — LinkedIn Intelligence")
    st.info(
        "No data yet. Run:\n\n"
        "```\npython main.py --analyze --count 5\n```\n\n"
        "Then refresh this page."
    )
    st.stop()

# ── Load Data ────────────────────────────────────────────────────────────────

posts = get_all_posts()
analyses = {}
for p in posts:
    a = get_analysis_for_post(p.id)
    if a:
        analyses[p.id] = a

# ── Header ───────────────────────────────────────────────────────────────────

st.markdown("# 🏢 The Hartford India")
st.markdown("*Competitive intelligence vs. Vanguard · Chubb · HCA · Lloyds · Carelon*")

# ── Alert Summary Bar ────────────────────────────────────────────────────────

high_posts = [p for p in posts if analyses.get(p.id) and analyses[p.id].alert_tag == "HIGH PRIORITY"]
medium_posts = [p for p in posts if analyses.get(p.id) and analyses[p.id].alert_tag == "MEDIUM"]
low_posts = [p for p in posts if analyses.get(p.id) and analyses[p.id].alert_tag == "LOW"]

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🔴 Needs Action", len(high_posts))
with col2:
    st.metric("🟡 Watch", len(medium_posts))
with col3:
    st.metric("🟢 Routine", len(low_posts))
with col4:
    avg_eng = sum(p.engagement_score for p in posts) // len(posts) if posts else 0
    st.metric("Avg Engagement", f"{avg_eng:,}")

st.markdown("---")

# ── Engagement Comparison (single clean chart) ──────────────────────────────

st.markdown("### 📊 Engagement by Company")

df_data = []
for p in posts:
    df_data.append({
        "Company": p.company.replace(" India", "").replace(" Technology Centre", ""),
        "Engagement": p.engagement_score,
        "Date": p.timestamp,
        "Type": p.post_type,
    })

df = pd.DataFrame(df_data)

# Avg engagement per company
company_avg = df.groupby("Company")["Engagement"].mean().reset_index()
company_avg.columns = ["Company", "Avg Engagement"]
company_avg = company_avg.sort_values("Avg Engagement", ascending=True)

fig = px.bar(
    company_avg,
    x="Avg Engagement",
    y="Company",
    orientation="h",
    color="Avg Engagement",
    color_continuous_scale=["#1a1a2e", "#e94560"],
    text=company_avg["Avg Engagement"].round(0).astype(int),
)
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font_color="#8892b0",
    showlegend=False,
    coloraxis_showscale=False,
    height=220,
    margin=dict(l=0, r=20, t=5, b=5),
    xaxis=dict(showgrid=False, showticklabels=False),
    yaxis=dict(showgrid=False),
)
fig.update_traces(textposition="outside")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ── Intelligence Feed ────────────────────────────────────────────────────────

# Filter tabs
tab_all, tab_high, tab_medium = st.tabs(["📋 All", "🔴 Needs Action", "🟡 Watch List"])


def render_card(post, analysis):
    """Render a compact intelligence card."""
    tag = analysis.alert_tag if analysis else "LOW"

    if tag == "HIGH PRIORITY":
        css_class = "intel-high"
        emoji = "🔴"
    elif tag == "MEDIUM":
        css_class = "intel-medium"
        emoji = "🟡"
    else:
        css_class = "intel-low"
        emoji = "🔵"

    # Short company name
    short_company = post.company.replace(" India", "").replace(" Technology Centre", "")
    date_str = post.timestamp.strftime("%b %d") if post.timestamp else "?"
    classification = analysis.content_classification if analysis else "—"

    # Clean up snapshot text
    snapshot = (analysis.executive_snapshot or "").strip() if analysis else ""
    if not snapshot:
        snapshot = (post.text or "")[:120].replace("\n", " ") + "..."

    # Action text
    action = ""
    if analysis and analysis.recommended_action:
        action = analysis.recommended_action.strip()
        import re
        # Add space between numbered points (e.g., changing "1. Foo... 2. Bar..." into separate lines)
        action = re.sub(r'(?<!^)\s+(?=\d+\.\s)', '<br><br>', action)
        # Convert markdown bold to HTML bold since we use raw HTML in the card
        action = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', action)

    st.markdown(f"""
    <div class="intel-card {css_class}">
        <div class="company">{emoji} {short_company} · {date_str} · {classification} · Eng: {post.engagement_score:,}</div>
        <div class="snapshot">{snapshot}</div>
        {"<div class='action'>⚡ " + action + "</div>" if action else ""}
        <div class="meta">👍 {post.likes:,}  💬 {post.comments:,}  🔄 {post.shares:,}</div>
    </div>
    """, unsafe_allow_html=True)

    # Expandable detail (only if user wants to dig deeper)
    with st.expander("View details", expanded=False):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            if analysis:
                st.markdown(f"**Strategic Intent:** {analysis.strategic_intent}")
                st.markdown(f"**Competitive Insight:** {analysis.competitive_insight}")
                st.markdown(f"**Trend Signal:** {analysis.trend_signal}")
        with col_b:
            st.markdown(f"**Engagement Rate:** {post.engagement_rate:.2f}%")
            st.markdown(f"**Post Type:** {post.post_type}")
            if post.hashtags:
                st.markdown(f"**Hashtags:** #{' #'.join(post.hashtags[:4])}")
            if post.post_url:
                st.markdown(f"[🔗 View on LinkedIn]({post.post_url})")


# Sort: HIGH first, then MEDIUM, then LOW — within each group by engagement
def sort_key(post):
    a = analyses.get(post.id)
    order = {"HIGH PRIORITY": 0, "MEDIUM": 1, "LOW": 2}
    return (order.get(a.alert_tag if a else "LOW", 2), -post.engagement_score)

sorted_posts = sorted(posts, key=sort_key)

with tab_all:
    for post in sorted_posts:
        a = analyses.get(post.id)
        if a:
            render_card(post, a)

with tab_high:
    high = [p for p in sorted_posts if analyses.get(p.id) and analyses[p.id].alert_tag == "HIGH PRIORITY"]
    if high:
        for post in high:
            render_card(post, analyses[post.id])
    else:
        st.info("No high-priority alerts. All clear! ✅")

with tab_medium:
    med = [p for p in sorted_posts if analyses.get(p.id) and analyses[p.id].alert_tag == "MEDIUM"]
    if med:
        for post in med:
            render_card(post, analyses[post.id])
    else:
        st.info("No medium alerts.")

# ── Footer ───────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    f"<div style='text-align:center; color:#5a6e8a; font-size:0.75rem;'>"
    f"{len(posts)} posts · {len(analyses)} analyzed · {len(companies)} competitors"
    f"</div>",
    unsafe_allow_html=True,
)
