
import pandas as pd
import plotly.express as px
import streamlit as st

from utils.databricks import ALLOWED_TABLES, run_query


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="IPL Pavilion",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#123B7A"
BLUE = "#174EA6"
ORANGE = "#F97316"
PURPLE = "#7928A1"
BLACK = "#111827"
MUTED = "#64748B"
BORDER = "#E2E8F0"
WHITE = "#FFFFFF"


# =========================================================
# STYLING
# =========================================================

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {{
        font-family: Inter, Arial, sans-serif;
    }}

    .stApp {{
        background: {WHITE};
        color: {BLACK};
    }}

    [data-testid="stHeader"] {{
        background: {NAVY};
        height: 12px;
    }}

    [data-testid="stSidebar"] {{
        background: #F7F9FC;
        border-right: 1px solid {BORDER};
    }}

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
        color: {MUTED};
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label {{
        color: {BLACK} !important;
        font-weight: 500;
    }}

    h1, h2, h3, h4 {{
        color: {NAVY} !important;
        font-weight: 750 !important;
        letter-spacing: -0.5px;
    }}

    p, label, li {{
        color: {BLACK};
    }}

    [data-testid="stMetric"] {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: 0 3px 12px rgba(18, 59, 122, 0.04);
    }}

    [data-testid="stMetricLabel"] {{
        color: {MUTED} !important;
        font-size: 13px;
    }}

    [data-testid="stMetricValue"] {{
        color: {NAVY} !important;
        font-weight: 750;
    }}

    div.stButton > button,
    div.stDownloadButton > button {{
        border-radius: 8px;
        border: 1px solid {BLUE};
        font-weight: 600;
        background: {WHITE};
        color: {BLUE};
    }}

    div.stButton > button[kind="primary"] {{
        background: {BLUE};
        color: {WHITE};
    }}

    div.stButton > button[kind="primary"]:hover {{
        background: {NAVY};
        color: {WHITE};
    }}

    [data-testid="stDataFrame"] {{
        border: 1px solid {BORDER};
        border-radius: 10px;
        overflow: hidden;
    }}

    hr {{
        border-color: {BORDER};
    }}

    .brand-title {{
        color: {NAVY};
        font-size: 27px;
        font-weight: 800;
        letter-spacing: -0.8px;
        line-height: 1.2;
    }}

    .brand-subtitle {{
        color: {MUTED};
        font-size: 12px;
        letter-spacing: 2.4px;
        font-weight: 700;
        margin-top: 7px;
    }}

    .eyebrow {{
        color: {MUTED};
        font-size: 11px;
        letter-spacing: 2px;
        font-weight: 700;
    }}

    .chart-card {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
    }}

    .cap-heading {{
        font-size: 23px;
        line-height: 1.25;
        font-weight: 800;
        margin-bottom: 5px;
    }}

    .cap-subheading {{
        font-size: 14px;
        color: {BLACK};
        font-weight: 500;
    }}

    .footer-text {{
        color: {MUTED};
        font-size: 12px;
    }}

    #MainMenu, footer {{
        visibility: hidden;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATA HELPERS
# =========================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_table(table_name: str) -> pd.DataFrame:
    """Load data from an approved Databricks Gold table."""
    if table_name not in ALLOWED_TABLES:
        raise ValueError("Table is not in the approved list.")

    return run_query(f"SELECT * FROM {table_name} LIMIT 5000")




@st.cache_data(ttl=300, show_spinner=False)
def load_top_individual_scores() -> pd.DataFrame:
    """Five highest individual innings, ranked by the actual innings score."""
    return run_query("""
        SELECT match_id, season, match_date, venue, inning, batsman,
               batting_team, bowling_team, runs, balls_faced,
               fours, sixes, strike_rate
        FROM ipl_analytics.gold.individual_batting_scores
        WHERE batsman IS NOT NULL
        ORDER BY runs DESC, balls_faced ASC, match_date DESC, match_id DESC
        LIMIT 5
    """)


@st.cache_data(ttl=300, show_spinner=False)
def load_individual_score_player_names() -> list:
    """Names from the complete table, not only the first 5,000 score rows."""
    result = run_query("""
        SELECT DISTINCT TRIM(batsman) AS batsman
        FROM ipl_analytics.gold.individual_batting_scores
        WHERE batsman IS NOT NULL AND TRIM(batsman) <> ''
        ORDER BY batsman
    """)
    if result.empty or "batsman" not in result.columns:
        return []
    return result["batsman"].dropna().astype(str).tolist()


def sql_string_literal(value: str) -> str:
    """Escape a user-selected player name before inserting it as a SQL literal."""
    return "'" + value.replace("'", "''") + "'"


@st.cache_data(ttl=180, show_spinner=False)
def load_individual_innings(player_name: str) -> pd.DataFrame:
    player_literal = sql_string_literal(player_name.strip())
    return run_query(f"""
        SELECT match_id, season, match_date, venue, inning, batsman,
               batting_team, bowling_team, runs, balls_faced,
               fours, sixes, strike_rate
        FROM ipl_analytics.gold.individual_batting_scores
        WHERE LOWER(TRIM(batsman)) = LOWER(TRIM({player_literal}))
        ORDER BY match_date DESC, match_id DESC, inning
    """)


def find_column(df, keywords):
    """Detect a column by common names."""
    if df.empty:
        return None

    lower_columns = {col: str(col).lower().strip() for col in df.columns}

    # Prefer exact matches first.
    for keyword in keywords:
        for col, lowered in lower_columns.items():
            if lowered == keyword.lower():
                return col

    # Then look for partial matches.
    for keyword in keywords:
        for col, lowered in lower_columns.items():
            if keyword.lower() in lowered:
                return col

    return None


def get_numeric_columns(df):
    result = []

    for col in df.columns:
        values = pd.to_numeric(df[col], errors="coerce")
        if values.notna().any():
            result.append(col)

    return result


def numeric_df(df, column):
    result = df.copy()
    result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.dropna(subset=[column])


def format_value(value):
    if value is None:
        return "—"

    try:
        number = float(value)

        if pd.isna(number):
            return "—"

        return f"{number:,.0f}" if number.is_integer() else f"{number:,.2f}"

    except (ValueError, TypeError):
        return str(value)


def apply_filters(df, key_prefix):
    """Optional sidebar filters for season, team and venue."""
    result = df.copy()

    definitions = [
        ("Season", ["season", "year"]),
        ("Team", ["batting_team", "bowling_team", "team", "franchise"]),
        ("Venue", ["venue", "stadium", "ground"]),
    ]

    for label, keywords in definitions:
        col = find_column(result, keywords)

        if col is None:
            continue

        values = sorted(result[col].dropna().astype(str).unique().tolist())

        if not values or len(values) > 250:
            continue

        selected = st.sidebar.multiselect(
            label,
            options=values,
            default=[],
            key=f"{key_prefix}_{label}",
            placeholder=f"All {label.lower()}s",
        )

        if selected:
            result = result[result[col].astype(str).isin(selected)]

    return result


# =========================================================
# CHART HELPERS
# =========================================================

def style_chart(fig, height=390):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor=WHITE,
        plot_bgcolor=WHITE,
        font=dict(
            family="Inter, Arial, sans-serif",
            color=BLACK,
            size=12,
        ),
        margin=dict(l=12, r=35, t=45, b=30),
        showlegend=False,
        height=height,
        bargap=0.28,
    )

    fig.update_xaxes(
        showgrid=True,
        gridcolor="#E8EDF5",
        zeroline=False,
        linecolor=BORDER,
        tickfont=dict(color=BLACK),
        title_font=dict(color=BLACK),
    )

    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        linecolor=BORDER,
        tickfont=dict(color=BLACK),
        title_font=dict(color=BLACK),
    )

    return fig


def render_bar_chart(df, category, metric, title, color=BLUE):
    chart_df = numeric_df(df, metric)

    if chart_df.empty:
        st.info("No numeric data is available for this chart.")
        return

    chart_df = (
        chart_df.groupby(category, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=True)
        .tail(10)
    )

    fig = px.bar(
        chart_df,
        x=metric,
        y=category,
        orientation="h",
        text=metric,
        title=title,
        color_discrete_sequence=[color],
    )

    fig.update_traces(
        texttemplate="%{x:,.0f}",
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
    )

    style_chart(fig)
    st.plotly_chart(fig, use_container_width=True)


def render_cap_chart(
    df, player_col, metric_col, title, subtitle, color, icon
):
    st.markdown('<div class="chart-card">', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:14px;
                    padding:8px 8px 12px 8px;">
            <div style="font-size:44px; line-height:1;">{icon}</div>
            <div>
                <div class="cap-heading" style="color:{color};">
                    {title}
                </div>
                <div class="cap-subheading">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if df.empty or player_col is None or metric_col is None:
        st.info("Required player or metric columns were not detected.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    chart_df = numeric_df(df, metric_col)
    chart_df[player_col] = chart_df[player_col].astype(str)

    chart_df = (
        chart_df.groupby(player_col, as_index=False)[metric_col]
        .max()
        .sort_values(metric_col, ascending=False)
        .head(10)
        .sort_values(metric_col, ascending=True)
    )

    if chart_df.empty:
        st.info("No data available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    fig = px.bar(
        chart_df,
        x=metric_col,
        y=player_col,
        orientation="h",
        text=metric_col,
        color_discrete_sequence=[color],
    )

    fig.update_traces(
        texttemplate="%{x:,.0f}",
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
        hovertemplate="%{y}<br>%{x:,.0f}<extra></extra>",
    )

    style_chart(fig, height=410)

    fig.update_layout(
        margin=dict(l=8, r=35, t=10, b=35),
    )

    fig.update_xaxes(
        title=metric_col.replace("_", " ").title()
    )

    fig.update_yaxes(
        title="",
        categoryorder="array",
        categoryarray=chart_df[player_col].tolist(),
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# TABLE DISPLAY / DOWNLOAD
# =========================================================

def display_dataframe(df, table_name, key_suffix=""):
    st.caption(
        f"`{table_name}` · {len(df):,} displayed rows"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{table_name.split('.')[-1]}.csv",
        mime="text/csv",
        key=f"download_{table_name}_{key_suffix}",
    )


def show_table(table_name, use_filters=True):
    try:
        with st.spinner("Fetching data from Databricks..."):
            df = load_table(table_name)

        if df.empty:
            st.info("This table returned no rows.")
            return df

        if use_filters:
            df = apply_filters(df, table_name)

        display_dataframe(df, table_name)
        return df

    except Exception as exc:
        st.error("Unable to load this table.")
        st.code(str(exc))
        return pd.DataFrame()


# =========================================================
# SEARCH HELPERS
# =========================================================

def searchable_player_select(
    df,
    column,
    label,
    all_label,
    key,
):
    """
    Streamlit selectbox supports typing to search existing options.
    Names come from the actual loaded table.
    """
    if column is None:
        st.warning(
            f"Could not detect the column for {label.lower()}. "
            f"Available columns: {', '.join(map(str, df.columns))}"
        )
        return None

    names = sorted(
        df[column]
        .dropna()
        .astype(str)
        .str.strip()
        .loc[lambda s: s.ne("")]
        .unique()
        .tolist(),
        key=str.casefold,
    )

    if not names:
        st.info(f"No {label.lower()} names were found in this table.")
        return None

    return st.selectbox(
        label,
        options=[all_label] + names,
        index=0,
        key=key,
        help="Click here and type the first letters of the name to search.",
    )


# =========================================================
# SIDEBAR
# =========================================================

# Show the bundled IPL-style logo above the Pavilion branding.
# Keep a text fallback if the logo asset is missing.
from pathlib import Path

_LOGO_PATH = Path(__file__).parent / "assets" / "ipl_logo.svg"
if _LOGO_PATH.exists():
    st.sidebar.image(str(_LOGO_PATH), use_container_width=True)
else:
    st.sidebar.markdown('<div style="font-size:42px; text-align:center;">🏏 IPL</div>', unsafe_allow_html=True)

st.sidebar.markdown(
    """
    <div style="padding:8px 0 26px 0;">
        <div class="brand-title">IPL PAVILION</div>
        <div class="brand-subtitle">CRICKET ANALYTICS</div>
    </div>
    """,
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Overview",
        "Batting Analytics",
        "Bowling Analytics",
        "Team & Venue",
        "Gold Layer Explorer",
    ],
)

st.sidebar.divider()
st.sidebar.markdown("**DATA SOURCE**")
st.sidebar.markdown("Databricks · Gold Layer")
st.sidebar.caption("Results cached for 5 minutes")

if st.sidebar.button("↻  Refresh data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()


# =========================================================
# PAGE HEADER
# =========================================================

st.markdown(
    '<div class="eyebrow">IPL ANALYTICS PLATFORM</div>',
    unsafe_allow_html=True,
)

st.title(page)

st.markdown(
    '<p style="color:#64748B; margin-top:-8px;">'
    "Explore IPL batting, bowling, team and venue performance."
    "</p>",
    unsafe_allow_html=True,
)

st.divider()


# =========================================================
# OVERVIEW
# =========================================================

if page == "Overview":

    orange_table = "ipl_analytics.gold.orange_cap"
    purple_table = "ipl_analytics.gold.purple_cap"
    matches_table = "ipl_analytics.gold.highest_scoring_matches"
    innings_table = "ipl_analytics.gold.highest_team_innings"

    try:
        with st.spinner("Loading IPL overview..."):
            orange = load_table(orange_table)
            purple = load_table(purple_table)
            matches = load_table(matches_table)
            innings = load_table(innings_table)

        orange_player = find_column(
            orange,
            ["batter_name", "batsman", "batter", "player_name", "player", "striker", "name"],
        )
        orange_runs = find_column(
            orange, ["total_runs", "runs", "run_scored"]
        )

        purple_player = find_column(
            purple, ["bowler_name", "bowler", "player_name", "player", "name"]
        )
        purple_wickets = find_column(
            purple, ["total_wickets", "wickets", "wicket_count"]
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Orange Cap Records", format_value(len(orange)))

        with c2:
            st.metric("Purple Cap Records", format_value(len(purple)))

        with c3:
            value = (
                pd.to_numeric(orange[orange_runs], errors="coerce").max()
                if orange_runs else None
            )
            st.metric("Highest Runs in Results", format_value(value))

        with c4:
            value = (
                pd.to_numeric(purple[purple_wickets], errors="coerce").max()
                if purple_wickets else None
            )
            st.metric("Highest Wickets in Results", format_value(value))

        st.divider()

        left, right = st.columns(2, gap="large")

        with left:
            render_cap_chart(
                orange,
                orange_player,
                orange_runs,
                "ORANGE CAP LEADERS",
                "Top run scorers",
                ORANGE,
                "🧢",
            )

        with right:
            render_cap_chart(
                purple,
                purple_player,
                purple_wickets,
                "PURPLE CAP LEADERS",
                "Top wicket takers",
                PURPLE,
                "🧢",
            )

        st.divider()

        left, right = st.columns(2, gap="large")

        with left:
            st.subheader("Highest Scoring Matches")
            if not matches.empty:
                st.dataframe(
                    matches.head(10),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No match data returned.")

        with right:
            st.subheader("Highest Team Innings")
            if not innings.empty:
                st.dataframe(
                    innings.head(10),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No innings data returned.")

    except Exception as exc:
        st.error("Unable to load the overview.")
        st.code(str(exc))


# =========================================================
# BATTING ANALYTICS — SEARCHABLE BATTER CAREER STATS
# =========================================================

elif page == "Batting Analytics":

    st.subheader("Batting Performance")

    options = {
        "Batter Career Stats": "ipl_analytics.gold.batter_career_stats",
        "Individual Batting Scores": "ipl_analytics.gold.individual_batting_scores",
        "Batter Venue Stats": "ipl_analytics.gold.batter_venue_stats",
        "Orange Cap": "ipl_analytics.gold.orange_cap",
        "Season & Venue Batting": "ipl_analytics.gold.player_season_venue_batting",
    }

    label = st.selectbox(
        "Choose batting analysis",
        list(options.keys()),
        key="batting_table_choice",
    )

    table_name = options[label]

    try:
        with st.spinner("Loading batting data..."):
            df = load_table(table_name)

        if df.empty:
            st.info("This table returned no rows.")

        else:
            if label == "Individual Batting Scores":
                st.markdown("### Top 5 Individual Batting Scores")
                st.caption("Ranked by runs in a single innings. Each row represents one player innings, not career totals.")

                top_scores = load_top_individual_scores()
                if top_scores.empty:
                    st.info("No individual batting score records were returned.")
                else:
                    top_cols = [
                        col for col in [
                            "batsman", "runs", "balls_faced", "fours", "sixes",
                            "strike_rate", "season", "match_date", "venue",
                            "batting_team", "bowling_team", "inning", "match_id"
                        ] if col in top_scores.columns
                    ]
                    st.dataframe(
                        top_scores[top_cols],
                        use_container_width=True,
                        hide_index=True,
                    )

                    chart_data = top_scores.copy()
                    chart_data["runs"] = pd.to_numeric(chart_data["runs"], errors="coerce")
                    chart_data = chart_data.dropna(subset=["runs"]).sort_values("runs", ascending=True)
                    if not chart_data.empty:
                        fig = px.bar(
                            chart_data,
                            x="runs",
                            y="batsman",
                            orientation="h",
                            text="runs",
                            title="Highest individual innings",
                            color_discrete_sequence=[ORANGE],
                            hover_data=[c for c in ["season", "match_date", "venue", "balls_faced"] if c in chart_data.columns],
                        )
                        fig.update_traces(texttemplate="%{x:,.0f}", textposition="outside", cliponaxis=False)
                        style_chart(fig)
                        st.plotly_chart(fig, use_container_width=True)

                st.divider()
                st.markdown("### 🔎 Search Individual Batting Scores")
                st.caption("Type a player's name, then select the exact player. No player innings are loaded until you choose a name.")

                all_names = load_individual_score_player_names()
                typed_name = st.text_input(
                    "Search batter name",
                    placeholder="Start typing, e.g. V Kohli",
                    key="individual_score_name_search",
                ).strip()

                matching_names = [
                    name for name in all_names
                    if typed_name.casefold() in name.casefold()
                ] if typed_name else []

                if typed_name and not matching_names:
                    st.warning("No matching player found. Try another spelling.")
                elif matching_names:
                    selected_name = st.selectbox(
                        "Select batter",
                        options=matching_names,
                        index=None,
                        placeholder="Choose a player to view their innings",
                        key="individual_score_name_select",
                    )
                    if selected_name:
                        player_innings = load_individual_innings(selected_name)
                        st.markdown(f"### Individual innings — {selected_name}")
                        if player_innings.empty:
                            st.info("No innings were found for this player.")
                        else:
                            runs_total = pd.to_numeric(player_innings["runs"], errors="coerce").fillna(0).sum()
                            avg_runs = runs_total / len(player_innings)
                            m1, m2, m3 = st.columns(3)
                            m1.metric("Innings records", f"{len(player_innings):,}")
                            m2.metric("Runs across innings", f"{runs_total:,.0f}")
                            m3.metric("Average runs per innings", f"{avg_runs:,.2f}")

                            detail_cols = [
                                col for col in [
                                    "match_date", "season", "venue", "inning",
                                    "batting_team", "bowling_team", "runs", "balls_faced",
                                    "fours", "sixes", "strike_rate", "match_id"
                                ] if col in player_innings.columns
                            ]
                            st.dataframe(
                                player_innings[detail_cols],
                                use_container_width=True,
                                hide_index=True,
                            )

                            plot_data = player_innings.copy()
                            plot_data["runs"] = pd.to_numeric(plot_data["runs"], errors="coerce")
                            plot_data["match_label"] = (
                                plot_data["match_date"].astype(str)
                                + " · " + plot_data["batting_team"].astype(str)
                                + " vs " + plot_data["bowling_team"].astype(str)
                            )
                            plot_data = plot_data.sort_values(["match_date", "match_id"])
                            fig = px.bar(
                                plot_data,
                                x="match_label",
                                y="runs",
                                title=f"{selected_name} — runs by innings",
                                labels={"match_label": "Match", "runs": "Runs"},
                                color_discrete_sequence=[BLUE],
                                hover_data=[c for c in ["season", "venue", "balls_faced", "strike_rate"] if c in plot_data.columns],
                            )
                            fig.update_layout(xaxis_tickangle=-45, margin=dict(l=12, r=25, t=45, b=110))
                            style_chart(fig, height=430)
                            st.plotly_chart(fig, use_container_width=True)

            elif label == "Batter Career Stats":

                batter_col = find_column(
                    df,
                    [
                        "batter_name",
                        "batsman",
                        "batter",
                        "player_name",
                        "striker",
                        "player",
                        "name",
                    ],
                )

                st.markdown("### 🔎 Find a Batter")
                st.caption(
                    "Click the search box and type a player's first letters "
                    "to find matching names."
                )

                selected_batter = searchable_player_select(
                    df=df,
                    column=batter_col,
                    label="Search Batter",
                    all_label="All Batters",
                    key="career_batter_search",
                )

                if selected_batter is not None:
                    if selected_batter != "All Batters":
                        df = df[
                            df[batter_col].astype(str) == selected_batter
                        ]

                    st.markdown("### Batter Career Statistics")

                    display_dataframe(
                        df,
                        table_name,
                        key_suffix="career_filtered",
                    )

            else:
                df = apply_filters(df, f"batting_{label}")

                display_dataframe(
                    df,
                    table_name,
                    key_suffix="batting",
                )

            if label != "Individual Batting Scores" and not df.empty:
                st.divider()
                st.subheader("Batting Metric Analysis")

                category = find_column(
                    df,
                    [
                        "batter_name",
                        "batsman",
                        "batter",
                        "player_name",
                        "striker",
                        "player",
                        "name",
                        "season",
                    ],
                )

                metrics = get_numeric_columns(df)

                if category and metrics:
                    metric = st.selectbox(
                        "Choose metric",
                        metrics,
                        key="bat_metric",
                    )

                    render_bar_chart(
                        df,
                        category,
                        metric,
                        f"{metric.replace('_', ' ').title()} by {category}",
                        ORANGE,
                    )
                else:
                    st.info(
                        "No suitable category and numeric metric "
                        "were detected for this chart."
                    )

    except Exception as exc:
        st.error("Unable to load batting analytics.")
        st.code(str(exc))


# =========================================================
# BOWLING ANALYTICS — BATTER VS BOWLER SEARCH
# =========================================================

elif page == "Bowling Analytics":

    st.subheader("Bowling Performance")

    options = {
        "Bowler Career Stats": "ipl_analytics.gold.bowler_career_stats",
        "Best Bowling Figures": "ipl_analytics.gold.best_bowling_figures",
        "Bowler Venue Stats": "ipl_analytics.gold.bowler_venue_stats",
        "Purple Cap": "ipl_analytics.gold.purple_cap",
        "Batter vs Bowler": "ipl_analytics.gold.batter_vs_bowler",
    }

    label = st.selectbox(
        "Choose bowling analysis",
        list(options.keys()),
        key="bowling_table_choice",
    )

    table_name = options[label]

    try:
        with st.spinner("Loading bowling data..."):
            df = load_table(table_name)

        if df.empty:
            st.info("This table returned no rows.")

        elif label == "Batter vs Bowler":
            # Fetch the complete name lists and selected matchup directly from
            # Databricks. Do not build the dropdowns from load_table()'s 5,000-row preview.
            h2h_table = "ipl_analytics.gold.batter_vs_bowler"

            batter_names_df = run_query(f"""
                SELECT DISTINCT TRIM(batsman) AS batsman
                FROM {h2h_table}
                WHERE batsman IS NOT NULL AND TRIM(batsman) <> ''
                ORDER BY batsman
            """)
            bowler_names_df = run_query(f"""
                SELECT DISTINCT TRIM(bowler) AS bowler
                FROM {h2h_table}
                WHERE bowler IS NOT NULL AND TRIM(bowler) <> ''
                ORDER BY bowler
            """)

            batter_names = (
                batter_names_df["batsman"].dropna().astype(str).str.strip().tolist()
                if not batter_names_df.empty and "batsman" in batter_names_df.columns
                else []
            )
            bowler_names = (
                bowler_names_df["bowler"].dropna().astype(str).str.strip().tolist()
                if not bowler_names_df.empty and "bowler" in bowler_names_df.columns
                else []
            )
            batter_names = sorted({name for name in batter_names if name}, key=str.casefold)
            bowler_names = sorted({name for name in bowler_names if name}, key=str.casefold)

            st.markdown("### 🔎 Head-to-Head Search")
            st.caption(
                "Choose a batter and bowler from the full name lists. Matchup results "
                "are queried directly from Databricks, not from the 5,000-row preview."
            )

            left, right = st.columns(2, gap="large")
            with left:
                selected_batter = st.selectbox(
                    "Search Batter",
                    options=["All Batters"] + batter_names,
                    key="vs_batter_search",
                    help="Click the dropdown and type a name, e.g. Kohli.",
                )
            with right:
                selected_bowler = st.selectbox(
                    "Search Bowler",
                    options=["All Bowlers"] + bowler_names,
                    key="vs_bowler_search",
                    help="Click the dropdown and type a name, e.g. Bumrah.",
                )

            where_clauses = []
            if selected_batter != "All Batters":
                safe_batter = selected_batter.replace("'", "''")
                where_clauses.append(f"LOWER(TRIM(batsman)) = LOWER('{safe_batter}')")
            if selected_bowler != "All Bowlers":
                safe_bowler = selected_bowler.replace("'", "''")
                where_clauses.append(f"LOWER(TRIM(bowler)) = LOWER('{safe_bowler}')")

            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
            # A selected pair is a compact aggregate row; all-pairs preview is capped
            # to keep the page responsive and can be narrowed with the selectors.
            row_limit = "" if where_clauses else " LIMIT 5000"
            query = f"""
                SELECT *
                FROM {h2h_table}
                {where_sql}
                ORDER BY batter_dismissals DESC, runs DESC
                {row_limit}
            """

            with st.spinner("Searching complete batter-vs-bowler table..."):
                filtered_df = run_query(query)

            st.divider()
            st.subheader("Head-to-Head Records")
            st.caption(f"Batter: {selected_batter} · Bowler: {selected_bowler}")

            if filtered_df.empty:
                st.warning(
                    "No matching row exists in `ipl_analytics.gold.batter_vs_bowler` "
                    "for this selection. If the pair should exist, check whether the "
                    "Gold table was built from all delivery records."
                )
            else:
                # Put the most useful columns first when they exist, preserving any extras.
                preferred = [
                    "batsman", "bowler", "runs", "balls_faced", "fours", "sixes",
                    "batter_dismissals", "strike_rate",
                ]
                ordered = [col for col in preferred if col in filtered_df.columns]
                ordered += [col for col in filtered_df.columns if col not in ordered]
                filtered_df = filtered_df[ordered]
                display_dataframe(
                    filtered_df,
                    h2h_table,
                    key_suffix="head_to_head_full_query",
                )

        else:
            df = apply_filters(df, f"bowling_{label}")

            display_dataframe(
                df,
                table_name,
                key_suffix="bowling",
            )

            if not df.empty:
                st.divider()
                st.subheader("Bowling Metric Analysis")

                category = find_column(
                    df,
                    [
                        "bowler_name",
                        "bowler",
                        "player_name",
                        "player",
                        "name",
                        "season",
                    ],
                )

                metrics = get_numeric_columns(df)

                if category and metrics:
                    metric = st.selectbox(
                        "Choose metric",
                        metrics,
                        key="bowl_metric",
                    )

                    render_bar_chart(
                        df,
                        category,
                        metric,
                        f"{metric.replace('_', ' ').title()} by {category}",
                        PURPLE,
                    )
                else:
                    st.info(
                        "No suitable category and numeric metric "
                        "were detected for this chart."
                    )

    except Exception as exc:
        st.error("Unable to load bowling analytics.")
        st.code(str(exc))


# =========================================================
# TEAM & VENUE — FILTERED, RANKED GOLD TABLES
# =========================================================

elif page == "Team & Venue":

    st.subheader("Team & Venue Insights")

    options = {
        "Team Head-to-Head": "ipl_analytics.gold.team_head_to_head",
        "Season Team Batting": "ipl_analytics.gold.season_team_batting",
        "Venue Run Stats": "ipl_analytics.gold.venue_run_stats",
        "Match Scorecard": "ipl_analytics.gold.match_scorecard",
        "Highest Team Innings": "ipl_analytics.gold.highest_team_innings",
        "Highest Scoring Matches": "ipl_analytics.gold.highest_scoring_matches",
    }

    label = st.selectbox(
        "Choose team or venue analysis",
        list(options.keys()),
        key="team_table_choice",
    )
    table_name = options[label]

    try:
        with st.spinner("Fetching data from Databricks..."):
            df = load_table(table_name)

        if df.empty:
            st.info("This table returned no rows.")
        else:
            season_col = find_column(df, ["season", "year", "season_year"])

            # Season-specific tables expose a season selector. Filtering is
            # applied only after the user presses Apply.
            selected_season = "All seasons"
            if label in {"Highest Team Innings", "Highest Scoring Matches", "Match Scorecard"} and season_col:
                season_values = sorted(
                    df[season_col].dropna().astype(str).unique().tolist(),
                    reverse=True,
                )
                with st.form(f"{label.lower().replace(' ', '_')}_filters"):
                    selected_season = st.selectbox(
                        "Filter by season",
                        ["All seasons"] + season_values,
                        key=f"{label}_season_filter",
                    )
                    apply_season = st.form_submit_button("Apply season filter", type="primary")
                if apply_season and selected_season != "All seasons":
                    df = df[df[season_col].astype(str) == selected_season]

            if label == "Team Head-to-Head":
                team1_col = find_column(df, ["team1", "team_1", "team_a", "first_team", "team_home", "team"])
                team2_col = find_column(df, ["team2", "team_2", "team_b", "second_team", "team_away", "opponent"])
                wins1_col = find_column(df, ["team1_wins", "team_1_wins", "team_a_wins", "first_team_wins", "wins_team1", "team1_win", "team_a_win"])

                if team1_col and team2_col:
                    teams = sorted(
                        set(df[team1_col].dropna().astype(str))
                        | set(df[team2_col].dropna().astype(str)),
                        key=str.casefold,
                    )
                    with st.form("head_to_head_team_filters"):
                        left, right = st.columns(2)
                        with left:
                            selected_team1 = st.selectbox(
                                "Team 1", ["Choose a team"] + teams,
                                key="h2h_team1_filter",
                            )
                        with right:
                            selected_team2 = st.selectbox(
                                "Team 2", ["Choose a team"] + teams,
                                key="h2h_team2_filter",
                            )
                        apply_teams = st.form_submit_button("Apply teams", type="primary")

                    if apply_teams:
                        if selected_team1 == "Choose a team" or selected_team2 == "Choose a team":
                            st.warning("Please select both teams before applying the filter.")
                        elif selected_team1 == selected_team2:
                            st.warning("Choose two different teams for a head-to-head comparison.")
                        else:
                            direct = (
                                (df[team1_col].astype(str) == selected_team1)
                                & (df[team2_col].astype(str) == selected_team2)
                            )
                            reverse = (
                                (df[team1_col].astype(str) == selected_team2)
                                & (df[team2_col].astype(str) == selected_team1)
                            )
                            df = df[direct | reverse].copy()

                if wins1_col:
                    df = numeric_df(df, wins1_col).sort_values(wins1_col, ascending=False, kind="stable")
                    st.caption(f"Default ranking: most wins by `{wins1_col}` first. Apply two teams above for a head-to-head lookup.")
                else:
                    st.caption("Team records are shown as stored because a Team 1 wins column could not be identified in this table.")

            elif label == "Highest Team Innings":
                runs_col = find_column(df, ["total_runs", "innings_runs", "team_runs", "runs", "total_score", "score"])
                if runs_col:
                    df = numeric_df(df, runs_col).sort_values(runs_col, ascending=False, kind="stable")

            elif label == "Highest Scoring Matches":
                runs_col = find_column(df, ["combined_runs", "total_runs", "match_runs", "total_score", "runs", "score"])
                if runs_col:
                    df = numeric_df(df, runs_col).sort_values(runs_col, ascending=False, kind="stable")

            elif label == "Match Scorecard":
                date_col = find_column(df, ["match_date", "date", "start_date", "match_dt"])
                if date_col:
                    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
                    df = df.sort_values(date_col, ascending=True, kind="stable", na_position="last")
                st.caption("Match scorecards are ordered by date, oldest to newest.")

            elif label == "Venue Run Stats":
                runs_col = find_column(df, ["total_runs", "runs", "average_runs", "avg_runs", "run_scored"])
                if runs_col:
                    df = numeric_df(df, runs_col).sort_values(runs_col, ascending=False, kind="stable")

            elif label == "Season Team Batting":
                runs_col = find_column(df, ["total_runs", "runs", "run_scored", "team_runs"])
                if runs_col:
                    df = numeric_df(df, runs_col).sort_values(runs_col, ascending=False, kind="stable")

            display_dataframe(df, table_name, key_suffix=label.lower().replace(" ", "_"))

            # Avoid generic metric charts here: these tables have different
            # meanings and should be ranked using the appropriate metric above.

    except Exception as exc:
        st.error("Unable to load team and venue analytics.")
        st.code(str(exc))


# =========================================================
# GOLD LAYER EXPLORER
# =========================================================

elif page == "Gold Layer Explorer":

    st.subheader("Gold Layer Explorer")
    st.caption("Featured tables are shown first. Search by table name, then select a table to inspect its real rows.")

    # These are useful starting points, not random first rows from ALLOWED_TABLES.
    featured_tables = [
        ("Individual Batting Scores", "ipl_analytics.gold.individual_batting_scores"),
        ("Batter Career Stats", "ipl_analytics.gold.batter_career_stats"),
        ("Orange Cap", "ipl_analytics.gold.orange_cap"),
        ("Purple Cap", "ipl_analytics.gold.purple_cap"),
        ("Highest Scoring Matches", "ipl_analytics.gold.highest_scoring_matches"),
    ]
    featured_tables = [
        (label, table) for label, table in featured_tables
        if table in ALLOWED_TABLES
    ]

    st.markdown("### ⭐ Featured Gold Tables")
    if featured_tables:
        card_cols = st.columns(len(featured_tables))
        for col, (label, table) in zip(card_cols, featured_tables):
            with col:
                st.markdown(f"**{label}**")
                st.caption(table.split(".")[-1])

    st.divider()
    table_search = st.text_input(
        "Search Gold tables",
        placeholder="Search table names, e.g. batter, venue, purple cap",
        key="gold_layer_table_search",
    ).strip().casefold()

    all_tables = sorted(ALLOWED_TABLES)
    filtered_tables = [
        table for table in all_tables
        if table_search in table.casefold()
        or table.split(".")[-1].replace("_", " ").casefold().find(table_search) >= 0
    ]

    if not filtered_tables:
        st.warning("No Gold tables match your search.")
    else:
        preferred = "ipl_analytics.gold.individual_batting_scores"
        default_table = preferred if preferred in filtered_tables else filtered_tables[0]
        table_name = st.selectbox(
            "Select a Gold table",
            options=filtered_tables,
            index=filtered_tables.index(default_table),
            format_func=lambda table: table.split(".")[-1].replace("_", " ").title(),
            key="explorer_table_choice",
        )

        st.caption(f"Source: `{table_name}`")
        if st.button("Load Table", type="primary", key="load_selected_gold_table"):
            st.session_state["explorer_table"] = table_name

        active_table = st.session_state.get("explorer_table")
        if active_table not in filtered_tables:
            active_table = None

        if active_table:
            show_table(active_table)
        else:
            st.info("Choose a table and press **Load Table** to preview its data.")

# =========================================================
# FOOTER
# =========================================================

st.divider()

st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between;
                flex-wrap:wrap; gap:10px; padding-bottom:14px;">
        <span class="footer-text">
            IPL Pavilion · Data Analytics Portfolio Project
        </span>
        <span style="color:{BLUE}; font-size:12px; font-weight:700;">
            STREAMLIT × DATABRICKS
        </span>
    </div>
    """,
    unsafe_allow_html=True,
)
