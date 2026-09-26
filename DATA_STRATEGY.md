# DATA_STRATEGY.md — Real Data Sourcing for Forecast Bust Detection

Legend: **[FACT]** verified via research below · **[ASSUMPTION]** · **[RECOMMENDATION]** · **[OPTION]**

---

## 1. The Core Requirement (restated precisely)

We need, for the same location and valid time, three aligned things:
1. **A historical forecast**, issued at time *t*, valid for time *t+n* (n = lead time in days), for the variable(s) we model.
2. **The real-world "truth"** for that same location/valid-time — either direct observations or the best available reanalysis proxy for observations.
3. Enough **temporal depth and density** (many issue dates × many lead times × many locations) to fit a bust/error model without overfitting to a handful of events.

The single biggest risk to this whole project is picking a data source that has *forecasts* but no *forecast archive* (most public weather APIs only expose "the current forecast," overwritten daily, with no historical run archive) — this looks fine on day 1 and fails silently on day 2 once we realize we can't reconstruct "what did the forecast for next Tuesday look like three days ago." We explicitly checked for this failure mode below.

---

## 2. Candidate Sources Evaluated

### 2.1 Open-Meteo (Historical Forecast API + Previous Runs API + Single Runs API + ERA5 Archive) — **[RECOMMENDATION: PRIMARY]**

**[FACT]** Open-Meteo is a free weather API aggregating 30+ operational NWP models (ECMWF IFS, NOAA GFS, DWD ICON, Météo-France, JMA, KMA, UK Met Office, BOM, CMA and more), with no API key required for non-commercial use, served as simple JSON over HTTP.

**[FACT]** It offers four complementary historical layers that map almost exactly onto our requirement:
- **ERA5 reanalysis** — hourly, gap-free, global, from January 1940 to present, 0.1–0.25° resolution. This is our **truth/reference** layer.
- **Historical Forecast archive** — from 2021, in the same JSON schema as the live Forecast API; designed for bias-correction/post-processing pipelines. This is a first candidate for the **forecast** layer.
- **Previous Runs API** — continuous time series at a *fixed lead-time offset* (1–7 days), from January 2024, specifically built for **lead-time-stratified skill analysis** — this is exactly our Day-1…Day-7 use case with almost zero engineering overhead.
- **Single Runs API** — archived *individual model runs* selected by exact initialization time (`run=YYYY-MM-DDThh:mm`), giving the *complete* forecast horizon of that one run. ECMWF IFS HRES (9 km) is archived from **March 14, 2024** onward at 00/06/12/18 UTC; other models (GFS, ICON, AROME) from **September 2025** onward. This is the cleanest way to reconstruct "what did the Day-1..Day-10 forecast look like, issued on this exact date" without any look-ahead leakage, because each run is stored exactly as it was produced.

**Assessment vs. requirements:**
| Criterion | Result |
|---|---|
| Availability | **[FACT]** No signup/API key, generous free non-commercial use |
| Historical depth (forecast side) | **[FACT]** Single Runs: ECMWF IFS from Mar 2024 (~2.5 yrs by demo time); other models from Sep 2025 (shorter) |
| Historical depth (truth side) | **[FACT]** ERA5 from 1940 — effectively unlimited depth |
| Lead time | **[FACT]** Up to 15-day horizon per run (IFS HRES) |
| Variables | **[FACT]** Rainfall/precipitation, temperature, wind, humidity, pressure all present in the standard variable set |
| Spatial resolution | **[FACT]** ~9 km (IFS HRES) to ~11 km global; ERA5 0.25° (~28 km) |
| India coverage | **[FACT]** Global coverage, so India included |
| Access difficulty | **[FACT]** Trivial — plain HTTP GET, JSON, point/small-grid queries; no GRIB parsing needed |
| Storage burden | Low — JSON responses for a bounded region/date range are small (MB, not GB) |
| Licensing | **[FACT]** CC BY 4.0 |
| Reproducibility | High — deterministic historical queries |
| True forecast vs. reanalysis | **[FACT]** Single Runs / Previous Runs are genuine archived forecast output, not reanalysis — satisfies "must be real forecast data" |

**[ASSUMPTION]** For rainfall specifically, we treat ERA5 (or, where feasible, IMD gridded rainfall as a cross-check) as "truth," acknowledging that ERA5 rainfall itself has known biases versus IMD's dense-gauge product over India — we state this limitation explicitly rather than hide it.

### 2.2 ECMWF TIGGE Archive (via ECDS) — **[RECOMMENDATION: BACKUP / ENSEMBLE-SPREAD FEATURE SOURCE]**

**[FACT]** TIGGE (THORPEX Interactive Grand Global Ensemble) is a public, non-commercial-research archive of global medium-range **ensemble** forecasts from ~10–13 NWP centres (including NCEP/GFS and ECMWF), available since October 2006, 6-hourly, GRIB2, typical forecast length 10–15 days, ensemble sizes 12–51 members, currently archived through ECMWF's ECDS (Earth-observation/Climate Data Store) with a public non-commercial research licence and a ~48-hour access delay for the most recent data (irrelevant for us since we only need historical dates).

**Assessment**: Excellent historical depth (2006–present) and the *only* practical free source of true multi-member **ensemble spread**, which is scientifically the most natural feature for forecast uncertainty. However: GRIB2 format requires `eccodes`/`cfgrib` parsing, MARS/ECDS request queuing can be slow, and per-file downloads can be large. **[RECOMMENDATION]** Use TIGGE only as a Tier-2/stretch enhancement (ensemble-spread feature) if Day-1 data work finishes early — do not make it the Day-1 dependency, because its access friction risks burning the most time-critical day of a 3-day sprint.

### 2.3 ERA5 via Copernicus CDS API directly — **[OPTION, not primary]**

**[FACT]** ERA5 is also downloadable directly via the `cdsapi` Python client against the Copernicus Climate Data Store, requiring a free account, an API token in `~/.cdsapirc`, and per-dataset licence acceptance; data is delivered as GRIB/NetCDF. **[RECOMMENDATION]** We prefer pulling ERA5 *through Open-Meteo's ERA5 archive endpoint* instead of the raw CDS API, because Open-Meteo returns plain JSON at exactly the point/region we ask for, with no GRIB/NetCDF handling and no account/token setup — strictly less engineering for an identical scientific data source. We keep the direct CDS path documented here only as a fallback if Open-Meteo's ERA5 endpoint has an outage or a coverage gap for our chosen sub-region.

### 2.4 IMD Gridded Rainfall (0.25°, 1901–present) — **[OPTION: India-specific truth cross-check]**

**[FACT]** IMD publishes a high-resolution (0.25°×0.25°) daily gridded rainfall dataset for India spanning 1901–present, distributed as binary `.grd`/ASCII files; an open-source R package (`imdR`) wraps IMD's own download endpoints, including a "provisional real-time" feed for recent dates. Some third-party mirrors (e.g., a Stanford Libraries copy) restrict redistribution to their own institutional affiliates, so we do **not** rely on any restricted mirror — only IMD's own public distribution via `imdR`/IMD's site is used, and only as an optional accuracy cross-check against ERA5 rainfall over India, not as the primary pipeline dependency (to avoid a hard dependency on an R toolchain and an external government endpoint's uptime during the sprint).

### 2.5 NOAA GFS / HRRR reforecast archives — **[OPTION, not selected]**

**[FACT]** NOAA maintains various GFS reforecast/archive products, but access typically requires large-volume GRIB downloads from NOAA's cloud buckets (AWS Open Data / NOMADS) with significant storage/bandwidth burden for global fields, and less turnkey point-extraction than Open-Meteo's JSON layer. **[RECOMMENDATION]** Not used in the 3-day MVP; documented as a future scale-up path once the pipeline needs true native-resolution GFS fields beyond what Open-Meteo re-serves.

---

## 3. Selected Strategy

**Primary data strategy [RECOMMENDATION]:**
- **Forecast side**: Open-Meteo **Previous Runs API** (lead-time-stratified series, from Jan 2024) as the main workhorse for Day 1–7, supplemented by **Single Runs API** (ECMWF IFS HRES, from Mar 2024) where we need the full Day 1–10/15 horizon of one exact issuance.
- **Truth side**: Open-Meteo **ERA5 archive** endpoint, queried at the same coordinates/valid-times.
- **Geography**: a bounded India sub-region (final bounding box decided in Task 02) chosen for strong monsoon-season signal and enough grid points for meaningful spatial variation without an unmanageable download volume.
- **Variable**: rainfall (precipitation_sum / hourly precipitation aggregated to daily) as primary; temperature, wind, humidity, pressure pulled alongside as derived/contextual features if time allows, per PRD MVP scope.
- **Window**: as much overlap between Previous-Runs/Single-Runs archive availability and "far enough in the past to have plenty of issue dates" as practical — realistically the ~18–24 months preceding the hackathon date, prioritizing at least one full monsoon season (June–September) for rainfall-bust density.

**Backup data strategy [RECOMMENDATION]:**
- If Open-Meteo has a coverage gap or rate-limit issue for the chosen region/window: fall back to direct **ECMWF TIGGE** pulls (control/high-res member only, to avoid full-ensemble GRIB parsing complexity) for the forecast side, still paired with ERA5 truth (via Open-Meteo or direct CDS).
- If rainfall-specific truth quality is questioned: cross-check a sample against **IMD gridded rainfall** for the same sub-region/dates.

**Why this is the right call for a 3-day AI-agent build:** every other credible route (raw TIGGE GRIB, raw CDS ERA5, NOAA reforecast buckets) trades scientific "purity" for engineering time we do not have; Open-Meteo gives us real, non-synthetic, properly time-stamped forecast-vs-truth pairs through a single simple interface, which is the single highest-leverage decision in this entire project.

## 4. What We Will NOT Do

- We will **not** treat Open-Meteo's *live* "Forecast API" (the continuously-updated, non-versioned endpoint) as a source of historical forecasts — that endpoint overwrites itself daily and would silently leak future information into "historical" training rows. Only the **Historical Forecast / Previous Runs / Single Runs** archival endpoints, which are explicitly versioned by issue time, are used for training data.
- We will not download full-resolution global GRIB fields when a point/small-region JSON query answers the same scientific question at a fraction of the engineering cost.
- We will not fabricate any forecast-truth pair. If a data gap exists for a specific date/location, that row is dropped, not interpolated into a synthetic value, unless explicitly flagged as a documented placeholder never used in the final demo numbers.

## 5. Estimated Size & Preprocessing Burden

- **[ASSUMPTION]** For a sub-region of roughly 8–15 grid points/cities, 5 lead times, daily issuance over an 18–24 month window, the raw JSON pull is on the order of low tens of thousands of forecast-issue/lead-time rows plus a matching ERA5 truth series — comfortably a few hundred MB at most, well within local-machine/Colab-free-tier limits.
- Preprocessing burden is dominated by (a) aligning forecast-valid-time to the nearest ERA5 hourly/daily truth value, (b) handling any missing hours/gaps, and (c) computing rolling climatology per grid cell for anomaly features — all doable in pandas/xarray without heavy compute.
