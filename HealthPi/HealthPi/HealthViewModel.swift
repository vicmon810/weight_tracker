//
//  HealthView.swift
//  HealthPi
//
//  Created by Kris Mao on 2/01/26.
//

import Foundation
import SwiftUI

@MainActor
final class HealthView: ObservableObject{
    private let healthManager = HealthManager()
    
    private let apiBaseURL = "http://192.168.88.6:8000"
    
    @Published var statusMessage: String = ""
    @Published var bodyMess : Double?
    @Published var stepCount: Double?
    @Published var sleepHours: Double?
    
    func requestPremission()  {
        statusMessage = "Requesting HealthKid authorization..."
        
        healthManager.requestAuthorization { [weak self] success
            in
            Task {
                self?.statusMessage = success ? "HealthKit Authorized" : "Authorization failed"
            }
        }
    }
    
    
    func loadTodaySummary(){
        statusMessage = "Loading data ...."
        
        Task {
            async let w = fetchWeight()
            async let s = fetchSteps()
            async let h = fetchSleep()
            
            let (weight, steps, sleep) = await (w,s,h)
            
            bodyMess = weight
            stepCount = steps
            sleepHours = sleep
            
            statusMessage = "Loaded from Health"
        }
    }
    
    private func fetchWeight() async -> Double? {
         await withCheckedContinuation { continuation in
             healthManager.fetchLatestBodyMass { value in
                 continuation.resume(returning: value)
             }
         }
     }
    
    private func fetchSteps() async -> Double?{
        await withCheckedContinuation{
            continuation in healthManager.fetchTodayStepCount
            {value in continuation.resume(returning: value)}
        }
    }
    
    private func fetchSleep() async -> Double?{
        await withCheckedContinuation{
            continuation in healthManager.fetchLastNightSleepHours{
                value in continuation.resume(returning: value)
            }
        }
    }
    
    func syncToPi(){
        guard
            let url = URL(string: apiBaseURL+"/checkin")
        else{
            statusMessage = "Invalid API URL"
            return
        }
        
        let exerciseMinutes: Int? = {
            if let steps = stepCount{
                return Int(steps/100.0)
            }
            return nil
        }()
        
        let payload = CheckPayLoad(
            mood:"Synced From Iphone",
            diet_note: "",
            execrise_minutes: exerciseMinutes,
            execrise_note: "Step from Apple health",
            sleep_hours: sleepHours,
            Weight: bodyMess
        )
        guard
            let body = try? JSONEncoder().encode(payload)
        else{
            statusMessage = "Failed to encode payload"
            return
        }
        
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = body
        
        statusMessage = "Syncing to Pi"
        
        
        let task = URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
                    Task { @MainActor in
                        if let error = error {
                            self?.statusMessage = "Sync failed: \(error.localizedDescription)"
                            return
                        }

                        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
                            self?.statusMessage = "Sync failed: HTTP \(http.statusCode)"
                            return
                        }

                        self?.statusMessage = "Synced successfully to Raspberry Pi."
                    }
                }

                task.resume()
        
        }
        
    }
    
    struct CheckPayLoad: Codable{
        let mood:String
        let diet_note:String
        let execrise_minutes:Int?
        let execrise_note: String?
        let sleep_hours: Double?
        let Weight: Double?
    }


