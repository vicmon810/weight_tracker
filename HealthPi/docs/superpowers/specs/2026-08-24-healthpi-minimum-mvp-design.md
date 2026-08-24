# HealthPi Minimum MVP Design

## Status

Approved in conversation on 2026-08-24.

## Objective

Deliver one reliable end-to-end workflow: an iPhone reads the user's latest weight, today's step count, and last night's sleep duration from HealthKit, then stores that daily snapshot in SQLite on the user's Raspberry Pi.

The MVP proves the data pipeline works. It does not attempt to prove the broader AI-assistant product vision.

## Success Criteria

The MVP is complete when:

1. A user can authorize HealthKit access on a physical iPhone.
2. One explicit action reads weight, steps, and sleep and sends one HTTP request.
3. The Raspberry Pi API validates and stores the snapshot in SQLite.
4. Repeating a sync for the same local calendar date updates the existing row rather than creating a duplicate.
5. Missing HealthKit values are stored as `null` without blocking the other values.
6. The app distinguishes loading, success, authorization failure, missing data, connection failure, and server failure.
7. Automated backend tests cover validation, persistence, and idempotent updates.
8. A second developer can start and verify the system using the README.

## Non-goals

The following are deliberately excluded:

- AI or LLM insights
- Web dashboard and charts
- Voice input
- Mood, diet, exercise-minute, and free-text check-ins
- Background or automatic sync
- Offline queues and automatic retries
- Authentication, accounts, and multi-user support
- Cloud deployment
- Trend analysis
- SwiftData persistence in the iOS app
- Apple clinical Health Records access

These features may be revisited only after the MVP acceptance criteria pass.

## User Flow

1. The user opens HealthPi.
2. The user grants HealthKit read permission.
3. The user taps **Read and Sync**.
4. The app reads the three health values concurrently.
5. The screen shows the retrieved values.
6. The app sends one daily snapshot to the configured Raspberry Pi endpoint.
7. The API inserts or updates the row identified by the snapshot date.
8. The app shows either a successful sync time or a specific error.

The MVP remains manually triggered. No app-launch or background sync is performed.

## Architecture

The system has four focused units:

### HealthKit provider

The iOS HealthKit provider owns authorization and queries. It returns a `HealthSummary` value and reports errors explicitly instead of using `nil` for every failure condition.

```swift
struct HealthSummary {
    let date: Date
    let weightKilograms: Double?
    let steps: Int?
    let sleepHours: Double?
}
```

Individual metric values remain optional because HealthKit may legitimately contain no sample. Authorization or query failures are errors, not missing values.

### API client

The iOS API client converts `HealthSummary` to the wire payload and owns HTTP behavior. It receives its base URL through initialization rather than reading a hard-coded address from the view model.

The client sends exactly one request per user action and treats only HTTP 2xx responses as success.

### View model and view

The view model coordinates authorization, loading, and synchronization. It depends on abstractions for the HealthKit provider and API client so its state transitions can be tested without a physical device or live server.

The SwiftUI view renders values and state. It contains no HealthKit, URLSession, date formatting, or payload-building logic.

### FastAPI persistence service

The backend validates requests, performs an atomic SQLite upsert, and returns named JSON fields. Database connection and schema initialization are isolated from endpoint handlers sufficiently for tests to use a temporary database.

## API Contract

### `POST /daily-health`

Request:

```json
{
  "date": "2026-08-24",
  "weight_kg": 78.2,
  "steps": 8560,
  "sleep_hours": 7.5
}
```

Rules:

- `date` is required and uses ISO `YYYY-MM-DD` format.
- `weight_kg`, `steps`, and `sleep_hours` are nullable.
- `weight_kg`, when present, must be greater than zero.
- `steps`, when present, must be a non-negative integer.
- `sleep_hours`, when present, must be between 0 and 24 inclusive.
- At least one metric must be non-null.
- A repeated request for the same date updates that row.
- Null fields do not erase previously stored non-null values during an update. This supports partial HealthKit availability.

Successful response:

```json
{
  "status": "ok",
  "date": "2026-08-24"
}
```

Validation errors use FastAPI's structured 422 response. Unexpected persistence errors return 500 without exposing internal paths or SQL.

### `GET /daily-health/{date}`

This verification endpoint returns the stored object with named fields. An unknown date returns 404. Listing, filtering, pagination, and dashboard-oriented endpoints are outside the MVP.

## SQLite Schema

```sql
CREATE TABLE IF NOT EXISTS daily_health (
    date TEXT PRIMARY KEY,
    weight_kg REAL,
    steps INTEGER,
    sleep_hours REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

`date` is the idempotency key. The API uses one `INSERT ... ON CONFLICT(date) DO UPDATE` statement. `created_at` remains unchanged on updates; `updated_at` changes on every accepted sync.

The MVP uses the iPhone's local calendar date in `Pacific/Auckland`, formatted before transmission. This intentionally defines a daily snapshot from the user's perspective rather than from UTC. Supporting travel and multiple user time zones is deferred.

## Health Data Semantics

- **Weight:** the latest HealthKit body-mass sample available at sync time. It may have been recorded before the snapshot date.
- **Steps:** the cumulative step count from local start-of-day to the sync time.
- **Sleep:** the sum of asleep intervals in the local noon-to-noon window ending at today's noon.

Steps are stored as steps. They are not converted into exercise minutes because that conversion has no valid basis in the available data.

The sleep implementation must include the HealthKit asleep categories supported by the deployment target and avoid double-counting overlapping samples. Exact sleep-stage reporting is outside the MVP.

## UI States

The screen displays the three metric values, an authorization action when required, one **Read and Sync** action, and one status area.

The view model exposes an explicit state equivalent to:

```text
idle
authorizing
loadingHealthData
syncing
success(date/time)
failure(user-facing message)
```

The action is disabled while authorization, loading, or synchronization is active. This prevents accidental concurrent requests in addition to the backend's idempotency protection.

## Configuration and Networking

The Raspberry Pi base URL is supplied from app configuration and is not embedded in `HealthViewModel`. Development may use a checked-in example value, while the real LAN address remains locally configurable.

The API and all supporting scripts use port `8999`. The iOS app requires the minimum local-network and App Transport Security configuration necessary for HTTP access to the LAN service. Broad network-security exceptions are not added without necessity.

## Error Handling

User-facing failures are grouped into:

- HealthKit unavailable
- HealthKit permission not granted
- HealthKit query failure
- Invalid API configuration
- Raspberry Pi unreachable or timed out
- API validation failure
- API server failure

The UI does not report success when there is no HTTP response or when the response status is outside 200–299. Debug prints containing health payloads are removed from production code.

## Testing Strategy

### Backend tests

Tests use FastAPI's test client and an isolated temporary SQLite database. They cover:

1. Creating a complete daily snapshot.
2. Reading it back by date.
3. Updating the same date without increasing row count.
4. Preserving an existing value when an update supplies `null`.
5. Accepting a valid partial snapshot.
6. Rejecting a snapshot with all metrics null.
7. Rejecting invalid dates and metric ranges.
8. Returning 404 for a missing date.

### iOS tests

Fake HealthKit and API implementations cover view-model behavior:

1. Successful read and sync transitions to success and invokes the API once.
2. Missing weight still syncs steps and sleep.
3. HealthKit failure does not call the API.
4. API failure produces failure state.
5. A second action while syncing does not create a concurrent request.

HealthKit queries themselves require physical-device acceptance testing because normal unit tests cannot reproduce the user's Health store.

### Manual acceptance

On a physical iPhone and Raspberry Pi:

1. Grant permission and synchronize.
2. Confirm the SQLite row with the GET endpoint.
3. Synchronize again and confirm one row remains.
4. Change available HealthKit data, synchronize, and confirm the row updates.
5. Stop the API and confirm the app reports a connection failure.
6. Restart the API and confirm synchronization recovers.

## Delivery Milestones

### M0: Protect and reconcile the repository

- Preserve current uncommitted work on a dedicated feature branch.
- Exclude Xcode user-state files.
- Reconcile the local branch with the five remote commits.
- Choose the remote `api/health_api.py` layout as the canonical backend location.
- Verify the baseline before MVP implementation.

### M1: Tested backend slice

- Add the schema and migration/initialization behavior.
- Implement and test POST and GET.
- Standardize the port at 8999.
- Verify idempotency using API tests and direct database assertions.

### M2: Testable iOS slice

- Introduce the health summary model and provider/client boundaries.
- Implement one read-and-sync action using Swift concurrency.
- Remove the duplicate request and step-to-exercise conversion.
- Move the base URL to configuration.
- Add view-model tests and simplify the screen.

### M3: End-to-end acceptance

- Run the API on the Raspberry Pi.
- Test from a physical iPhone over the LAN.
- Complete every manual acceptance scenario.
- Document setup, configuration, verification, and known limitations.

## Risks and Mitigations

- **Dirty, divergent Git state:** isolate and reconcile before implementation; never bulk-stage existing changes.
- **HealthKit only works meaningfully on device:** keep business coordination testable with fakes and reserve query validation for explicit device tests.
- **LAN address changes:** inject configuration and document how to update it.
- **Duplicate requests:** disable the UI during sync, send once, and enforce date-based idempotency on the server.
- **Schema drift from the old check-in model:** use one canonical backend module and a dedicated `daily_health` table rather than partially mutating the broken legacy schema.
- **Health data privacy:** keep data on the LAN, avoid payload logging, and request only the three HealthKit read permissions required by the MVP.

## Completion Rule

No excluded feature is added until all automated tests pass and every M3 manual acceptance scenario has been demonstrated. The MVP is considered shipped when the documented iPhone-to-Raspberry-Pi flow works twice for the same date without creating a duplicate row.
