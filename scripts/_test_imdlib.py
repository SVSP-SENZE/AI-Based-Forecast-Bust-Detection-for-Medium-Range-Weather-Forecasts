"""Test IMD endpoint and imdlib actual download."""
import urllib.request, os, sys

# Test the new imdlib endpoint
url = "https://imdpune.gov.in/cmpg/Griddata/rainfall.php"
print(f"Testing: {url}")
try:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "test"})
    with urllib.request.urlopen(req, timeout=15) as r:
        print(f"  HTTP {r.status}")
        print(f"  Content-Type: {r.headers.get('Content-Type')}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")

# Also try to actually call imdlib with correct signature
import imdlib
print("\nTesting imdlib.get_data('rain', 2000, 2000) ...")
imd_cache = "data/raw/imd_rain_2000"
os.makedirs(imd_cache, exist_ok=True)
try:
    data = imdlib.get_data("rain", 2000, 2000, fn_format="yearwise", file_dir=imd_cache)
    print(f"  Success! type={type(data)}")
    print(f"  attrs: {[a for a in dir(data) if not a.startswith('_')]}")
    if hasattr(data, "data"):
        print(f"  data.data shape: {data.data.shape}")
        print(f"  data.data dtype: {data.data.dtype}")
        print(f"  Sample [0,60,30]: {data.data[0,60,30]}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")
    # Check what files were created
    for f in os.listdir(imd_cache):
        fsize = os.path.getsize(os.path.join(imd_cache, f))
        print(f"  Found: {f} ({fsize} bytes)")
