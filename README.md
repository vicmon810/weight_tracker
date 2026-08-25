# HealthPi

HealthPi is a small, self-hosted health data pipeline that syncs a daily summary from Apple Health to a Raspberry Pi.

The minimum MVP answers one question: **can an iPhone reliably send weight, steps, and sleep data to a private SQLite database on the local network?**

## What works today

- Reads weight, steps, and sleep from Apple Health
- Syncs from a physical iPhone with one button
- Stores one SQLite record per Auckland calendar date
- Updates the existing record when the same date is synced again
- Preserves previously stored values when a later sync omits a field
- Shows loading, success, and retryable error states

## Architecture

```text
Apple Health
  weight · steps · sleep
          │
          ▼
SwiftUI iPhone app
  Sync Today
          │  HTTP on a trusted private LAN
          ▼
FastAPI on Raspberry Pi
          │
          ▼
SQLite · daily_health
```

## Requirements

- Raspberry Pi or another machine with Python 3.11+
- Xcode 15.2+
- Physical iPhone running iOS 17.2+
- iPhone and Raspberry Pi connected to the same trusted private network

## Quick start

### 1. Start the API

On the Raspberry Pi:

```bash
git clone https://github.com/vicmon810/weight_tracker.git
cd weight_tracker

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
./start.sh
```

The server listens on port `8999` and creates `health.db` in the repository directory.

Check that it is reachable, replacing `PI_IP_ADDRESS` with the Pi's LAN IP:

```bash
curl http://PI_IP_ADDRESS:8999/health
```

Expected response:

```json
{"status":"ok"}
```

### 2. Configure the iPhone app

1. Open `HealthPi/HealthPi.xcodeproj` in Xcode.
2. Open `HealthPi/HealthPi/Info.plist`.
3. Set `HealthAPIBaseURL` to the Pi's address, for example:

   ```text
   http://192.168.1.20:8999
   ```

4. Select your Apple development team.
5. Select a physical iPhone and run the app.

### 3. Sync Apple Health

1. Tap **Sync Today**.
2. Allow access to weight, steps, and sleep when iOS requests permission.
3. Wait for **Synced successfully**.

HealthKit does not distinguish denied read permission from missing data. If every requested value is unavailable, HealthPi reports that no health data could be synced.

## Verify the saved data

Use today's date in the `Pacific/Auckland` timezone:

```bash
curl http://PI_IP_ADDRESS:8999/daily-health/2026-08-25
```

Example response:

```json
{
  "date": "2026-08-25",
  "weight_kg": 72.4,
  "steps": 8321,
  "sleep_hours": 7.5,
  "created_at": "2026-08-24T20:00:00+00:00",
  "updated_at": "2026-08-24T20:00:00+00:00"
}
```

Tap **Sync Again** and query the same endpoint. The date remains a single record and its available values are updated.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Check server availability |
| `POST` | `/daily-health` | Create or update one daily summary |
| `GET` | `/daily-health/{date}` | Read one summary by date |

Example payload:

```json
{
  "date": "2026-08-25",
  "weight_kg": 72.4,
  "steps": 8321,
  "sleep_hours": 7.5
}
```

At least one health value is required. Weight must be positive, steps cannot be negative, and sleep must be between 0 and 24 hours.

## Tests

Run the backend test suite:

```bash
.venv/bin/python -m pytest -q
```

Compile the app and iOS unit tests without code signing:

```bash
xcodebuild \
  -project HealthPi/HealthPi.xcodeproj \
  -scheme HealthPi \
  -destination 'generic/platform=iOS Simulator' \
  build-for-testing \
  CODE_SIGNING_ALLOWED=NO
```

Run the `HealthPiTests` target from Xcode when an iOS Simulator is installed. It covers:

- Sync sequencing and retry behavior
- Auckland calendar-date encoding
- Overlapping sleep interval merging

## MVP boundaries

This release intentionally excludes:

- Authentication and public internet access
- Background synchronization
- Dashboards and trend analysis
- AI or LLM-generated insights
- Multiple users

The API currently trusts the local network. **Do not expose port 8999 directly to the public internet.**

## Project layout

```text
HealthPi/                 SwiftUI application and iOS tests
api/health_api.py        FastAPI application and SQLite storage
tests/                   Backend API tests
start.sh                 Raspberry Pi server entry point
requirements.txt         Python dependencies
docs/superpowers/        MVP design and implementation plan
```
