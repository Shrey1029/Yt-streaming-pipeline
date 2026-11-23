WITH snapshots AS (
    SELECT DISTINCT region, ingested_at
    FROM yt_curated
    WHERE dt >= '2026-11-03'
),
ordered_snapshots AS (
    SELECT
        region,
        ingested_at,
        LAG(ingested_at) OVER (
            PARTITION BY region
            ORDER BY ingested_at
        ) AS previous_snapshot
    FROM snapshots
),
numbered AS (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY region
            ORDER BY ingested_at DESC
        ) AS rn
    FROM ordered_snapshots
),
latest_pair AS (
    SELECT
        region,
        ingested_at AS latest_snapshot,
        previous_snapshot
    FROM numbered
    WHERE rn = 1
      AND previous_snapshot IS NOT NULL
)
SELECT
    y.region,
    y.video_id,
    y.title,
    y.rank,
    y.views
FROM yt_curated y
JOIN latest_pair p
    ON y.region = p.region
   AND y.ingested_at = p.latest_snapshot
WHERE y.dt >= '2026-11-03'
  AND NOT EXISTS (
      SELECT 1
      FROM yt_curated old
      WHERE old.region = y.region
        AND old.video_id = y.video_id
        AND old.ingested_at = p.previous_snapshot
  )
ORDER BY y.region, y.rank;