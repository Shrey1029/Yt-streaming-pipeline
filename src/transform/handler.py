
import json
import boto3
import pandas as pd
import awswrangler as wr

s3 = boto3.client("s3")


def flatten(envelope):
    rows = []

    for rank, video in enumerate(envelope.get("items", []), start=1):
        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})

        rows.append({
            "video_id": video.get("id"),
            "title": snippet.get("title"),
            "channel_id": snippet.get("channelId"),
            "channel_title": snippet.get("channelTitle"),
            "category_id": snippet.get("categoryId"),
            "published_at": snippet.get("publishedAt"),
            "views": statistics.get("viewCount"),
            "likes": statistics.get("likeCount"),
            "comments": statistics.get("commentCount"),
            "rank": rank,
            "region": envelope.get("region"),
            "ingested_at": envelope.get("ingested_at")
        })

    columns = [
        "video_id", "title", "channel_id", "channel_title",
        "category_id", "published_at", "views", "likes",
        "comments", "rank", "region", "ingested_at"
    ]

    df = pd.DataFrame(rows, columns=columns)

    df["published_at"] = pd.to_datetime(
        df["published_at"], utc=True, errors="coerce"
    )
    df["ingested_at"] = pd.to_datetime(
        df["ingested_at"], utc=True, errors="coerce"
    )

    for column in ["views", "likes", "comments"]:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        ).astype("Int64")

    df["rank"] = df["rank"].astype("int32")

    return df


def process(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    envelope = json.loads(response["Body"].read())

    df = flatten(envelope)

    output_key = key.replace("raw/", "curated/", 1)
    output_key = output_key.replace(".json", ".parquet")

    wr.s3.to_parquet(
        df=df,
        path=f"s3://{bucket}/{output_key}",
        index=False
    )

    return output_key, len(df)


def lambda_handler(event, context):
    for record in event["Records"]:
        message = json.loads(record["body"])

        output_key, rows = process(
            message["bucket"],
            message["key"]
        )

        print(f"Transformed {rows} rows -> {output_key}")

    return {"status": "success"}
