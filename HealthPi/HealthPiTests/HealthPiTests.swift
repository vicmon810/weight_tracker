import XCTest
@testable import HealthPi

@MainActor
final class HealthPiTests: XCTestCase {
    func testSyncLoadsHealthBeforePostingSummary() async {
        let summary = HealthSummary(
            date: Date(timeIntervalSince1970: 1_786_982_400),
            weightKilograms: 72.4,
            steps: 8_321,
            sleepHours: 7.5
        )
        let health = HealthProviderStub(summary: summary)
        let api = HealthAPIStub()
        let viewModel = HealthViewModel(healthProvider: health, apiClient: api)

        await viewModel.syncToday()

        XCTAssertEqual(health.authorizationRequests, 1)
        XCTAssertEqual(health.summaryRequests, 1)
        XCTAssertEqual(api.receivedSummaries, [summary])
        XCTAssertEqual(viewModel.state, .success)
        XCTAssertEqual(viewModel.summary, summary)
    }

    func testSyncFailureIsVisibleAndCanBeRetried() async {
        let health = HealthProviderStub(error: TestError.expected)
        let api = HealthAPIStub()
        let viewModel = HealthViewModel(healthProvider: health, apiClient: api)

        await viewModel.syncToday()
        guard case .failure = viewModel.state else {
            return XCTFail("Expected a visible failure state")
        }

        health.error = nil
        health.summary = HealthSummary(
            date: Date(timeIntervalSince1970: 1_786_982_400),
            weightKilograms: nil,
            steps: 100,
            sleepHours: nil
        )
        await viewModel.syncToday()

        XCTAssertEqual(viewModel.state, .success)
        XCTAssertEqual(api.receivedSummaries.count, 1)
    }

    func testPayloadUsesAucklandCalendarDateAndSnakeCaseKeys() throws {
        let date = try XCTUnwrap(ISO8601DateFormatter().date(from: "2026-08-24T12:30:00Z"))
        let summary = HealthSummary(
            date: date,
            weightKilograms: 71.2,
            steps: 9_876,
            sleepHours: 6.75
        )

        let data = try HealthAPIClient.payloadData(for: summary)
        let json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])

        XCTAssertEqual(json["date"] as? String, "2026-08-25")
        XCTAssertEqual(json["weight_kg"] as? Double, 71.2)
        XCTAssertEqual(json["steps"] as? Int, 9_876)
        XCTAssertEqual(json["sleep_hours"] as? Double, 6.75)
    }

    func testMergedSleepHoursDoesNotDoubleCountOverlaps() {
        let origin = Date(timeIntervalSince1970: 0)
        let intervals = [
            DateInterval(start: origin, duration: 4 * 3_600),
            DateInterval(start: origin.addingTimeInterval(3 * 3_600), duration: 3 * 3_600),
            DateInterval(start: origin.addingTimeInterval(7 * 3_600), duration: 3_600),
        ]

        XCTAssertEqual(HealthManager.mergedHours(in: intervals), 7, accuracy: 0.001)
    }
}

private enum TestError: Error {
    case expected
}

@MainActor
private final class HealthProviderStub: HealthDataProviding {
    var summary: HealthSummary?
    var error: Error?
    var authorizationRequests = 0
    var summaryRequests = 0

    init(summary: HealthSummary? = nil, error: Error? = nil) {
        self.summary = summary
        self.error = error
    }

    func requestAuthorization() async throws {
        authorizationRequests += 1
    }

    func loadTodaySummary() async throws -> HealthSummary {
        summaryRequests += 1
        if let error { throw error }
        return try XCTUnwrap(summary)
    }
}

@MainActor
private final class HealthAPIStub: DailyHealthPosting {
    var receivedSummaries: [HealthSummary] = []

    func post(_ summary: HealthSummary) async throws {
        receivedSummaries.append(summary)
    }
}
