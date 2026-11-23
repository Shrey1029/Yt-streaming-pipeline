WITH snapshots AS (
    SELECT
        region,
        video_id,
        title,
        ingested_at,
        views,

        LAG(views) OVER (
            PARTITION BY region, video_id
            ORDER BY ingested_at
        ) AS previous_views,

        LAG(ingested_at) OVER (
            PARTITION BY region, video_id
            ORDER BY ingested_at
        ) AS previous_timestamp

    FROM yt_curated
    WHERE dt >= '2026-11-03'
)

SELECT
    region,
    title,
    views - previous_views AS views_gained,

    DATE_DIFF(
        'minute',
        previous_timestamp,
        ingested_at
    ) AS minutes_between,

    ROUND(
        (views - previous_views) * 60.0 /
        DATE_DIFF('minute', previous_timestamp, ingested_at)
    ) AS views_per_hour

FROM snapshots

WHERE previous_views IS NOT NULL
  AND DATE_DIFF('minute', previous_timestamp, ingested_at) > 0

ORDER BY views_per_hour DESC
LIMIT 20;