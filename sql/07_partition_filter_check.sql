SELECT
    region,
    COUNT(*) AS total_records
FROM yt_curated
WHERE dt = '2026-11-19'
GROUP BY region
ORDER BY region;

