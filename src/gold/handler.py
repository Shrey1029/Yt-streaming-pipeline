import os
import time
import boto3

ATHENA_CLIENT = boto3.client(
    "athena",
    region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1"),
)

DATABASE = os.environ.get("GLUE_DATABASE", "yt_pipeline")
WORKGROUP = os.environ.get("ATHENA_WORKGROUP", "yt-wg")
CURATED_TABLE = os.environ.get("CURATED_TABLE", "yt_curated")
GOLD_TABLE = os.environ.get("GOLD_TABLE", "daily_video_stats")


def _run_and_wait(sql: str, poll_interval: float = 2.0, max_wait: float = 120.0) -> str:
    response = ATHENA_CLIENT.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DATABASE},
        WorkGroup=WORKGROUP,
    )
    query_execution_id = response["QueryExecutionId"]

    elapsed = 0.0
    while elapsed < max_wait:
        status_resp = ATHENA_CLIENT.get_query_execution(QueryExecutionId=query_execution_id)
        state = status_resp["QueryExecution"]["Status"]["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            if state != "SUCCEEDED":
                reason = status_resp["QueryExecution"]["Status"].get(
                    "StateChangeReason", "Unknown error"
                )
                raise RuntimeError(
                    f"Athena query {query_execution_id} ended with state {state}: {reason}"
                )
            return query_execution_id
        time.sleep(poll_interval)
        elapsed += poll_interval

    raise TimeoutError(f"Athena query {query_execution_id} timed out after {max_wait}s")


def _partition_has_rows(dt: str) -> int:
    check_sql = f"""
    SELECT CAST(COUNT(*) AS VARCHAR) AS row_count
    FROM {GOLD_TABLE}
    WHERE dt = '{dt}';
    """
    qid = _run_and_wait(check_sql)
    results = ATHENA_CLIENT.get_query_results(QueryExecutionId=qid)
    rows = results.get("ResultSet", {}).get("Rows", [])
    # Row 0 is the column header; Row 1 is the first data row
    if len(rows) > 1:
        val = rows[1].get("Data", [{}])[0].get("VarCharValue", "0")
        return int(val)
    return 0


def lambda_handler(event, context):
    dt = event.get("dt")
    if not dt:
        raise ValueError("Missing required 'dt' (YYYY-MM-DD) in Lambda event")

    force_rerun = bool(event.get("force_rerun", False))
    existing_rows = _partition_has_rows(dt)

    if existing_rows > 0 and not force_rerun:
        return {
            "status": "skipped",
            "dt": dt,
            "existing_rows": existing_rows,
            "message": f"Partition dt={dt} already has {existing_rows} rows; set force_rerun=true to append anyway.",
        }

    insert_sql = f"""
    INSERT INTO {GOLD_TABLE}
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
        FROM {CURATED_TABLE}
        WHERE dt = '{dt}'
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
    WHERE rn_latest = 1;
    """

    query_execution_id = _run_and_wait(insert_sql)
    return {
        "status": "succeeded",
        "dt": dt,
        "previous_rows": existing_rows,
        "query_execution_id": query_execution_id,
    }