SELECT
    region,
    HOUR(
        AT_TIMEZONE(
            WITH_TIMEZONE(ingested_at, 'UTC'),
            'Asia/Kolkata'
        )
    ) AS ist_hour,
    COUNT(*) AS records_collected
FROM yt_curated
WHERE dt >= '2026-11-03'
GROUP BY
    region,
    HOUR(
        AT_TIMEZONE(
            WITH_TIMEZONE(ingested_at, 'UTC'),
            'Asia/Kolkata'
        )
    )
ORDER BY region, records_collected DESC;