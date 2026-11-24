# YouTube Trending Analytics Pipeline & Dashboard

An end-to-end serverless data engineering pipeline and interactive Streamlit dashboard that ingests YouTube trending video metrics across regions, curates partitioned Parquet datasets on Amazon S3, models daily gold aggregations in AWS Athena, and visualizes category-level shifts over time.

---

## Architecture & Data Flow

```text
+-------------------+      +---------------------+      +-------------------------+
|  YouTube Data API | ---> |   AWS Lambda        | ---> |   Amazon S3 (Raw)       |
|  (v3 /videos)     |      |   (yt-ingest)       |      |   JSON Snapshots        |
+-------------------+      +---------------------+      +-------------------------+
                                                                     |
                                                          S3 Event / Trigger
                                                                     v
+-------------------+      +---------------------+      +-------------------------+
|  Streamlit UI     | <--- |   AWS Athena        | <--- |   AWS Lambda            |
|  (app.py)         |      |   yt_pipeline DB    |      |   (yt-transform)        |
+-------------------+      +---------------------+      +-------------------------+
        |                            ^                               |
        |  On-Demand Refresh         |  Partitioned Parquet          v
        +----------------------------+------------------- Amazon S3 (Curated & Gold)
