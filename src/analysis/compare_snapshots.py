import json, glob
files = sorted(glob.glob("tmp/region=IN/**/*.json", recursive=True))
a, b = [json.load(open(f)) for f in files[-2:]]
old = {v["id"]: int(v["statistics"]["viewCount"]) for v in a["items"]}
for v in b["items"][:10]:
    vid, new = v["id"], int(v["statistics"]["viewCount"])
    if vid in old:
        print(v["snippet"]["title"][:50], "+", new - old[vid])