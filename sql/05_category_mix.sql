SELECT
    region,
    category_id,
    COUNT(DISTINCT video_id) AS total_videos
FROM yt_curated
WHERE dt >= '2026-11-03'
GROUP BY region, category_id
ORDER BY region, total_videos DESC;