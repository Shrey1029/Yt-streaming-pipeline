import base64
import os
import time
from pathlib import Path

import awswrangler as wr
import boto3
from botocore.exceptions import ClientError
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

YT_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "18": "Short Movies",
    "19": "Travel & Events",
    "20": "Gaming",
    "21": "Videoblogging",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}

INGEST_FUNCTION_NAME = os.getenv("YT_INGEST_LAMBDA", "yt-ingest")
GOLD_STATS_S3_LOCATION = os.getenv("GOLD_STATS_S3_LOCATION")

st.set_page_config(page_title="YouTube Category Tracker", layout="wide")
st.title("YouTube Trending Categories: Old Run vs. New Run")

session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="ap-south-1",
)


def _athena_kwargs():
    output_bucket = os.getenv("ATHENA_OUTPUT_BUCKET")
    kwargs = {}
    if output_bucket:
        kwargs["s3_output"] = f"s3://{output_bucket}/athena-results/"
    return kwargs


def _wait_for_athena_success(query_execution_id: str, step_label: str):
    res = wr.athena.wait_query(query_execution_id=query_execution_id, boto3_session=session)
    state = res["QueryExecution"]["Status"].get("State")
    reason = res["QueryExecution"]["Status"].get("StateChangeReason", "")
    if state != "SUCCEEDED":
        raise RuntimeError(f"{step_label} failed ({state}): {reason}")


def _cleanup_s3_prefix(s3_uri: str):
    if not s3_uri or not s3_uri.startswith("s3://"):
        return
    without_scheme = s3_uri[5:]
    parts = without_scheme.split("/", 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    s3_client = session.client("s3")
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        objs = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
        if objs:
            s3_client.delete_objects(Bucket=bucket, Delete={"Objects": objs})


def refresh_daily_stats():
    athena_kw = _athena_kwargs()

    repair_curated_qid = wr.athena.start_query_execution(
        sql="MSCK REPAIR TABLE yt_pipeline.yt_curated",
        database="yt_pipeline",
        boto3_session=session,
        **athena_kw,
    )
    _wait_for_athena_success(repair_curated_qid, "MSCK REPAIR yt_curated")

    drop_qid = wr.athena.start_query_execution(
        sql="DROP TABLE IF EXISTS yt_pipeline.daily_video_stats",
        database="yt_pipeline",
        boto3_session=session,
        **athena_kw,
    )
    _wait_for_athena_success(drop_qid, "DROP daily_video_stats")

    if GOLD_STATS_S3_LOCATION:
        _cleanup_s3_prefix(GOLD_STATS_S3_LOCATION)
        external_loc_clause = f",\n        external_location = '{GOLD_STATS_S3_LOCATION.rstrip('/')}/'"
    else:
        external_loc_clause = ""

    ctas_sql = f"""
    CREATE TABLE yt_pipeline.daily_video_stats
    WITH (
        format = 'PARQUET',
        partitioned_by = ARRAY['dt', 'region']{external_loc_clause}
    ) AS
    WITH daily_ranked AS (
        SELECT
            video_id,
            title,
            channel_id,
            channel_title,
            category_id,
            published_at,
            views,
            likes,
            comments,
            rank,
            ingested_at,
            dt,
            region,
            ROW_NUMBER() OVER (
                PARTITION BY region, dt, video_id
                ORDER BY ingested_at DESC
            ) AS rn_latest,
            MIN(views) OVER (
                PARTITION BY region, dt, video_id
            ) AS min_views_day,
            MAX(views) OVER (
                PARTITION BY region, dt, video_id
            ) AS max_views_day,
            MIN(rank) OVER (
                PARTITION BY region, dt, video_id
            ) AS best_rank_day,
            COUNT(*) OVER (
                PARTITION BY region, dt, video_id
            ) AS snapshots_in_day
        FROM yt_curated
        WHERE dt IS NOT NULL
    )
    SELECT
        video_id,
        title,
        channel_id,
        channel_title,
        category_id,
        published_at,
        views AS end_of_day_views,
        likes AS end_of_day_likes,
        comments AS end_of_day_comments,
        rank AS end_of_day_rank,
        best_rank_day,
        (max_views_day - min_views_day) AS views_delta_in_day,
        snapshots_in_day,
        ingested_at AS last_ingested_at,
        dt,
        region
    FROM daily_ranked
    WHERE rn_latest = 1
    """

    ctas_qid = wr.athena.start_query_execution(
        sql=ctas_sql,
        database="yt_pipeline",
        boto3_session=session,
        **athena_kw,
    )
    _wait_for_athena_success(ctas_qid, "CTAS daily_video_stats")


def trigger_pipeline_run():
    lambda_client = session.client("lambda")
    try:
        with st.spinner(f"Triggering `{INGEST_FUNCTION_NAME}`..."):
            resp = lambda_client.invoke(
                FunctionName=INGEST_FUNCTION_NAME,
                InvocationType="RequestResponse",
                LogType="Tail",
            )
    except ClientError as exc:
        st.error(f"AWS Lambda invoke failed: {exc}")
        return False
    except Exception as exc:
        st.error(f"Unexpected error invoking Lambda: {exc}")
        return False

    log_b64 = resp.get("LogResult")
    if log_b64:
        decoded_logs = base64.b64decode(log_b64).decode("utf-8", errors="replace")
        st.sidebar.text_area("Latest Lambda Tail Log", decoded_logs, height=180)

    if resp.get("FunctionError"):
        payload = resp.get("Payload")
        err_msg = (
            payload.read().decode("utf-8", errors="replace")
            if payload
            else "Unknown Lambda error"
        )
        st.error(f"Lambda returned FunctionError: {err_msg}")
        return False

    with st.spinner("Waiting for `yt-transform` to write curated Parquet..."):
        time.sleep(10)

    try:
        with st.spinner("Rebuilding `yt_pipeline.daily_video_stats` in Athena..."):
            refresh_daily_stats()
    except Exception as exc:
        st.error(f"Failed to refresh `daily_video_stats`: {exc}")
        return False

    st.cache_data.clear()
    st.success(
        f"Pipeline triggered (status {resp.get('StatusCode')}), `daily_video_stats` refreshed, and cache cleared."
    )
    return True


auto_run = st.sidebar.checkbox("Auto-run pipeline on dashboard start", value=False)
if st.sidebar.button("Run Pipeline & Refresh", type="primary"):
    if trigger_pipeline_run():
        st.rerun()

if st.sidebar.button("Clear Cache & Reload"):
    st.cache_data.clear()
    st.rerun()

if auto_run and "did_autorun" not in st.session_state:
    st.session_state["did_autorun"] = True
    if trigger_pipeline_run():
        st.rerun()


def find_col(cols, options):
    lower = {c.lower(): c for c in cols}
    for opt in options:
        if opt.lower() in lower:
            return lower[opt.lower()]
    return None


@st.cache_data(ttl=300)
def load_available_runs():
    q_df = wr.athena.read_sql_query(
        sql="SELECT DISTINCT CAST(dt AS VARCHAR) AS dt FROM yt_pipeline.daily_video_stats WHERE dt IS NOT NULL ORDER BY dt ASC",
        database="yt_pipeline",
        boto3_session=session,
        **_athena_kwargs(),
    )
    return sorted(q_df["dt"].dropna().astype(str).unique())


@st.cache_data(ttl=300)
def load_data(selected_runs=None, limit=5000):
    where_sql = ""
    if selected_runs:
        quoted = ", ".join(f"'{r}'" for r in selected_runs)
        where_sql = f" WHERE CAST(dt AS VARCHAR) IN ({quoted})"
    return wr.athena.read_sql_query(
        sql=f"SELECT * FROM yt_pipeline.daily_video_stats{where_sql} ORDER BY dt DESC LIMIT {int(limit)}",
        database="yt_pipeline",
        boto3_session=session,
        **_athena_kwargs(),
    )


@st.cache_data(ttl=300)
def load_dq_report():
    dq_sql = """
    SELECT
        dt,
        region,
        COUNT(*) AS total_rows,
        COUNT(DISTINCT video_id) AS distinct_videos,
        COUNT(*) - COUNT(DISTINCT video_id) AS duplicate_video_days,
        SUM(CASE WHEN video_id IS NULL OR TRIM(video_id) = '' THEN 1 ELSE 0 END) AS missing_video_id,
        SUM(CASE WHEN views_delta_in_day < 0 THEN 1 ELSE 0 END) AS negative_view_deltas,
        SUM(CASE WHEN best_rank_day < 1 THEN 1 ELSE 0 END) AS invalid_best_rank
    FROM yt_pipeline.daily_video_stats
    GROUP BY dt, region
    ORDER BY dt DESC, region
    """
    return wr.athena.read_sql_query(
        sql=dq_sql,
        database="yt_pipeline",
        boto3_session=session,
        **_athena_kwargs(),
    )


try:
    available_runs = load_available_runs()
except Exception as exc:
    st.error(f"Failed to query available runs from `daily_video_stats`: {exc}")
    st.stop()

if len(available_runs) < 2:
    st.info(f"Only one run found ({available_runs}). Run again later to compare runs.")
    st.stop()

default_old_idx = max(0, len(available_runs) - 2)
default_new_idx = len(available_runs) - 1

old_run = st.sidebar.selectbox("Earlier Run", available_runs, index=default_old_idx)
new_run = st.sidebar.selectbox("Later Run", available_runs, index=default_new_idx)

limit = st.sidebar.slider("Rows to load", 500, 10000, 5000, step=500)
df = load_data(selected_runs=sorted({old_run, new_run}), limit=limit)

cat_col = find_col(df.columns, ["category_id", "category", "category_name", "video_category"])
date_col = find_col(df.columns, ["date", "dt", "run_date", "snapshot_date", "run_ts"])
country_col = find_col(df.columns, ["region", "country", "region_code"])
metric_col = find_col(df.columns, ["views", "view_count", "total_views"])

if not cat_col or not date_col:
    st.error(f"Could not auto-detect category/date columns. Found columns: {list(df.columns)}")
    st.stop()

st.sidebar.caption(
    f"Loaded {len(df)} rows | Available runs: {available_runs}"
)

df = df.copy()
df["run"] = df[date_col].astype(str)
raw_cat = df[cat_col].astype(str).str.strip()
df["category"] = raw_cat.map(lambda x: f"{YT_CATEGORIES[x]} ({x})" if x in YT_CATEGORIES else x)
df["country"] = df[country_col].astype(str) if country_col else "ALL"
df["value"] = df[metric_col].fillna(0) if metric_col else 1

if country_col:
    countries = sorted(df["country"].unique())
    default_c = [c for c in ["IN", "GB", "US"] if c in countries] or countries
    picked_countries = st.sidebar.multiselect("Countries", countries, default=default_c)
    if picked_countries:
        df = df[df["country"].isin(picked_countries)]

comp = (
    df[df["run"].isin([old_run, new_run])]
    .groupby(["category", "run"], as_index=False)["value"]
    .sum()
)

fig = px.bar(
    comp,
    x="category",
    y="value",
    color="run",
    barmode="group",
    labels={"value": metric_col or "Trending Count", "category": "Video Category", "run": "Run"},
    title=f"Trending Categories: {old_run} vs. {new_run}",
)
fig.update_xaxes(type="category")
st.plotly_chart(fig, width="stretch")

old_cats = set(df[df["run"] == old_run]["category"].unique())
new_cats = set(df[df["run"] == new_run]["category"].unique())

kept_trending = sorted(old_cats & new_cats)
newly_trending = sorted(new_cats - old_cats)
dropped_off = sorted(old_cats - new_cats)

c1, c2, c3 = st.columns(3)
c1.metric("Kept Trending (Both Runs)", len(kept_trending))
c2.metric("New in Later Run", len(newly_trending))
c3.metric("Dropped Since Earlier Run", len(dropped_off))

st.subheader("Status Breakdown")
st.write("**Kept trending in both runs:**", ", ".join(kept_trending) if kept_trending else "None")
st.write("**New in later run:**", ", ".join(newly_trending) if newly_trending else "None")
st.write("**Dropped since earlier run:**", ", ".join(dropped_off) if dropped_off else "None")

with st.expander("Data Quality Check (`daily_video_stats`)"):
    try:
        dq_df = load_dq_report()
        st.dataframe(dq_df, width="stretch")
    except Exception as exc:
        st.warning(f"Could not run DQ query: {exc}")