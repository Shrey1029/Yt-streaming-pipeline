SELECT
    region,
    COUNT(*) AS video_count
FROM v_latest_snapshot
GROUP BY region
ORDER BY region;