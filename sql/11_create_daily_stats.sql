CREATE TABLE daily_video_stats
WITH (
    format = 'PARQUET',
    partitioned_by = ARRAY['dt', 'region']
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
WHERE rn_latest = 1;