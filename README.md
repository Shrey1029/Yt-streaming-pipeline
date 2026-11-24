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
```
---

### Data Layers

Bronze / Raw (S3): Raw JSON payloads captured per region (IN, GB, US, etc.) by yt-ingest.

Silver / Curated (yt_pipeline.yt_curated): Cleaned, deduplicated, and schema-enforced Parquet files partitioned by dt and region.

Gold / Analytics (yt_pipeline.daily_video_stats): Daily video-level rollups built via Athena CTAS (sql/11_create_daily_stats.sql), capturing end-of-day views, likes, comments, best daily rank, intra-day view deltas, and snapshot counts.
---

### Key Features
Serverless Ingestion & Transformation: Event-driven AWS Lambda functions (yt-ingest and yt-transform) provisioned with Terraform (infra/).

Idempotent Gold Table Rebuilds: Automated MSCK REPAIR TABLE, single-statement DROP, S3 prefix cleanup, and CREATE TABLE AS SELECT (CTAS) rebuilds with explicit Athena execution status verification.

Interactive Run-vs-Run Comparison: Compare any two pipeline runs side by side by category, country/region, and view metrics using Plotly charts.

Built-In Data Quality Monitoring: Live Athena DQ checks auditing row counts, distinct video IDs, duplicate video-days, null IDs, negative view deltas, and rank validity.

Full Documentation: Includes YouTube_Streaming_Data_Engineering_Project_Documentation.pdf detailing system design, troubleshooting, and architecture flowcharts.

```
├── infra/                                                     # Terraform IaC for S3, IAM, Lambda, and Glue/Athena
├── sql/
│   └── 11_create_daily_stats.sql                              # CTAS definition for yt_pipeline.daily_video_stats
├── src/
│   ├── dashboard/
│   │   └── app.py                                             # Streamlit dashboard & Athena refresh orchestrator
│   └── lambdas/                                               # Ingestion & transformation Lambda handlers
├── YouTube_Streaming_Data_Engineering_Project_Documentation.pdf
├── .env.example
└── README.md
```
---

### Getting Started

1. Prerequisites
Python 3.11+

AWS account with access to S3, Lambda, Glue Data Catalog, and Athena (ap-south-1)

YouTube Data API v3 key (configured in your ingestion Lambda environment)

2.
 git clone https://github.com/Shrey1029/Yt-streaming-pipeline.git
cd Yt-streaming-pipeline

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install streamlit boto3 awswrangler pandas plotly python-dotenv

3. Environment Configuration
Create a .env file in the project root:

AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key
AWS_DEFAULT_REGION=ap-south-1

YT_INGEST_LAMBDA=yt-ingest
ATHENA_OUTPUT_BUCKET=your-athena-query-results-bucket
GOLD_STATS_S3_LOCATION=s3://your-pipeline-bucket/gold/daily_video_stats/

Note: Setting GOLD_STATS_S3_LOCATION ensures Athena writes daily_video_stats to a deterministic S3 prefix that is automatically cleaned prior to each CTAS rebuild, preventing HIVE_PATH_ALREADY_EXISTS or leftover-object errors.

4. Run the Dashboard








