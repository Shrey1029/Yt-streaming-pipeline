import json, os, boto3, urllib.request, urllib.parse, datetime as dt

BUCKET = os.environ.get("BUCKET", "yt-pipeline-shreyansh-raw")
REGIONS = ["IN", "US", "GB"]
MAX_PAGES = 4  # 4 x 50 = up to 200 videos per region

s3 = boto3.client("s3")

def get_key():
    k = os.environ.get("YOUTUBE_API_KEY")
    if k:
        return k
    ssm = boto3.client("ssm", region_name="ap-south-1")
    return ssm.get_parameter(Name="/yt/api_key", WithDecryption=True)["Parameter"]["Value"]

def fetch_region(region, api_key):
    items, token = [], None
    for _ in range(MAX_PAGES):
        params = {"part": "snippet,statistics", "chart": "mostPopular",
                  "regionCode": region, "maxResults": 50, "key": api_key}
        if token:
            params["pageToken"] = token
        url = "https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(params)
        data = json.loads(urllib.request.urlopen(url).read())
        items += data.get("items", [])
        token = data.get("nextPageToken")
        if not token:
            break
    return items

def main():
    api_key = get_key()
    now = dt.datetime.now(dt.timezone.utc)
    for r in REGIONS:
        items = fetch_region(r, api_key)
        envelope = {"region": r, "ingested_at": now.isoformat(), "items": items}
        key = f"raw/region={r}/dt={now:%Y-%m-%d}/hour={now:%H}/{now:%H%M%S}.json"
        s3.put_object(Bucket=BUCKET, Key=key, Body=json.dumps(envelope))
        print(f"uploaded {len(items)} videos -> {key}")

if __name__ == "__main__":
    main()