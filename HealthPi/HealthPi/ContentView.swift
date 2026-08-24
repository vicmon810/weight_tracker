import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel: HealthViewModel

    init(viewModel: HealthViewModel) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                VStack(spacing: 8) {
                    Image(systemName: "heart.text.square.fill")
                        .font(.system(size: 52))
                        .foregroundStyle(.red)
                    Text("HealthPi")
                        .font(.largeTitle.bold())
                    Text("Apple Health → Raspberry Pi")
                        .foregroundStyle(.secondary)
                }

                if let summary = viewModel.summary {
                    HStack(spacing: 12) {
                        MetricCard(title: "Weight", value: formattedWeight(summary.weightKilograms), icon: "scalemass")
                        MetricCard(title: "Steps", value: formattedSteps(summary.steps), icon: "figure.walk")
                        MetricCard(title: "Sleep", value: formattedSleep(summary.sleepHours), icon: "bed.double")
                    }
                }

                statusView

                Button {
                    Task { await viewModel.syncToday() }
                } label: {
                    Label(buttonTitle, systemImage: "arrow.triangle.2.circlepath")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.borderedProminent)
                .disabled(viewModel.state.isBusy)
            }
            .padding()
            .navigationTitle("Daily Sync")
        }
    }

    @ViewBuilder
    private var statusView: some View {
        switch viewModel.state {
        case .idle:
            Text("Tap Sync Today to read HealthKit and save one daily record.")
                .foregroundStyle(.secondary)
        case .authorizing:
            ProgressView("Requesting Health access…")
        case .loading:
            ProgressView("Reading today’s health data…")
        case .syncing:
            ProgressView("Sending to Raspberry Pi…")
        case .success:
            Label("Synced successfully", systemImage: "checkmark.circle.fill")
                .foregroundStyle(.green)
        case .failure(let message):
            Label(message, systemImage: "exclamationmark.triangle.fill")
                .foregroundStyle(.red)
        }
    }

    private var buttonTitle: String {
        switch viewModel.state {
        case .success, .failure:
            return "Sync Again"
        default:
            return "Sync Today"
        }
    }

    private func formattedWeight(_ value: Double?) -> String {
        value.map { String(format: "%.1f kg", $0) } ?? "—"
    }

    private func formattedSteps(_ value: Int?) -> String {
        value.map(String.init) ?? "—"
    }

    private func formattedSleep(_ value: Double?) -> String {
        value.map { String(format: "%.1f h", $0) } ?? "—"
    }
}

private struct MetricCard: View {
    let title: String
    let value: String
    let icon: String

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.title2)
            Text(value)
                .font(.headline)
                .minimumScaleFactor(0.7)
                .lineLimit(1)
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }
}

#Preview {
    ContentView(
        viewModel: HealthViewModel(
            healthProvider: HealthManager(),
            apiClient: HealthAPIClient(baseURL: URL(string: "http://127.0.0.1:8999")!)
        )
    )
}
