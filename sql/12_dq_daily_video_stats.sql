-- Data quality check for Gold table: daily_video_stats
-- Checks for duplicate video rows per (dt, region), null/blank video_ids,
-- negative daily view deltas, and invalid best ranks.

SELECT
    dt,
    region,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT video_id) AS distinct_videos,
    COUNT(*) - COUNT(DISTINCT video_id) AS duplicate_video_days,
    SUM(CASE WHEN video_id IS NULL OR TRIM(video_id) = '' THEN 1 ELSE 0 END) AS missing_video_id,
    SUM(CASE WHEN views_delta_in_day < 0 THEN 1 ELSE 0 END) AS negative_view_deltas,
    SUM(CASE WHEN best_rank_day < 1 THEN 1 ELSE 0 END) AS invalid_best_rank
FROM daily_video_stats
GROUP BY dt, region
ORDER BY dt DESC, region;