import SwiftUI

@main
struct HealthPiApp: App {
    private let apiBaseURL: URL = {
        guard
            let value = Bundle.main.object(forInfoDictionaryKey: "HealthAPIBaseURL") as? String,
            let url = URL(string: value)
        else {
            preconditionFailure("HealthAPIBaseURL is missing or invalid")
        }
        return url
    }()

    var body: some Scene {
        WindowGroup {
            ContentView(viewModel: HealthViewModel(baseURL: apiBaseURL))
        }
    }
}
