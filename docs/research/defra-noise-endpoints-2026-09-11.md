# England Strategic Noise Maps — Verified Endpoints (Defra Data Services Platform)

Checked live on 2026-09-11 by fetching capabilities documents from environment.data.gov.uk.

## Round 3 (2017 data) — vector, WFS confirmed working

| Metric | slug (`/spatialdata/<slug>/wfs`) | WFS typeName | Band attribute | Native CRS | Min mapped band |
|---|---|---|---|---|---|
| Road Lden | `road-noise-lden-england-round-3` | `dataset-fd1c6327-ad77-42ae-a761-7c6a0866523d:Road_Noise_Lden_England_Round_3` | `noiseclass` | EPSG:27700 | 55.0-59.9 |
| Road Lnight | `road-noise-lnight-england-round-3` | `dataset-cc48e728-602a-4e8a-9221-49f661ab58f8:Road_Noise_Lnight_England_Round_3` | `noiseclass` | EPSG:27700 | 50.0-54.9 |
| Rail Lden | `rail-noise-lden-england-round-3` | `dataset-e8e78e12-9297-450b-b875-e0523cb3c9ea:Rail_Noise_Lden_England_Round_3` | `noiseclass` | EPSG:27700 | 55.0-59.9 |
| Rail Lnight | `rail-noise-lnight-england-round-3` | `dataset-f6c0e3b6-3186-4d0a-b0e7-ca32bfb6573f:Rail_Noise_Lnight_England_Round_3` | `noiseclass` | EPSG:27700 | 50.0-54.9 |

All four confirmed via `?service=WFS&request=GetCapabilities&version=2.0.0` + `DescribeFeatureType`. Geometry field is `shape`. Live values run `55.0-59.9 / 60.0-64.9 / 65.0-69.9 / 70.0-74.9 / >=75.0` (Lden) and `50.0-54.9 / … / >=70.0` (Lnight) — polygons only exist ≥55 dB (Lden) / ≥50 dB (Lnight); below that, nothing is drawn.

## Round 4 (2022 data) — raster only for England; no WFS

Round 4 ships as **"<Road|Rail> Noise – All Metrics – England Round 4"** (dataset IDs `562c9d56-7c2d-4d42-83bb-578d6e97a517` road, `3fb3c2d7-292c-4e0a-bd5b-d8e4e1fe2947` rail) with **WMS + WCS only** — GetCapabilities exposes no WFS. There is no England Round-4 NoiseClass vector layer. WMS sub-layers include `Road_Noise_Lden_England_Round_4_All`/`_Maj`, `Road_Noise_Lnight_England_Round_4_All`/`_Maj`, and Rail equivalents. Quirk: rail's real slug is **`noise-data`**, not `rail-noise-all-metrics-england-round-4` (the dataset page's own copy-link buttons point to `/spatialdata/noise-data/wms`).

## Item 5 — point-value model: yes, via Round 4 WMS GetFeatureInfo

Round 4 layers are `queryable="1"`; `GetFeatureInfo` returns an actual dB number (`GRAY_INDEX`), not a band — this is the closest thing to an "Lden model points" product (a rendered 10 m-grid raster, 4 m receptor height, not a discrete point dataset):

```
GET https://environment.data.gov.uk/spatialdata/road-noise-all-metrics-england-round-4/wms
    ?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo
    &LAYERS=Road_Noise_Lden_England_Round_4_All&QUERY_LAYERS=Road_Noise_Lden_England_Round_4_All
    &CRS=EPSG:4326&BBOX=51.49252,-0.22848,51.49268,-0.22832
    &WIDTH=3&HEIGHT=3&I=1&J=1&INFO_FORMAT=application/json&FORMAT=image/png
→ {"type":"FeatureCollection","features":[{"properties":{"GRAY_INDEX":75.29000091552734}}]}
```
Rail Lden near Clapham Junction (51.4646,-0.1706) gave `GRAY_INDEX: 72.22`.

## Round 3 WFS query mechanics (confirmed working)

- **Axis order**: with `bbox=...,urn:ogc:def:crs:EPSG::4326`, order is **lat,lon,lat,lon**. Working example (King St, Hammersmith):
```
https://environment.data.gov.uk/spatialdata/road-noise-lden-england-round-3/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=dataset-fd1c6327-ad77-42ae-a761-7c6a0866523d:Road_Noise_Lden_England_Round_3&outputFormat=application/json&bbox=51.490,-0.230,51.495,-0.226,urn:ogc:def:crs:EPSG::4326
```
→ first feature: `{"noiseclass":"55.0-59.9","gdb_geomattr_data":null}`, geometry in EPSG:27700 (`[523215,178295]`) regardless of query CRS. A bbox with no CRS suffix defaults to EPSG:27700 (lon/lat numbers there return 0 features).
- **CQL_FILTER** works: `INTERSECTS(shape, SRID=4326;POINT(-0.2284 51.4926))` → 1 feature, `noiseclass:"70.0-74.9"`.
- **Simplest for a script**: OGC API - Features, `/spatialdata/<slug>/ogc/features/v1/collections/<Layer_Name>/items?bbox=lon,lat,lon,lat` (plain WGS84 order, no CRS juggling), e.g. collection `Road_Noise_Lden_England_Round_3` — tested, returns GeoJSON already in WGS84.

## Licence

**Open Government Licence v3.0** (stated on every dataset page; CKAN `extras.licence`). Dataset metadata's `notes` field gives attribution verbatim: **"Attribution statement: © Crown Copyright"**. WFS `ows:AccessConstraints`: "made freely available by Defra and its agencies for your use… access [as] an Open Geospatial Consortium (OGC) Web Feature Service."

## Caveats

1. England Round 4 has no WFS/vector NoiseClass layer — only Round 3 (2017-based) gives simple band polygons; a `road-noise-lden-england-round-4` WFS slug does not exist (404/app-shell).
2. Rail Round 4's working slug is `noise-data`, inconsistent with its title — a platform naming inconsistency; verify before hardcoding.
3. `noiseclass` text differs between docs (`75.0+`) and live data (`>=75.0`) — match by regex/prefix, not exact string.
4. WMS `GetFeatureInfo` value depends on BBOX/WIDTH/HEIGHT/I/J alignment; use odd WIDTH/HEIGHT with center I/J (or a ~10 m bbox) to hit the intended pixel, not a neighbor.
5. Round 4 raster renders down to 35 dB (Lnight)/40 dB (others) vs Round 3 vector's 50/55 dB floor, and uses 2021 traffic data vs Round 3's 2017 — the two rounds are not directly comparable at low levels.
