"""Probe GEFS S3 bucket top-level to find actual path structure."""
import urllib.request, re

def s3_list(prefix="", delimiter="/", max_keys=20):
    url = (
        f"https://noaa-gefs-retrospective.s3.amazonaws.com/"
        f"?prefix={prefix}&delimiter={delimiter}&max-keys={max_keys}"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "test"})
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read().decode("utf-8")
    keys = re.findall(r"<Key>(.*?)</Key>", raw)
    prefixes = re.findall(r"<CommonPrefixes><Prefix>(.*?)</Prefix></CommonPrefixes>", raw)
    return keys, prefixes, raw

print("=== Level 0 ===")
k, p, _ = s3_list("", "/")
print(f"  Keys: {k[:5]}")
print(f"  Prefixes: {p[:5]}")

print("\n=== Level 1: GEFSv12/ ===")
k, p, _ = s3_list("GEFSv12/", "/")
print(f"  Keys: {k[:5]}")
print(f"  Prefixes: {p[:10]}")

print("\n=== Level 2: GEFSv12/reforecast/ ===")
k, p, _ = s3_list("GEFSv12/reforecast/", "/")
print(f"  Keys: {k[:5]}")
print(f"  Prefixes: {p[:5]}")

print("\n=== Level 3: GEFSv12/reforecast/2000/ ===")
k, p, _ = s3_list("GEFSv12/reforecast/2000/", "/")
print(f"  Keys: {k[:3]}")
print(f"  Prefixes: {p[:5]}")

print("\n=== Level 4: GEFSv12/reforecast/2000/20000101/ ===")
k, p, _ = s3_list("GEFSv12/reforecast/2000/20000101/", "/")
print(f"  Keys: {k[:3]}")
print(f"  Prefixes: {p[:10]}")

print("\n=== Level 5: GEFSv12/reforecast/2000/20000101/c00/ ===")
k, p, _ = s3_list("GEFSv12/reforecast/2000/20000101/c00/", "/")
print(f"  Keys: {k[:3]}")
print(f"  Prefixes: {p[:10]}")
