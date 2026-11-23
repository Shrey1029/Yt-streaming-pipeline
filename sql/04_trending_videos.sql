SELECT
    region,
    video_id,
    MAX_BY(title, ingested_at) AS title,
    COUNT(*) AS snapshots,
    MIN(rank) AS best_rank

FROM yt_curated

WHERE dt >= '2026-11-03'

GROUP BY region, video_id

ORDER BY snapshots DESC

LIMIT 20;