import Foundation
import HealthKit

enum HealthManagerError: LocalizedError {
    case healthDataUnavailable
    case missingHealthType

    var errorDescription: String? {
        switch self {
        case .healthDataUnavailable:
            return "Health data is unavailable on this device."
        case .missingHealthType:
            return "A required HealthKit data type is unavailable."
        }
    }
}

@MainActor
final class HealthManager: HealthDataProviding {
    private let store: HKHealthStore
    private var calendar: Calendar

    init(store: HKHealthStore = HKHealthStore()) {
        self.store = store
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(identifier: "Pacific/Auckland")!
        self.calendar = calendar
    }

    func requestAuthorization() async throws {
        guard HKHealthStore.isHealthDataAvailable() else {
            throw HealthManagerError.healthDataUnavailable
        }
        guard
            let bodyMass = HKObjectType.quantityType(forIdentifier: .bodyMass),
            let steps = HKObjectType.quantityType(forIdentifier: .stepCount),
            let sleep = HKObjectType.categoryType(forIdentifier: .sleepAnalysis)
        else {
            throw HealthManagerError.missingHealthType
        }

        try await store.requestAuthorization(toShare: [], read: [bodyMass, steps, sleep])
    }

    func loadTodaySummary() async throws -> HealthSummary {
        let now = Date()
        async let weight = loadLatestWeight(before: now)
        async let steps = loadSteps(on: now)
        async let sleep = loadLastNightSleep(for: now)

        return try await HealthSummary(
            date: now,
            weightKilograms: weight,
            steps: steps,
            sleepHours: sleep
        )
    }

    private func loadLatestWeight(before end: Date) async throws -> Double? {
        guard let type = HKQuantityType.quantityType(forIdentifier: .bodyMass) else {
            throw HealthManagerError.missingHealthType
        }
        let descriptor = NSSortDescriptor(key: HKSampleSortIdentifierEndDate, ascending: false)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: type,
                predicate: HKQuery.predicateForSamples(withStart: nil, end: end),
                limit: 1,
                sortDescriptors: [descriptor]
            ) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let sample = samples?.first as? HKQuantitySample
                continuation.resume(returning: sample?.quantity.doubleValue(for: .gramUnit(with: .kilo)))
            }
            store.execute(query)
        }
    }

    private func loadSteps(on date: Date) async throws -> Int? {
        guard let type = HKQuantityType.quantityType(forIdentifier: .stepCount) else {
            throw HealthManagerError.missingHealthType
        }
        let start = calendar.startOfDay(for: date)
        let end = calendar.date(byAdding: .day, value: 1, to: start)!
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKStatisticsQuery(
                quantityType: type,
                quantitySamplePredicate: predicate,
                options: .cumulativeSum
            ) { _, statistics, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let value = statistics?.sumQuantity()?.doubleValue(for: .count())
                continuation.resume(returning: value.map { Int($0.rounded()) })
            }
            store.execute(query)
        }
    }

    private func loadLastNightSleep(for date: Date) async throws -> Double? {
        guard let type = HKCategoryType.categoryType(forIdentifier: .sleepAnalysis) else {
            throw HealthManagerError.missingHealthType
        }
        let today = calendar.startOfDay(for: date)
        let start = calendar.date(byAdding: .hour, value: -6, to: today)!
        let end = calendar.date(byAdding: .hour, value: 12, to: today)!
        let predicate = HKQuery.predicateForSamples(withStart: start, end: end)

        return try await withCheckedThrowingContinuation { continuation in
            let query = HKSampleQuery(
                sampleType: type,
                predicate: predicate,
                limit: HKObjectQueryNoLimit,
                sortDescriptors: nil
            ) { _, samples, error in
                if let error {
                    continuation.resume(throwing: error)
                    return
                }
                let asleepValues: Set<Int> = [
                    HKCategoryValueSleepAnalysis.asleepUnspecified.rawValue,
                    HKCategoryValueSleepAnalysis.asleepCore.rawValue,
                    HKCategoryValueSleepAnalysis.asleepDeep.rawValue,
                    HKCategoryValueSleepAnalysis.asleepREM.rawValue,
                ]
                let intervals = (samples as? [HKCategorySample] ?? [])
                    .filter { asleepValues.contains($0.value) }
                    .map { DateInterval(start: max($0.startDate, start), end: min($0.endDate, end)) }
                continuation.resume(returning: intervals.isEmpty ? nil : Self.mergedHours(in: intervals))
            }
            store.execute(query)
        }
    }

    static func mergedHours(in intervals: [DateInterval]) -> Double {
        let sorted = intervals
            .filter { $0.duration > 0 }
            .sorted { $0.start < $1.start }
        guard var current = sorted.first else { return 0 }

        var duration = 0.0
        for interval in sorted.dropFirst() {
            if interval.start <= current.end {
                current = DateInterval(start: current.start, end: max(current.end, interval.end))
            } else {
                duration += current.duration
                current = interval
            }
        }
        duration += current.duration
        return duration / 3_600
    }
}
