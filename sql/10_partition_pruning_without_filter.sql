SELECT
    region,
    COUNT(*) AS total_records
FROM yt_curated
GROUP BY region
ORDER BY region;