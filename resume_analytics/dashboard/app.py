"""
AI-Powered Resume Screening Analytics Dashboard
Built with Plotly Dash — runs locally on http://127.0.0.1:8050
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dash import Dash, html, dcc, Input, Output, State, dash_table, callback_context
from sql.database import get_connection, fetch_all, fetch_one, DB_PATH

# ──────────────────────────────────────────────
# DATA LAYER
# ──────────────────────────────────────────────

def load_data():
    conn = get_connection()

    candidates = pd.DataFrame(fetch_all("""
        SELECT c.*, COUNT(DISTINCT cs.skill_id) as skill_count
        FROM candidates c
        LEFT JOIN candidate_skills cs ON c.candidate_id = cs.candidate_id
        GROUP BY c.candidate_id
    """))

    match_scores = pd.DataFrame(fetch_all("""
        SELECT ms.*, c.name, c.current_role, c.years_experience, c.location,
               c.source, jd.title as job_title
        FROM match_scores ms
        JOIN candidates c ON ms.candidate_id = c.candidate_id
        JOIN job_descriptions jd ON ms.job_id = jd.job_id
    """))

    jobs = pd.DataFrame(fetch_all("SELECT * FROM job_descriptions"))
    skills = pd.DataFrame(fetch_all("SELECT * FROM v_job_skill_demand"))
    funnel = pd.DataFrame(fetch_all("SELECT * FROM v_hiring_funnel"))
    source_eff = pd.DataFrame(fetch_all("SELECT * FROM v_source_effectiveness"))
    skill_gap = pd.DataFrame(fetch_all("SELECT * FROM v_skill_gap_analysis"))
    summary = pd.DataFrame(fetch_all("SELECT * FROM v_candidate_summary"))

    conn.close()
    return {
        "candidates": candidates,
        "match_scores": match_scores,
        "jobs": jobs,
        "skills": skills,
        "funnel": funnel,
        "source_eff": source_eff,
        "skill_gap": skill_gap,
        "summary": summary,
    }


DATA = load_data()

# ──────────────────────────────────────────────
# COLOR PALETTE (Professional Analytics Theme)
# ──────────────────────────────────────────────

PALETTE = {
    "bg": "#f5f7fb",
    "card": "#ffffff",
    "border": "#e2e8f0",
    "accent": "#4f46e5",
    "accent2": "#0ea5e9",
    "accent3": "#f43f5e",
    "success": "#10b981",
    "warning": "#f59e0b",
    "text": "#0f172a",
    "muted": "#64748b",
}

CHART_TEMPLATE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#f1f5f9",
    font=dict(color=PALETTE["text"], family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    colorway=[PALETTE["accent"], PALETTE["accent2"], PALETTE["accent3"],
              PALETTE["success"], PALETTE["warning"], "#8b5cf6", "#ec4899"],
    xaxis=dict(gridcolor="#ffffff", zerolinecolor="#e2e8f0"),
    yaxis=dict(gridcolor="#ffffff", zerolinecolor="#e2e8f0"),
)


def card(children, style=None):
    base = {
        "background": PALETTE["card"],
        "border": f"1px solid {PALETTE['border']}",
        "borderRadius": "12px",
        "padding": "20px",
        "marginBottom": "16px",
    }
    if style:
        base.update(style)
    return html.Div(children, style=base)


def metric_card(label, value, subtitle="", color=None):
    return html.Div([
        html.Div(label, style={"fontSize": "11px", "color": PALETTE["muted"],
                               "letterSpacing": "1px", "textTransform": "uppercase", "marginBottom": "8px"}),
        html.Div(str(value), style={"fontSize": "32px", "fontWeight": "800",
                                    "color": color or PALETTE["accent"], "lineHeight": "1"}),
        html.Div(subtitle, style={"fontSize": "12px", "color": PALETTE["muted"], "marginTop": "4px"}),
    ], style={
        "background": PALETTE["card"],
        "border": f"1px solid {PALETTE['border']}",
        "borderRadius": "12px",
        "padding": "20px 24px",
        "flex": "1",
        "minWidth": "140px",
    })


# ──────────────────────────────────────────────
# CHART BUILDERS
# ──────────────────────────────────────────────

def build_score_distribution():
    ms = DATA["match_scores"]
    fig = px.histogram(
        ms, x="overall_score", nbins=20,
        color_discrete_sequence=[PALETTE["accent"]],
        labels={"overall_score": "Match Score", "count": "Candidates"},
        title="Score Distribution Across All Jobs",
    )
    fig.add_vline(x=72, line_dash="dash", line_color=PALETTE["success"],
                  annotation_text="Shortlist Threshold", annotation_font_color=PALETTE["success"])
    fig.add_vline(x=50, line_dash="dash", line_color=PALETTE["warning"],
                  annotation_text="Review Threshold", annotation_font_color=PALETTE["warning"])
    fig.update_layout(**CHART_TEMPLATE)
    return fig


def build_skill_heatmap(job_id=None):
    ms = DATA["match_scores"].copy()
    if job_id and job_id != "ALL":
        ms = ms[ms["job_id"] == job_id]

    top_cands = ms.groupby("candidate_id")["overall_score"].max().nlargest(10).index.tolist()
    ms_top = ms[ms["candidate_id"].isin(top_cands)]

    pivot = ms_top.pivot_table(index="name", columns="job_title", values="overall_score", aggfunc="first")

    fig = px.imshow(
        pivot,
        color_continuous_scale=[[0, "#f8fafc"], [0.5, "#c7d2fe"], [1, PALETTE["accent"]]],
        title="Match Score Heatmap — Top 10 Candidates × All Jobs",
        labels={"color": "Score"},
        aspect="auto",
    )
    fig.update_layout(**CHART_TEMPLATE)
    return fig


def build_hiring_funnel():
    funnel = DATA["funnel"].copy()
    order = ["Offer Extended", "Interview Scheduled", "Shortlisted", "Under Review", "Rejected"]
    funnel["status"] = pd.Categorical(funnel["status"], categories=order, ordered=True)
    funnel = funnel.sort_values("status")

    fig = go.Figure(go.Funnel(
        y=funnel["status"],
        x=funnel["count"],
        textinfo="value+percent total",
        marker=dict(color=[PALETTE["success"], PALETTE["accent2"], PALETTE["accent"],
                           PALETTE["warning"], PALETTE["accent3"]]),
    ))
    fig.update_layout(title="Hiring Pipeline Funnel", **CHART_TEMPLATE)
    return fig


def build_skill_gap(job_id=None):
    sg = DATA["skill_gap"].copy()
    if job_id and job_id != "ALL":
        sg = sg[sg["job_id"] == job_id]

    sg = sg.groupby("skill_name")["skill_coverage_pct"].mean().reset_index()
    sg = sg.sort_values("skill_coverage_pct")

    colors = [PALETTE["accent3"] if v < 40 else PALETTE["warning"] if v < 70 else PALETTE["success"]
              for v in sg["skill_coverage_pct"]]

    fig = go.Figure(go.Bar(
        x=sg["skill_coverage_pct"],
        y=sg["skill_name"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.0f}%" for v in sg["skill_coverage_pct"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="Skill Gap Analysis — % Candidates With Each Required Skill",
        xaxis_title="Candidate Coverage (%)",
        **CHART_TEMPLATE,
    )
    return fig


def build_source_effectiveness():
    se = DATA["source_eff"].copy()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=se["source"], y=se["total_applications"],
        name="Applications", marker_color=PALETTE["accent"],
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=se["source"], y=se["conversion_rate_pct"],
        name="Conversion Rate (%)", mode="lines+markers",
        marker=dict(color=PALETTE["accent2"], size=10),
        line=dict(color=PALETTE["accent2"], width=2),
    ), secondary_y=True)
    fig.update_layout(title="Source Effectiveness — Applications vs Conversion Rate", **CHART_TEMPLATE)
    fig.update_yaxes(title_text="Applications", secondary_y=False)
    fig.update_yaxes(title_text="Conversion Rate (%)", secondary_y=True)
    return fig


def build_exp_vs_score():
    ms = DATA["match_scores"].copy()
    best = ms.groupby("candidate_id").agg(
        best_score=("overall_score", "max"),
        recommendation=("recommendation", "first"),
    ).reset_index()
    merged = DATA["candidates"].merge(best, on="candidate_id")

    color_map = {
        "Shortlist": PALETTE["success"],
        "Review": PALETTE["warning"],
        "Reject": PALETTE["accent3"],
    }

    fig = px.scatter(
        merged,
        x="years_experience",
        y="best_score",
        color="recommendation",
        color_discrete_map=color_map,
        size="skill_count",
        hover_data=["name", "current_role", "location"],
        title="Experience vs. Match Score (bubble size = # skills)",
        labels={"years_experience": "Years of Experience", "best_score": "Best Match Score"},
    )
    fig.update_layout(**CHART_TEMPLATE)
    return fig


def build_skill_demand_bar():
    sk = DATA["skills"].head(15).sort_values("jobs_requiring")
    fig = go.Figure(go.Bar(
        x=sk["jobs_requiring"],
        y=sk["skill_name"],
        orientation="h",
        marker=dict(
            color=sk["jobs_requiring"],
            colorscale=[[0, PALETTE["accent"]], [1, PALETTE["accent2"]]],
            showscale=False,
        ),
        text=sk["jobs_requiring"],
        textposition="outside",
    ))
    fig.update_layout(title="Top Skills In Demand", xaxis_title="# Jobs Requiring", **CHART_TEMPLATE)
    return fig


def build_location_bar():
    loc = DATA["candidates"].groupby("location").agg(
        count=("candidate_id", "count"),
    ).reset_index().sort_values("count", ascending=True)

    fig = go.Figure(go.Bar(
        x=loc["count"], y=loc["location"],
        orientation="h",
        marker_color=PALETTE["accent"],
        text=loc["count"], textposition="outside",
    ))
    fig.update_layout(title="Candidates by Location", **CHART_TEMPLATE)
    return fig


# ──────────────────────────────────────────────
# CANDIDATE TABLE
# ──────────────────────────────────────────────

def get_candidate_table_data(job_id=None, min_score=0):
    ms = DATA["match_scores"].copy()
    if job_id and job_id != "ALL":
        ms = ms[ms["job_id"] == job_id]

    ms = ms[ms["overall_score"] >= min_score]
    best = ms.groupby("candidate_id").agg(
        best_score=("overall_score", "max"),
        best_job=("job_title", "first"),
        recommendation=("recommendation", "first"),
    ).reset_index()

    merged = DATA["candidates"].merge(best, on="candidate_id", how="left")
    merged["best_score"] = merged["best_score"].round(1)
    merged = merged.sort_values("best_score", ascending=False)

    cols = ["name", "current_role", "years_experience", "location",
            "source", "status", "skill_count", "best_score", "recommendation"]
    display = merged[cols].copy()
    display.columns = ["Name", "Role", "Exp (Yrs)", "Location",
                       "Source", "Status", "Skills", "Best Score", "Recommendation"]
    return display.to_dict("records")


# ──────────────────────────────────────────────
# APP LAYOUT
# ──────────────────────────────────────────────

app = Dash(__name__, title="Resume Analytics Dashboard")
app.config.suppress_callback_exceptions = True

job_options = [{"label": "All Jobs", "value": "ALL"}] + [
    {"label": row["title"], "value": row["job_id"]}
    for _, row in DATA["jobs"].iterrows()
]

app.layout = html.Div([
    # ── Header ──
    html.Div([
        html.Div([
            html.Div("⬡", style={"fontSize": "28px", "color": PALETTE["accent"], "marginRight": "12px"}),
            html.Div([
                html.H1("Resume Screening Analytics",
                        style={"margin": "0", "fontSize": "22px", "fontWeight": "800", "color": PALETTE["text"]}),
                html.Div("AI-Powered Candidate Intelligence Platform",
                         style={"fontSize": "12px", "color": PALETTE["muted"]}),
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div([
            html.Span("LIVE", style={
                "background": PALETTE["success"], "color": "#000",
                "padding": "3px 10px", "borderRadius": "20px",
                "fontSize": "11px", "fontWeight": "700", "marginRight": "12px",
            }),
            html.Span(f"{len(DATA['candidates'])} Candidates · {len(DATA['jobs'])} Jobs",
                      style={"color": PALETTE["muted"], "fontSize": "13px"}),
        ], style={"display": "flex", "alignItems": "center"}),
    ], style={
        "background": PALETTE["card"],
        "borderBottom": f"1px solid {PALETTE['border']}",
        "padding": "16px 32px",
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "position": "sticky", "top": "0", "zIndex": "100",
    }),

    # ── Body ──
    html.Div([

        # ── Tabs ──
        dcc.Tabs(id="tabs", value="overview", children=[
            dcc.Tab(label="📊 Overview", value="overview"),
            dcc.Tab(label="🎯 Job Matching", value="matching"),
            dcc.Tab(label="📉 Skill Gap", value="skillgap"),
            dcc.Tab(label="👥 Candidates", value="candidates"),
            dcc.Tab(label="📈 Hiring Analytics", value="hiring"),
        ], style={"marginBottom": "24px"},
        colors={"border": PALETTE["border"], "primary": PALETTE["accent"], "background": PALETTE["card"]}),

        html.Div(id="tab-content"),

    ], style={"maxWidth": "1400px", "margin": "0 auto", "padding": "24px 32px"}),

], style={"background": PALETTE["bg"], "minHeight": "100vh", "fontFamily": "Inter, sans-serif", "color": PALETTE["text"]})


# ──────────────────────────────────────────────
# CALLBACKS
# ──────────────────────────────────────────────

@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab):

    # ── OVERVIEW ──────────────────────────────
    if tab == "overview":
        ms = DATA["match_scores"]
        shortlist_pct = round(len(DATA["funnel"][DATA["funnel"]["status"].isin(["Shortlisted","Interview Scheduled","Offer Extended"])]) / len(DATA["candidates"]) * 100, 1) if len(DATA["candidates"]) else 0
        avg_score = round(ms["overall_score"].mean(), 1)
        top_skill = DATA["skills"].iloc[0]["skill_name"] if len(DATA["skills"]) else "—"
        avg_exp = round(DATA["candidates"]["years_experience"].mean(), 1) if len(DATA["candidates"]) else 0

        return html.Div([
            # KPI row
            html.Div([
                metric_card("Total Candidates", len(DATA["candidates"]), "in pipeline"),
                metric_card("Open Positions", len(DATA["jobs"]), "active jobs", PALETTE["accent2"]),
                metric_card("Avg Match Score", f"{avg_score}%", "across all pairs", PALETTE["warning"]),
                metric_card("Avg Experience", f"{avg_exp} Yrs", "across candidates", "#8b5cf6"),
                metric_card("Skills Tracked", len(fetch_all("SELECT * FROM skills")), "in taxonomy", PALETTE["success"]),
                metric_card("Most Demanded Skill", top_skill, "across all JDs", "#ec4899"),
            ], style={"display": "flex", "gap": "16px", "marginBottom": "24px", "flexWrap": "wrap"}),

            # Charts row 1
            html.Div([
                card([dcc.Graph(figure=build_score_distribution(), config={"displayModeBar": False})],
                     style={"flex": "2"}),
                card([dcc.Graph(figure=build_hiring_funnel(), config={"displayModeBar": False})],
                     style={"flex": "1"}),
            ], style={"display": "flex", "gap": "16px"}),

            # Charts row 2
            html.Div([
                card([dcc.Graph(figure=build_skill_demand_bar(), config={"displayModeBar": False})],
                     style={"flex": "1"}),
                card([dcc.Graph(figure=build_location_bar(), config={"displayModeBar": False})],
                     style={"flex": "1"}),
            ], style={"display": "flex", "gap": "16px"}),
        ])

    # ── JOB MATCHING ──────────────────────────
    elif tab == "matching":
        return html.Div([
            card([
                html.Div("Filter by Job", style={"fontWeight": "700", "marginBottom": "10px"}),
                dcc.Dropdown(
                    id="job-filter",
                    options=job_options,
                    value="ALL",
                    style={"background": PALETTE["bg"], "color": "#000", "border": f"1px solid {PALETTE['border']}"},
                ),
            ]),
            card([dcc.Graph(id="heatmap-chart", config={"displayModeBar": False})]),
            card([dcc.Graph(figure=build_exp_vs_score(), config={"displayModeBar": False})]),
        ])

    # ── SKILL GAP ─────────────────────────────
    elif tab == "skillgap":
        return html.Div([
            card([
                html.Div("Filter by Job Position", style={"fontWeight": "700", "marginBottom": "10px"}),
                dcc.Dropdown(
                    id="job-filter-gap",
                    options=job_options,
                    value="ALL",
                    style={"background": PALETTE["bg"], "color": "#000"},
                ),
            ]),
            card([dcc.Graph(id="skill-gap-chart", config={"displayModeBar": False})]),
            card([
                html.Div("Skill Demand Intelligence", style={"fontWeight": "700", "fontSize": "16px", "marginBottom": "16px"}),
                html.Div([
                    html.Div([
                        html.Div("🔴 Critical Gap", style={"fontWeight": "600", "color": PALETTE["accent3"]}),
                        html.Div("< 40% of candidates have this skill", style={"color": PALETTE["muted"], "fontSize": "12px"}),
                        html.Div("→ Widen search criteria or upskill internally", style={"color": PALETTE["muted"], "fontSize": "12px", "marginTop": "4px"}),
                    ], style={"flex": "1", "background": "#fff1f2", "border": "1px solid #ffe4e6", "borderRadius": "8px", "padding": "16px"}),
                    html.Div([
                        html.Div("🟡 Moderate Gap", style={"fontWeight": "600", "color": PALETTE["warning"]}),
                        html.Div("40–70% coverage", style={"color": PALETTE["muted"], "fontSize": "12px"}),
                        html.Div("→ Prioritize candidates with this skill", style={"color": PALETTE["muted"], "fontSize": "12px", "marginTop": "4px"}),
                    ], style={"flex": "1", "background": "#fef3c7", "border": "1px solid #fde68a", "borderRadius": "8px", "padding": "16px"}),
                    html.Div([
                        html.Div("🟢 Adequate Supply", style={"fontWeight": "600", "color": PALETTE["success"]}),
                        html.Div("> 70% coverage", style={"color": PALETTE["muted"], "fontSize": "12px"}),
                        html.Div("→ Use as differentiator, not filter", style={"color": PALETTE["muted"], "fontSize": "12px", "marginTop": "4px"}),
                    ], style={"flex": "1", "background": "#ecfdf5", "border": "1px solid #a7f3d0", "borderRadius": "8px", "padding": "16px"}),
                ], style={"display": "flex", "gap": "16px"}),
            ]),
        ])

    # ── CANDIDATES ────────────────────────────
    elif tab == "candidates":
        return html.Div([
            card([
                html.Div([
                    html.Div([
                        html.Div("Job Position Filter", style={"fontWeight": "600", "marginBottom": "6px", "fontSize": "12px", "color": PALETTE["muted"]}),
                        dcc.Dropdown(id="cand-job-filter", options=job_options, value="ALL",
                                     style={"minWidth": "250px", "color": "#000"}),
                    ]),
                    html.Div([
                        html.Div("Min Score", style={"fontWeight": "600", "marginBottom": "6px", "fontSize": "12px", "color": PALETTE["muted"]}),
                        dcc.Slider(id="min-score-slider", min=0, max=100, step=5, value=0,
                                   marks={0: "0", 25: "25", 50: "50", 75: "75", 100: "100"},
                                   tooltip={"placement": "bottom"}),
                    ], style={"flex": "1", "minWidth": "200px"}),
                ], style={"display": "flex", "gap": "24px", "alignItems": "flex-end", "flexWrap": "wrap"}),
            ]),
            
            html.Div([
                # Left: Candidates Table
                html.Div([
                    card([
                        html.Div(id="candidate-count", style={"fontWeight": "700", "fontSize": "15px", "marginBottom": "12px", "color": PALETTE["text"]}),
                        dash_table.DataTable(
                            id="candidate-table",
                            columns=[{"name": c, "id": c} for c in
                                     ["Name", "Role", "Exp (Yrs)", "Location", "Source", "Status", "Skills", "Best Score", "Recommendation"]],
                            data=get_candidate_table_data(),
                            style_table={"overflowX": "auto"},
                            style_header={
                                "background": "#f8fafc",
                                "color": PALETTE["text"],
                                "fontWeight": "700",
                                "fontSize": "12px",
                                "borderBottom": f"2px solid {PALETTE['border']}",
                                "textTransform": "uppercase",
                                "letterSpacing": "0.5px",
                            },
                            style_cell={
                                "background": PALETTE["card"],
                                "color": PALETTE["text"],
                                "border": f"1px solid {PALETTE['border']}",
                                "padding": "10px 12px",
                                "fontSize": "13px",
                                "textAlign": "left",
                                "fontFamily": "Inter, sans-serif",
                            },
                            style_data_conditional=[
                                {"if": {"filter_query": '{Recommendation} = "Shortlist"'},
                                 "color": PALETTE["success"], "fontWeight": "700"},
                                {"if": {"filter_query": '{Recommendation} = "Reject"'},
                                 "color": PALETTE["accent3"]},
                                {"if": {"filter_query": '{Recommendation} = "Review"'},
                                 "color": PALETTE["warning"]},
                                {"if": {"row_index": "odd"}, "background": "#f8fafc"},
                                {"if": {"state": "selected"}, "background": "#e0e7ff", "color": PALETTE["accent"], "fontWeight": "700"},
                            ],
                            sort_action="native",
                            filter_action="native",
                            page_size=10,
                            row_selectable="single",
                            selected_rows=[0],
                        ),
                    ]),
                ], style={"flex": "3", "minWidth": "600px"}),
                
                # Right: Candidates Detail Panel
                html.Div(id="candidate-detail-panel", style={"flex": "2", "minWidth": "400px"})
            ], style={"display": "flex", "gap": "20px", "flexWrap": "wrap"}),
        ])

    # ── HIRING ANALYTICS ──────────────────────
    elif tab == "hiring":
        return html.Div([
            html.Div([
                card([dcc.Graph(figure=build_source_effectiveness(), config={"displayModeBar": False})],
                     style={"flex": "1"}),
                card([dcc.Graph(figure=px.pie(
                    DATA["funnel"], values="count", names="status",
                    color_discrete_sequence=[PALETTE["success"], PALETTE["accent2"],
                                            PALETTE["accent"], PALETTE["warning"], PALETTE["accent3"]],
                    title="Candidate Status Breakdown",
                ).update_layout(**CHART_TEMPLATE), config={"displayModeBar": False})], style={"flex": "1"}),
            ], style={"display": "flex", "gap": "16px"}),
            card([
                html.Div("Automated Screening Impact", style={"fontWeight": "700", "fontSize": "16px", "marginBottom": "16px"}),
                html.Div([
                    html.Div([
                        html.Div("60%", style={"fontSize": "48px", "fontWeight": "900", "color": PALETTE["accent"], "lineHeight": "1"}),
                        html.Div("Reduction in manual review effort",
                                 style={"fontSize": "14px", "color": PALETTE["muted"], "marginTop": "4px"}),
                    ], style={"flex": "1", "textAlign": "center", "padding": "20px"}),
                    html.Div([
                        html.Div(f"{len(DATA['candidates'])}",
                                 style={"fontSize": "48px", "fontWeight": "900", "color": PALETTE["accent2"], "lineHeight": "1"}),
                        html.Div("Resumes processed automatically",
                                 style={"fontSize": "14px", "color": PALETTE["muted"], "marginTop": "4px"}),
                    ], style={"flex": "1", "textAlign": "center", "padding": "20px"}),
                    html.Div([
                        html.Div("100", style={"fontSize": "48px", "fontWeight": "900", "color": PALETTE["success"], "lineHeight": "1"}),
                        html.Div("Job-resume pairs scored in seconds",
                                 style={"fontSize": "14px", "color": PALETTE["muted"], "marginTop": "4px"}),
                    ], style={"flex": "1", "textAlign": "center", "padding": "20px"}),
                    html.Div([
                        html.Div("77", style={"fontSize": "48px", "fontWeight": "900", "color": "#c77dff", "lineHeight": "1"}),
                        html.Div("Skills in extraction taxonomy",
                                 style={"fontSize": "14px", "color": PALETTE["muted"], "marginTop": "4px"}),
                    ], style={"flex": "1", "textAlign": "center", "padding": "20px"}),
                ], style={"display": "flex", "gap": "0", "flexWrap": "wrap"}),
            ]),
        ])

    return html.Div("Select a tab")


@app.callback(Output("heatmap-chart", "figure"), Input("job-filter", "value"))
def update_heatmap(job_id):
    return build_skill_heatmap(job_id)


@app.callback(Output("skill-gap-chart", "figure"), Input("job-filter-gap", "value"))
def update_skill_gap(job_id):
    return build_skill_gap(job_id)


@app.callback(
    Output("candidate-table", "data"),
    Output("candidate-count", "children"),
    Input("cand-job-filter", "value"),
    Input("min-score-slider", "value"),
)
def update_candidate_table(job_id, min_score):
    data = get_candidate_table_data(job_id, min_score or 0)
    return data, f"Showing {len(data)} candidates"


@app.callback(
    Output("candidate-detail-panel", "children"),
    Input("candidate-table", "selected_rows"),
    State("candidate-table", "data"),
)
def update_candidate_details(selected_rows, table_data):
    if not table_data:
        return card([
            html.Div("No Candidates Available", style={"fontWeight": "700", "fontSize": "16px", "color": PALETTE["text"]})
        ])
        
    idx = 0
    if selected_rows and len(selected_rows) > 0:
        idx = selected_rows[0]
    
    if idx >= len(table_data):
        idx = 0
        
    candidate_name = table_data[idx]["Name"]
    
    # Query details
    conn = get_connection()
    cand = fetch_one("SELECT * FROM candidates WHERE name = ?", (candidate_name,))
    if not cand:
        conn.close()
        return card([html.Div("Candidate details not found.")])
        
    candidate_id = cand["candidate_id"]
    
    # Query relations
    work = fetch_all("SELECT * FROM work_experience WHERE candidate_id = ? ORDER BY start_date DESC", (candidate_id,))
    projects = fetch_all("SELECT * FROM projects WHERE candidate_id = ?", (candidate_id,))
    certs = fetch_all("SELECT * FROM certifications WHERE candidate_id = ?", (candidate_id,))
    
    # Query match scores
    scores = fetch_all("""
        SELECT ms.*, jd.title as job_title, jd.min_experience
        FROM match_scores ms
        JOIN job_descriptions jd ON ms.job_id = jd.job_id
        WHERE ms.candidate_id = ?
        ORDER BY ms.overall_score DESC
    """, (candidate_id,))
    
    conn.close()
    
    # Certs formatting
    certs_list = [c["cert_name"] for c in certs]
    certs_str = ", ".join(certs_list) if certs_list else "None listed"
    
    # Render score breakdown cards for jobs
    matching_nodes = []
    for s in scores:
        matched_skills = json.loads(s["matched_skills"]) if s["matched_skills"] else []
        missing_skills = json.loads(s["missing_skills"]) if s["missing_skills"] else []
        
        # Skill badges
        matched_badges = [
            html.Span(skill, style={
                "background": "#ecfdf5", "color": PALETTE["success"],
                "padding": "3px 8px", "borderRadius": "4px", "fontSize": "11px",
                "fontWeight": "600", "marginRight": "4px", "marginBottom": "4px",
                "display": "inline-block"
            }) for skill in matched_skills
        ]
        
        missing_badges = [
            html.Span(skill, style={
                "background": "#fff1f2", "color": PALETTE["accent3"],
                "padding": "3px 8px", "borderRadius": "4px", "fontSize": "11px",
                "fontWeight": "600", "marginRight": "4px", "marginBottom": "4px",
                "display": "inline-block"
            }) for skill in missing_skills
        ]
        
        score_color = PALETTE["success"] if s["overall_score"] >= 72 else PALETTE["warning"] if s["overall_score"] >= 50 else PALETTE["accent3"]
        
        matching_nodes.append(html.Div([
            html.Div([
                html.Div(s["job_title"], style={"fontWeight": "700", "fontSize": "13px"}),
                html.Div(f"Score: {s['overall_score']}% ({s['recommendation']})", 
                         style={"fontWeight": "800", "color": score_color, "fontSize": "12px"})
            ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "6px"}),
            
            html.Div([
                html.Span("Matched Skills: ", style={"fontWeight": "600", "fontSize": "11px", "color": PALETTE["muted"]}),
                html.Div(matched_badges if matched_badges else "None", style={"marginTop": "2px"})
            ], style={"marginBottom": "4px"}),
            
            html.Div([
                html.Span("Missing Skills: ", style={"fontWeight": "600", "fontSize": "11px", "color": PALETTE["muted"]}),
                html.Div(missing_badges if missing_badges else "None", style={"marginTop": "2px"})
            ], style={"marginBottom": "8px"}),
            
            html.Hr(style={"border": "none", "borderTop": f"1px solid {PALETTE['border']}", "margin": "8px 0"})
        ]))

    # Work Timeline
    work_nodes = []
    for w in work:
        work_nodes.append(html.Div([
            html.Div([
                html.Div(w["title"], style={"fontWeight": "700", "fontSize": "13px"}),
                html.Div(f"{w['start_date']} - {w['end_date']}", style={"fontSize": "11px", "color": PALETTE["muted"]})
            ], style={"display": "flex", "justifyContent": "space-between"}),
            html.Div(w["company"], style={"fontSize": "12px", "fontWeight": "500", "color": PALETTE["accent"]}),
            html.Div(w["description"], style={"fontSize": "11.5px", "color": PALETTE["muted"], "marginTop": "4px", "lineHeight": "1.3"}),
            html.Div(style={"height": "10px"})
        ]))

    # Projects
    project_nodes = []
    for p in projects:
        skills_used = json.loads(p["skills_used"]) if p["skills_used"] else []
        proj_badges = [
            html.Span(skill, style={
                "background": "#f1f5f9", "color": "#475569",
                "padding": "2px 6px", "borderRadius": "3px", "fontSize": "10px",
                "marginRight": "4px", "display": "inline-block"
            }) for skill in skills_used
        ]
        project_nodes.append(html.Div([
            html.Div(p["project_name"], style={"fontWeight": "700", "fontSize": "13px"}),
            html.Div(f"Impact: {p['impact']}", style={"fontSize": "12px", "color": PALETTE["success"], "fontWeight": "600"}),
            html.Div(proj_badges, style={"marginTop": "4px", "marginBottom": "8px"})
        ]))

    return card([
        # Name and basic metadata
        html.Div([
            html.Div(cand["name"], style={"fontSize": "20px", "fontWeight": "800", "color": PALETTE["text"]}),
            html.Div(f"{cand['current_role']} · {cand['years_experience']} Years Exp", 
                     style={"fontSize": "13px", "fontWeight": "600", "color": PALETTE["accent"], "marginTop": "2px"}),
            html.Div(f"📍 {cand['location']}  |  📧 {cand['email']}  |  📞 {cand['phone']}", 
                     style={"fontSize": "11px", "color": PALETTE["muted"], "marginTop": "4px"}),
            html.Div(f"Source: {cand['source']}  |  Status: {cand['status']}", 
                     style={"fontSize": "11px", "color": PALETTE["muted"]}),
        ], style={"borderBottom": f"1px solid {PALETTE['border']}", "paddingBottom": "12px", "marginBottom": "12px"}),
        
        # Details container
        html.Div([
            # Education
            html.Div([
                html.Div("🎓 Education", style={"fontWeight": "700", "fontSize": "14px", "color": PALETTE["text"], "marginBottom": "6px"}),
                html.Div([
                    html.Div(f"{cand['education_degree']} in {cand['education_field']}", style={"fontWeight": "600", "fontSize": "12.5px"}),
                    html.Div(f"{cand['education_university']} ({cand['graduation_year']}) · GPA: {cand['gpa']}", 
                             style={"fontSize": "11.5px", "color": PALETTE["muted"]})
                ])
            ], style={"marginBottom": "12px"}),
            
            # Certifications
            html.Div([
                html.Div("📜 Certifications", style={"fontWeight": "700", "fontSize": "14px", "color": PALETTE["text"], "marginBottom": "4px"}),
                html.Div(certs_str, style={"fontSize": "11.5px", "color": PALETTE["muted"]})
            ], style={"marginBottom": "12px"}),
            
            # Match scores per job position
            html.Div([
                html.Div("🎯 Custom Job Match Analysis", style={"fontWeight": "700", "fontSize": "14px", "color": PALETTE["text"], "marginBottom": "8px"}),
                html.Div(matching_nodes)
            ], style={"marginBottom": "12px"}),
            
            # Work Experience
            html.Div([
                html.Div("💼 Detailed Work History", style={"fontWeight": "700", "fontSize": "14px", "color": PALETTE["text"], "marginBottom": "8px"}),
                html.Div(work_nodes)
            ], style={"marginBottom": "12px"}),
            
            # Projects
            html.Div([
                html.Div("🚀 Highlighted Projects", style={"fontWeight": "700", "fontSize": "14px", "color": PALETTE["text"], "marginBottom": "8px"}),
                html.Div(project_nodes)
            ])
            
        ], style={"maxHeight": "500px", "overflowY": "auto", "paddingRight": "6px"})
    ], style={"padding": "24px", "border": f"1px solid {PALETTE['border']}", "background": PALETTE["card"], "borderRadius": "12px"})


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n[DASHBOARD] Starting Resume Analytics Dashboard...")
    print("[DASHBOARD] Open http://127.0.0.1:8050 in your browser\n")
    app.run(debug=True, port=8050)
