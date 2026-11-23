WITH ranked AS (
    SELECT
        region,
        video_id,
        title,
        rank,
        ingested_at,
        LAG(rank) OVER (
            PARTITION BY region, video_id
            ORDER BY ingested_at
        ) AS previous_rank
    FROM yt_curated
    WHERE dt >= '2026-11-03'
)
SELECT
    region,
    video_id,
    title,
    previous_rank,
    rank AS current_rank,
    previous_rank - rank AS rank_improvement,
    ingested_at
FROM ranked
WHERE previous_rank IS NOT NULL
ORDER BY rank_improvement DESC
LIMIT 50;