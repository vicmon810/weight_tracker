# HealthPi minimum MVP

HealthPi currently proves one complete path:

```text
Apple Health (weight, steps, sleep)
        ↓
iPhone app (one Sync Today button)
        ↓ private LAN
FastAPI on Raspberry Pi
        ↓
SQLite daily_health table
```

The same calendar date is idempotent: syncing again updates the existing row instead of creating a duplicate. Missing fields do not erase values already stored for that day.

## 1. Run the Raspberry Pi API

Requirements: Python 3.11 or newer and an iPhone/Pi on the same trusted private network.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./start.sh
```

The API listens on `0.0.0.0:8999` and creates `health.db` in the repository directory.

Check it from another machine on the LAN:

```bash
curl http://PI_IP_ADDRESS:8999/health
```

Expected response:

```json
{"status":"ok"}
```

## 2. Configure and run the iPhone app

1. Open `HealthPi/HealthPi.xcodeproj` in Xcode.
2. In `HealthPi/HealthPi/Info.plist`, replace the `HealthAPIBaseURL` value with the Pi's LAN address, for example `http://192.168.1.20:8999`.
3. Select your Apple development team and a physical iPhone. HealthKit data is not available in a useful form on a generic build destination.
4. Build and run, tap **Sync Today**, and allow access to weight, steps, and sleep when iOS asks.

HealthKit does not reveal whether read permission was denied; denied data appears the same as no data. The app reports an error if all three values are unavailable.

## 3. Verify the stored record

Replace the date below with today's date in the `Pacific/Auckland` timezone:

```bash
curl http://PI_IP_ADDRESS:8999/daily-health/2026-08-24
```

Example response:

```json
{
  "date": "2026-08-24",
  "weight_kg": 72.4,
  "steps": 8321,
  "sleep_hours": 7.5,
  "created_at": "2026-08-24T08:00:00+00:00",
  "updated_at": "2026-08-24T08:00:00+00:00"
}
```

Tap **Sync Again** and verify the endpoint still returns one record for the date.

## Tests

Backend:

```bash
.venv/bin/python -m pytest -q
```

iOS tests compile as part of:

```bash
xcodebuild \
  -project HealthPi/HealthPi.xcodeproj \
  -scheme HealthPi \
  -destination 'generic/platform=iOS Simulator' \
  build-for-testing \
  CODE_SIGNING_ALLOWED=NO
```

Run the `HealthPiTests` target in Xcode with an installed iOS Simulator. The tests cover sync sequencing and retry, Auckland date encoding, and overlapping sleep interval merging.

## Deliberately outside this MVP

Authentication, remote internet access, dashboards, trend analysis, AI/LLM features, background sync, and multi-user support are future milestones. The HTTP API assumes a trusted private LAN and must not be exposed directly to the public internet.
