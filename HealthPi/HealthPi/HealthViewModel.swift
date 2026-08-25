import Foundation

struct HealthSummary: Equatable {
    let date: Date
    let weightKilograms: Double?
    let steps: Int?
    let sleepHours: Double?

    var hasData: Bool {
        weightKilograms != nil || steps != nil || sleepHours != nil
    }
}

@MainActor
protocol HealthDataProviding {
    func requestAuthorization() async throws
    func loadTodaySummary() async throws -> HealthSummary
}

@MainActor
protocol DailyHealthPosting {
    func post(_ summary: HealthSummary) async throws
}

enum HealthSyncState: Equatable {
    case idle
    case authorizing
    case loading
    case syncing
    case success
    case failure(String)

    var isBusy: Bool {
        self == .authorizing || self == .loading || self == .syncing
    }
}

enum HealthSyncError: LocalizedError {
    case noHealthData
    case invalidServerResponse
    case serverRejected(Int)

    var errorDescription: String? {
        switch self {
        case .noHealthData:
            return "No Health data was available for this day."
        case .invalidServerResponse:
            return "The Raspberry Pi returned an invalid response."
        case .serverRejected(let statusCode):
            return "The Raspberry Pi rejected the sync (HTTP \(statusCode))."
        }
    }
}

@MainActor
final class HealthAPIClient: DailyHealthPosting {
    private struct Payload: Encodable {
        let date: String
        let weightKg: Double?
        let steps: Int?
        let sleepHours: Double?

        enum CodingKeys: String, CodingKey {
            case date
            case weightKg = "weight_kg"
            case steps
            case sleepHours = "sleep_hours"
        }
    }

    private let baseURL: URL
    private let session: URLSession

    init(baseURL: URL, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.session = session
    }

    func post(_ summary: HealthSummary) async throws {
        var request = URLRequest(url: baseURL.appendingPathComponent("daily-health"))
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try Self.payloadData(for: summary)

        let (_, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw HealthSyncError.invalidServerResponse
        }
        guard (200...299).contains(httpResponse.statusCode) else {
            throw HealthSyncError.serverRejected(httpResponse.statusCode)
        }
    }

    static func payloadData(for summary: HealthSummary) throws -> Data {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Pacific/Auckland")!

        let components = calendar.dateComponents([.year, .month, .day], from: summary.date)
        let date = String(
            format: "%04d-%02d-%02d",
            components.year!,
            components.month!,
            components.day!
        )
        return try JSONEncoder().encode(
            Payload(
                date: date,
                weightKg: summary.weightKilograms,
                steps: summary.steps,
                sleepHours: summary.sleepHours
            )
        )
    }
}

@MainActor
final class HealthViewModel: ObservableObject {
    @Published private(set) var state: HealthSyncState = .idle
    @Published private(set) var summary: HealthSummary?

    private let healthProvider: HealthDataProviding
    private let apiClient: DailyHealthPosting

    init(healthProvider: HealthDataProviding, apiClient: DailyHealthPosting) {
        self.healthProvider = healthProvider
        self.apiClient = apiClient
    }

    convenience init(baseURL: URL) {
        self.init(
            healthProvider: HealthManager(),
            apiClient: HealthAPIClient(baseURL: baseURL)
        )
    }

    func syncToday() async {
        guard !state.isBusy else { return }

        do {
            state = .authorizing
            try await healthProvider.requestAuthorization()

            state = .loading
            let loadedSummary = try await healthProvider.loadTodaySummary()
            guard loadedSummary.hasData else { throw HealthSyncError.noHealthData }
            summary = loadedSummary

            state = .syncing
            try await apiClient.post(loadedSummary)
            state = .success
        } catch {
            state = .failure(error.localizedDescription)
        }
    }
}
