
import pandas as pd
import streamlit as st
from databricks import sql


ALLOWED_TABLES = {
    "ipl_analytics.gold.batter_career_stats",
    "ipl_analytics.gold.batter_venue_stats",
    "ipl_analytics.gold.batter_vs_bowler",
    "ipl_analytics.gold.best_bowling_figures",
    "ipl_analytics.gold.bowler_career_stats",
    "ipl_analytics.gold.bowler_venue_stats",
    "ipl_analytics.gold.highest_scoring_matches",
    "ipl_analytics.gold.highest_team_innings",
    "ipl_analytics.gold.individual_batting_scores",
    "ipl_analytics.gold.match_scorecard",
    "ipl_analytics.gold.orange_cap",
    "ipl_analytics.gold.player_season_venue_batting",
    "ipl_analytics.gold.purple_cap",
    "ipl_analytics.gold.season_team_batting",
    "ipl_analytics.gold.team_head_to_head",
    "ipl_analytics.gold.venue_run_stats",
}


def run_query(query: str, parameters=None) -> pd.DataFrame:
    """Run a SQL query using Databricks PAT authentication."""

    cfg = st.secrets["databricks"]

    with sql.connect(
        server_hostname=cfg["server_hostname"].strip(),
        http_path=cfg["http_path"].strip(),
        access_token=cfg["access_token"].strip(),
        use_cloud_fetch=False,
    ) as connection:

        with connection.cursor() as cursor:
            if parameters is not None:
                cursor.execute(query, parameters=parameters)
            else:
                cursor.execute(query)

            rows = cursor.fetchall()

            columns = (
                [column[0] for column in cursor.description]
                if cursor.description
                else []
            )

            return pd.DataFrame(rows, columns=columns)


def test_connection() -> bool:
    """Check whether Databricks authentication and SQL work."""

    df = run_query("SELECT 1 AS connection_test")

    return (
        not df.empty
        and int(df.iloc[0]["connection_test"]) == 1
    )


def get_table_preview(table_name: str) -> pd.DataFrame:
    """Load a preview from an approved Gold table."""

    if table_name not in ALLOWED_TABLES:
        raise ValueError("Table is not in the approved list.")

    return run_query(f"SELECT * FROM {table_name} LIMIT 100")
