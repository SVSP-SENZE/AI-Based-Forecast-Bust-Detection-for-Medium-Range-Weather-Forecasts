"""
Inspect the full .idx file for GEFS 2000010100/c00/Days:1-10/apcp_sfc
to find:
  - Which messages represent daily (Day 1) accumulation
  - Byte offsets for those messages
  - File size of full GRIB2 (to compute each message's byte length)
"""
import urllib.request, re

BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com"
init = "2000010100"
member = "c00"
day_range = "Days:1-10"
var = "apcp_sfc"

# Fetch .idx
idx_url = f"{BASE}/GEFSv12/reforecast/2000/{init}/{member}/{day_range}/{var}_{init}_{member}.grib2.idx"
print(f"Fetching: {idx_url}")
req = urllib.request.Request(idx_url, headers={"User-Agent": "test"})
with urllib.request.urlopen(req, timeout=20) as r:
    idx_text = r.read().decode("utf-8", errors="replace")

lines = [l for l in idx_text.strip().split("\n") if l.strip()]
print(f"Total index messages: {len(lines)}\n")

# Format: N:BYTE_OFFSET:d=INIT:VAR:LEVEL:TIME_RANGE:METADATA
print("All APCP messages:")
for ln in lines:
    if "APCP" in ln:
        print(f"  {ln}")

print("\nAll message time ranges (condensed):")
for ln in lines:
    parts = ln.split(":")
    if len(parts) >= 6:
        msg_n   = parts[0]
        offset  = parts[1]
        time_r  = parts[5]
        meta    = parts[6] if len(parts) > 6 else ""
        print(f"  msg={msg_n:>3} | offset={offset:>9} | time={time_r:<25} | {meta}")

# Also get full file size via HEAD
grib_url = f"{BASE}/GEFSv12/reforecast/2000/{init}/{member}/{day_range}/{var}_{init}_{member}.grib2"
print(f"\nGRIB2 file size (HEAD):")
req2 = urllib.request.Request(grib_url, method="HEAD", headers={"User-Agent": "test"})
with urllib.request.urlopen(req2, timeout=10) as r2:
    file_size = int(r2.headers.get("Content-Length", 0))
    print(f"  {file_size:,} bytes = {file_size/1024/1024:.1f} MB")
print(f"  Last message byte offset (approx end): see above")
