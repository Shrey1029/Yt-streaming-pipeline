SELECT region, COUNT(*) AS total_rows,
       COUNT(DISTINCT ingested_at) AS snapshots
FROM yt_curated
GROUP BY region;