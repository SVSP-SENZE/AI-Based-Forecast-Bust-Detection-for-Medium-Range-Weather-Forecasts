"""
Diagnose GRIB2 Data Representation Template (DRT) of GEFS APCP messages.
DRT=3 is 'complex packing with spatial differencing'.
Read Section 5 metadata to understand encoding.
"""
import urllib.request, struct

BASE = "https://noaa-gefs-retrospective.s3.amazonaws.com"
INIT = "2000010100"
MEMBER = "c00"
GRIB_URL = f"{BASE}/GEFSv12/reforecast/2000/{INIT}/{MEMBER}/Days:1-10/apcp_sfc_{INIT}_{MEMBER}.grib2"

# Fetch one full message (0-6h, msg 2): bytes 422515 to 925322
print("Fetching msg 2 (0-6h APCP): bytes 422515-925322")
req = urllib.request.Request(GRIB_URL, headers={
    "User-Agent": "test", "Range": "bytes=422515-925322"})
with urllib.request.urlopen(req, timeout=30) as r:
    data = r.read()
print(f"Downloaded: {len(data)} bytes")

def read_uint(buf, offset, n):
    return int.from_bytes(buf[offset:offset+n], "big")

def grib_signed_lat(v):
    if v & 0x80000000:
        return -float(v & 0x7FFFFFFF) / 1e6
    return float(v) / 1e6

pos = 0
while pos < len(data) - 4:
    sec_len = read_uint(data, pos, 4)
    if sec_len == 0: break
    sec_num = data[pos+4]
    print(f"\n--- Section {sec_num} (len={sec_len}, pos={pos}) ---")
    
    if sec_num == 0:  # Indicator
        discipline = data[pos+6]
        edition = data[pos+7]
        total = read_uint(data, pos+8, 8)
        print(f"  Discipline={discipline}, Edition={edition}, Total={total}")
        
    elif sec_num == 1:  # Identification
        center = read_uint(data, pos+5, 2)
        subcenter = read_uint(data, pos+7, 2)
        master_table = data[pos+9]
        ref_time_sig = data[pos+11]
        year = read_uint(data, pos+12, 2)
        month = data[pos+14]
        day = data[pos+15]
        hour = data[pos+16]
        minute = data[pos+17]
        second = data[pos+18]
        print(f"  Center={center}, SubCenter={subcenter}, MasterTable={master_table}")
        print(f"  RefTime={year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}Z")
        print(f"  RefTimeSig={ref_time_sig} (1=start of forecast)")
        
    elif sec_num == 3:  # Grid Definition
        gdt = read_uint(data, pos+11, 2)
        ni = read_uint(data, pos+30, 4)
        nj = read_uint(data, pos+34, 4)
        la1 = grib_signed_lat(read_uint(data, pos+46, 4))
        lo1 = read_uint(data, pos+50, 4) / 1e6
        la2 = grib_signed_lat(read_uint(data, pos+55, 4))
        lo2 = read_uint(data, pos+59, 4) / 1e6
        di  = read_uint(data, pos+63, 4) / 1e6
        dj  = read_uint(data, pos+67, 4) / 1e6
        print(f"  GDT={gdt} (0=lat/lon)")
        print(f"  Ni={ni}, Nj={nj}")
        print(f"  La1={la1:.3f}, Lo1={lo1:.3f}")
        print(f"  La2={la2:.3f}, Lo2={lo2:.3f}")
        print(f"  Di={di:.4f} deg, Dj={dj:.4f} deg")
        
    elif sec_num == 4:  # Product Definition
        pdt = read_uint(data, pos+7, 2)
        cat = data[pos+9]
        num = data[pos+10]
        print(f"  PDT={pdt}, Category={cat}, Number={num}")
        # time range for APCP
        if pdt in (0,8):
            hrs = read_uint(data, pos+17, 4)
            unit = data[pos+16]  # time range unit: 1=hour
            print(f"  FcstTime={hrs}h (unit_code={unit})")
        if pdt == 8:  # average/accum
            year2 = read_uint(data, pos+34, 2)
            mon2 = data[pos+36]; day2 = data[pos+37]
            hr2 = data[pos+38]; mn2 = data[pos+39]; sc2 = data[pos+40]
            n_time_ranges = data[pos+41]
            stat_proc = data[pos+43]  # 1=accum
            inc_type = data[pos+44]
            time_unit = data[pos+45]
            time_len = read_uint(data, pos+46, 4)
            print(f"  EndOfOverall={year2}-{mon2:02d}-{day2:02d} {hr2:02d}:{mn2:02d}Z")
            print(f"  N_time_ranges={n_time_ranges}, StatProc={stat_proc}(1=accum), TimeLen={time_len}h")
            
    elif sec_num == 5:  # Data Representation
        n_packed = read_uint(data, pos+5, 4)
        drt = read_uint(data, pos+9, 2)
        print(f"  N_packed={n_packed}, DRT={drt}")
        if drt == 0:  # Simple packing
            ref_val = struct.unpack(">f", data[pos+11:pos+15])[0]
            E = struct.unpack(">h", data[pos+15:pos+17])[0]
            D = struct.unpack(">h", data[pos+17:pos+19])[0]
            nbits = data[pos+19]
            print(f"  RefVal={ref_val}, E={E}, D={D}, NbitsPerVal={nbits}")
        elif drt == 2:  # Complex packing
            ref_val = struct.unpack(">f", data[pos+11:pos+15])[0]
            E = struct.unpack(">h", data[pos+15:pos+17])[0]
            D = struct.unpack(">h", data[pos+17:pos+19])[0]
            nbits = data[pos+19]
            orig_type = data[pos+20]
            print(f"  Complex packing: RefVal={ref_val}, E={E}, D={D}, Nbits={nbits}, OrigType={orig_type}")
            # Section 5 for DRT=2 has more fields
            n_groups = read_uint(data, pos+21, 4)
            group_width_ref = data[pos+25]
            group_width_bits = data[pos+26]
            group_len_ref = read_uint(data, pos+27, 4)
            group_len_incr = data[pos+31]
            last_group_len = read_uint(data, pos+32, 4)
            scaled_group_len_bits = data[pos+36]
            print(f"  N_groups={n_groups}, GroupWidthRef={group_width_ref}, GroupWidthBits={group_width_bits}")
            print(f"  GroupLenRef={group_len_ref}, GroupLenIncr={group_len_incr}")
            print(f"  ScaledGroupLenBits={scaled_group_len_bits}")
        elif drt == 3:  # Complex packing with spatial differencing
            ref_val = struct.unpack(">f", data[pos+11:pos+15])[0]
            E = struct.unpack(">h", data[pos+15:pos+17])[0]
            D = struct.unpack(">h", data[pos+17:pos+19])[0]
            nbits = data[pos+19]
            orig_type = data[pos+20]
            n_groups = read_uint(data, pos+21, 4)
            group_width_ref = data[pos+25]
            group_width_bits = data[pos+26]
            group_len_ref = read_uint(data, pos+27, 4)
            group_len_incr = data[pos+31]
            last_group_len = read_uint(data, pos+32, 4)
            scaled_group_len_bits = data[pos+36]
            order = data[pos+37]   # spatial differencing order (1 or 2)
            extra_bytes = data[pos+38]  # octets for extra descriptors
            print(f"  Complex+SpatDiff: RefVal={ref_val}, E={E}, D={D}, Nbits={nbits}")
            print(f"  OrigType={orig_type}, N_groups={n_groups}")
            print(f"  GroupWidthRef={group_width_ref}, GroupWidthBits={group_width_bits}")
            print(f"  GroupLenRef={group_len_ref}, GroupLenIncr={group_len_incr}")
            print(f"  LastGroupLen={last_group_len}, ScaledGroupLenBits={scaled_group_len_bits}")
            print(f"  SpatialDiffOrder={order}, ExtraDescOctets={extra_bytes}")
            print(f"  Section 5 bytes[37:50] hex: {data[pos+37:pos+50].hex()}")
        else:
            print(f"  DRT={drt} - raw sec5 bytes: {data[pos+9:pos+40].hex()}")
            
    elif sec_num == 6:  # Bitmap
        bmi = data[pos+5]
        print(f"  BitmapIndicator={bmi} (255=no bitmap)")
        
    elif sec_num == 7:  # Data
        print(f"  Data section: {sec_len-5} bytes of packed values")
        print(f"  First 20 bytes hex: {data[pos+5:pos+25].hex()}")
        
    elif sec_num == 8:
        print("  END section")
        break
    
    pos += sec_len

print("\nDone.")
