WITH latest_snapshot AS (
    SELECT
        region,
        MAX(ingested_at) AS max_ingested_at
    FROM yt_curated
    WHERE dt >= '2026-11-03'
    GROUP BY region
),
ranked_videos AS (
    SELECT
        y.region,
        y.video_id,
        y.title,
        y.channel_title,
        y.rank,
        y.views,
        y.ingested_at,
        ROW_NUMBER() OVER (
            PARTITION BY y.region
            ORDER BY y.rank ASC, y.views DESC
        ) AS rn
    FROM yt_curated y
    INNER JOIN latest_snapshot ls
        ON y.region = ls.region
       AND y.ingested_at = ls.max_ingested_at
    WHERE y.dt >= '2026-11-03'
)
SELECT
    region,
    video_id,
    title,
    channel_title,
    rank,
    views,
    ingested_at
FROM ranked_videos
WHERE rn <= 10
ORDER BY region, rn;