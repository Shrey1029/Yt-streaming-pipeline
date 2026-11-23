SELECT
    region,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT ingested_at) AS snapshots
FROM yt_curated
WHERE dt >= '2026-11-03'
GROUP BY region
ORDER BY region;