# HealthPi Minimum MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Build one manual, reliable iPhone-to-Raspberry-Pi flow that reads weight, today's steps, and last night's sleep from HealthKit and idempotently stores the daily snapshot in SQLite.

**Architecture:** A small FastAPI service owns validation and an atomic SQLite upsert. The iOS app separates HealthKit reads, HTTP synchronization, and view state behind narrow protocols so orchestration can be unit tested. One user action loads a HealthSummary and sends one DailyHealthRequest.

**Tech Stack:** Swift 5, SwiftUI, HealthKit, URLSession, XCTest, Python 3, FastAPI, Pydantic 2, SQLite, pytest.

**Spec:** HealthPi/docs/superpowers/specs/2026-08-24-healthpi-minimum-mvp-design.md

## Global Constraints

- Support iOS 17.2 and later.
- Use Gregorian calendar dates fixed to Pacific/Auckland.
- Store only date, weight_kg, steps, sleep_hours, created_at, and updated_at.
- Preserve a stored non-null metric when a later same-date request supplies null.
- Use port 8999 consistently.
- Treat HTTP without authentication as trusted-private-LAN-only.
- Do not add AI, dashboard, voice, background sync, offline retry, accounts, trends, SwiftData, or clinical Health Records.
- Never log health payload values.

---

### Task 1: Isolate the MVP and establish a clean baseline

**Files:**
- Modify: .gitignore
- Carry forward: HealthPi/docs/superpowers/specs/2026-08-24-healthpi-minimum-mvp-design.md
- Carry forward: HealthPi/docs/superpowers/plans/2026-08-24-healthpi-minimum-mvp.md

**Interfaces:**
- Consumes: current origin/main, design commit d670710, and the dirty checkout as read-only reference.
- Produces: isolated branch codex/healthpi-minimum-mvp based on current origin/main.

- [ ] **Step 1: Preserve the current checkout**

Record git status --short --branch and leave every uncommitted Swift, Python, README, and Xcode-user-state change untouched.

- [ ] **Step 2: Create the isolated worktree**

Run:

    git fetch origin
    git worktree add /tmp/healthpi-minimum-mvp -b codex/healthpi-minimum-mvp origin/main

Expected: /tmp/healthpi-minimum-mvp is clean and points at current origin/main.

- [ ] **Step 3: Bring in the approved documents only**

Run:

    git cherry-pick d670710

Copy the amended spec and this plan from the original checkout because their working-tree versions are newer than the cherry-picked design.

- [ ] **Step 4: Remove repository noise**

Add these exact rules to .gitignore if absent:

    xcuserdata/
    *.xcuserstate
    .DS_Store

- [ ] **Step 5: Verify the baseline**

Run:

    python3 -m py_compile api/health_api.py
    bash -n start.sh
    xcodebuild -project HealthPi/HealthPi.xcodeproj -scheme HealthPi -sdk iphoneos -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build

Record baseline failures. Separate Xcode environment failures from Swift compiler failures.

- [ ] **Step 6: Commit repository hygiene**

    git add .gitignore HealthPi/docs/superpowers/specs/2026-08-24-healthpi-minimum-mvp-design.md HealthPi/docs/superpowers/plans/2026-08-24-healthpi-minimum-mvp.md
    git commit -m "chore: isolate HealthPi minimum MVP"

---

### Task 2: Implement the tested daily-health API

**Files:**
- Replace: api/health_api.py
- Create: tests/test_daily_health_api.py
- Create: requirements.txt
- Modify: start.sh

**Interfaces:**
- Consumes: JSON with ISO date plus optional weight_kg, steps, and sleep_hours.
- Produces: create_app(db_path: str) -> FastAPI, POST /daily-health, GET /daily-health/{date}, GET /health.

- [ ] **Step 1: Add minimal dependencies**

Create requirements.txt:

    fastapi
    httpx
    pydantic>=2
    pytest
    uvicorn

Create .venv and install the file.

- [ ] **Step 2: Write the failing create/read test**

Create tests/test_daily_health_api.py:

    from fastapi.testclient import TestClient
    from api.health_api import create_app

    def test_create_and_read_daily_health(tmp_path):
        client = TestClient(create_app(str(tmp_path / "health.db")))
        payload = {
            "date": "2026-08-24",
            "weight_kg": 78.2,
            "steps": 8560,
            "sleep_hours": 7.5,
        }
        response = client.post("/daily-health", json=payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "date": "2026-08-24"}
        stored = client.get("/daily-health/2026-08-24")
        assert stored.status_code == 200
        assert stored.json()["weight_kg"] == 78.2
        assert stored.json()["steps"] == 8560
        assert stored.json()["sleep_hours"] == 7.5

- [ ] **Step 3: Verify RED**

Run:

    .venv/bin/pytest tests/test_daily_health_api.py::test_create_and_read_daily_health -v

Expected: FAIL because create_app or /daily-health does not exist.

- [ ] **Step 4: Write minimal production code**

Replace legacy backend with:
- DailyHealthRequest using Pydantic date and Field constraints.
- A model validator rejecting requests where all three metrics are null.
- create_app(db_path) that creates daily_health.
- POST using one INSERT ... ON CONFLICT(date) DO UPDATE statement.
- COALESCE for each nullable metric.
- GET returning a named JSON object or 404.
- GET /health returning {"status": "ok"}.
- Module app using HEALTH_DB_PATH or health.db.

- [ ] **Step 5: Verify GREEN**

Run the first test. Expected: PASS.

- [ ] **Step 6: Add one failing test per remaining behavior**

Add separate tests for:
- same-date update keeps one row;
- null preserves an existing metric;
- a partial snapshot is accepted;
- all-null metrics return 422;
- invalid date, negative steps, non-positive weight, and sleep over 24 return 422;
- unknown date returns 404;
- /health returns ok.

Directly query SELECT COUNT(*) for the idempotency assertion.

- [ ] **Step 7: Verify RED then GREEN**

Run each new test before its implementation and observe the expected failure. Then implement only enough to pass. Finally run:

    .venv/bin/pytest -v
    python3 -m py_compile api/health_api.py

- [ ] **Step 8: Simplify start.sh**

Use only:

    #!/usr/bin/env bash
    set -euo pipefail
    exec .venv/bin/python -m uvicorn api.health_api:app --host 0.0.0.0 --port 8999

Run bash -n start.sh.

- [ ] **Step 9: Commit**

    git add api/health_api.py tests/test_daily_health_api.py requirements.txt start.sh
    git commit -m "feat: add idempotent daily health API"

---

### Task 3: Implement the testable iOS coordinator and API client

**Files:**
- Create: HealthPi/HealthPi/HealthSummary.swift
- Create: HealthPi/HealthPi/HealthAPIClient.swift
- Replace: HealthPi/HealthPi/HealthViewModel.swift
- Modify: HealthPi/HealthPiTests/HealthPiTests.swift
- Modify: HealthPi/HealthPi.xcodeproj/project.pbxproj

**Interfaces:**
- HealthDataProviding.loadSummary() async throws -> HealthSummary
- DailyHealthSyncing.sync(_ summary: HealthSummary) async throws
- HealthViewModel.readAndSync() async

- [ ] **Step 1: Write failing ViewModel tests**

Use fakes and assert:
- success publishes the summary, calls the syncer once, and enters success;
- provider failure never calls the syncer;
- sync failure enters failure;
- a call while loading is ignored.

The first test shape is:

    @MainActor
    func testReadAndSyncPublishesSummaryAndCallsAPIOnce() async {
        let summary = HealthSummary(
            date: Date(timeIntervalSince1970: 1_724_434_400),
            weightKilograms: 78.2,
            steps: 8560,
            sleepHours: 7.5
        )
        let provider = FakeHealthProvider(result: .success(summary))
        let syncer = FakeDailyHealthSyncer()
        let viewModel = HealthViewModel(healthProvider: provider, syncer: syncer)
        await viewModel.readAndSync()
        XCTAssertEqual(viewModel.summary, summary)
        XCTAssertEqual(syncer.received, [summary])
        XCTAssertEqual(viewModel.state, .success)
    }

- [ ] **Step 2: Verify RED**

Run the HealthPi test target. Expected: compile failure because the types do not exist.

- [ ] **Step 3: Add the minimal model and protocols**

Create:

    struct HealthSummary: Equatable, Sendable {
        let date: Date
        let weightKilograms: Double?
        let steps: Int?
        let sleepHours: Double?
    }

    protocol HealthDataProviding {
        func requestAuthorization() async throws
        func loadSummary() async throws -> HealthSummary
    }

    protocol DailyHealthSyncing {
        func sync(_ summary: HealthSummary) async throws
    }

- [ ] **Step 4: Implement the minimal ViewModel**

Use one readAndSync method, guard against active work, publish one summary, and map errors to failure. Keep requestAuthorization separate because it presents the system sheet.

- [ ] **Step 5: Verify GREEN**

Run all ViewModel tests.

- [ ] **Step 6: Write the failing API-client test**

Use URLProtocol to capture exactly one request. Assert POST, /daily-health, and JSON keys date, weight_kg, steps, sleep_hours. Assert Auckland date formatting at a UTC boundary.

- [ ] **Step 7: Implement HealthAPIClient**

Use URLSession.data(for:), inject base URL/session/time zone, require HTTPURLResponse, and accept only 200 through 299. Do not add retry or caching.

- [ ] **Step 8: Verify and commit**

Run tests and unsigned iOS build, then commit the model, client, ViewModel, tests, and project changes.

---

### Task 4: Connect HealthKit and reduce the UI to the MVP

**Files:**
- Replace: HealthPi/HealthPi/HealthManager.swift
- Replace: HealthPi/HealthPi/ContentView.swift
- Simplify: HealthPi/HealthPi/HealthPiApp.swift
- Delete: HealthPi/HealthPi/Item.swift
- Modify: HealthPi/HealthPi/HealthPi.entitlements
- Modify: HealthPi/HealthPi/Info.plist
- Modify: HealthPi/HealthPi.xcodeproj/project.pbxproj
- Modify: HealthPi/HealthPiTests/HealthPiTests.swift

**Interfaces:**
- Consumes HealthDataProviding, HealthSummary, HealthAPIClient, HealthViewModel.
- Produces the real HealthKit provider and one manual authorization/read/sync UI.

- [ ] **Step 1: Write failing sleep-interval tests**

Test a pure mergedDuration function for adjacent, overlapping, and nested intervals.

- [ ] **Step 2: Verify RED**

Run the sleep tests and observe the missing function failure.

- [ ] **Step 3: Implement interval merging**

Sort by start, merge overlapping or adjacent intervals, then total the merged durations. Filter HealthKit samples with allAsleepValues.

- [ ] **Step 4: Convert HealthManager to async**

Use HealthKit's async authorization API. Query weight, steps, and sleep so query errors throw and legitimate no-sample results return nil. Load the three values concurrently and return HealthSummary for the Auckland day.

- [ ] **Step 5: Reduce permissions and configuration**

Keep only base HealthKit entitlement. Remove clinical records and background delivery. Add purpose strings for reading weight, steps, sleep, NSLocalNetworkUsageDescription, and the minimal iOS 17.2 local-network ATS exception.

- [ ] **Step 6: Simplify the app**

Remove SwiftData and Item. Use plain WindowGroup. Inject real dependencies. Render metrics, conditional authorization, one Read and Sync action, and one status message. Disable actions while busy.

- [ ] **Step 7: Verify**

Run iOS tests and unsigned generic-device build. Expected: no deprecated asleep warning.

- [ ] **Step 8: Commit**

Commit only intentional iOS sources, tests, plist, entitlements, and project changes.

---

### Task 5: Document and verify the MVP

**Files:**
- Replace: README.md
- Modify: HealthPi/docs/superpowers/specs/2026-08-24-healthpi-minimum-mvp-design.md

**Interfaces:**
- Consumes the working API, iOS app, automated tests, and trusted-LAN constraint.
- Produces a reproducible runbook and evidence-backed handoff.

- [ ] **Step 1: Replace speculative documentation**

Document prerequisites, virtualenv setup, HEALTH_DB_PATH, port 8999, Pi URL configuration, permissions, curl examples, tests, trusted-LAN warning, and known limitations. Remove AI, dashboard, fine-tuning, and speculative ERD content.

- [ ] **Step 2: Run automated verification**

    .venv/bin/pytest -v
    python3 -m py_compile api/health_api.py
    bash -n start.sh
    xcodebuild -project HealthPi/HealthPi.xcodeproj -scheme HealthPi -sdk iphoneos -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO build
    git diff --check

Expected: all commands exit zero.

- [ ] **Step 3: Run API smoke test**

POST the same date twice with different partial metrics, GET the row, and query SQLite. Expected: one row containing merged metrics.

- [ ] **Step 4: Run physical-device acceptance**

On iPhone and Raspberry Pi: grant access, sync, verify GET, sync again, stop/restart API, verify error and recovery. Record a device-only blocker instead of claiming completion.

- [ ] **Step 5: Final commit**

Confirm git status contains only intentional files and commit the README/spec changes.
