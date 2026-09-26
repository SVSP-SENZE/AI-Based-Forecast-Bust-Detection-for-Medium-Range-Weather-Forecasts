"""Probe GEFS S3: correct path is YYYYMMDDHH (10-digit), then member/Days."""
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
    return keys, prefixes

# Correct: 10-digit init time
print("=== Level 4 (correct): GEFSv12/reforecast/2000/2000010100/ ===")
k, p = s3_list("GEFSv12/reforecast/2000/2000010100/", "/")
print(f"  Keys: {k[:5]}")
print(f"  Prefixes: {p[:10]}")

print("\n=== Level 5: c00 member ===")
k, p = s3_list("GEFSv12/reforecast/2000/2000010100/c00/", "/")
print(f"  Keys: {k[:3]}")
print(f"  Prefixes: {p[:10]}")

# Also show size of a sample file
print("\n=== HEAD request: one GRIB2 file size ===")
# typical key: GEFSv12/reforecast/YYYY/YYYYMMDDHH/c00/Days:1-10/apcp_sfc_YYYYMMDDHH_c00.grib2
# Build sample key from actual listing
if p:
    sub = p[0]
    k2, p2 = s3_list(sub, "/")
    print(f"  Sub-prefixes of {sub}: {p2[:10]}")
    print(f"  Keys: {k2[:5]}")
    if p2:
        sub2 = p2[0]
        k3, p3 = s3_list(sub2, "/", max_keys=5)
        print(f"  Sub-prefixes of {sub2}: {p3[:5]}")
        print(f"  Keys: {k3[:5]}")
        # Try HEAD on first key to get size
        if k3:
            key = k3[0]
            head_url = f"https://noaa-gefs-retrospective.s3.amazonaws.com/{key}"
            try:
                req = urllib.request.Request(head_url, method="HEAD", headers={"User-Agent": "test"})
                with urllib.request.urlopen(req, timeout=10) as r:
                    cl = r.headers.get("Content-Length", "?")
                    ct = r.headers.get("Content-Type", "?")
                    print(f"\n  SAMPLE FILE: {key}")
                    print(f"  Size: {cl} bytes ({int(cl)//1024//1024} MB)" if cl != "?" else f"  Size: unknown")
                    print(f"  Content-Type: {ct}")
            except Exception as e:
                print(f"  HEAD failed: {e}")
