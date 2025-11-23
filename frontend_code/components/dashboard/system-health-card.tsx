"use client"
import { Mic, Wifi, Activity } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function SystemHealthCard() {
  return (
    <Card className="h-full border-0 shadow-lg ring-1 ring-slate-900/5 dark:bg-card dark:ring-white/10 rounded-3xl overflow-hidden">
      <CardHeader className="border-b border-slate-50 bg-slate-50/50 pb-4">
        <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-700">
          <Activity className="h-4 w-4 text-primary" />
          System Health
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 pt-6">
        {/* Connection Status */}
        <div className="flex items-center justify-between rounded-2xl bg-white p-1">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-50 text-slate-500 shadow-sm border border-slate-100">
              <Wifi className="h-5 w-5" />
            </div>
            <div className="space-y-0.5">
              <p className="text-sm font-semibold text-slate-700">ESP32-Monitor</p>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-600">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Online
              </span>
            </div>
          </div>
        </div>

        {/* Mic Input Level */}
        <div className="space-y-3 rounded-2xl bg-slate-50/50 p-4 border border-slate-100">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-slate-500 font-medium">
              <Mic className="h-4 w-4" />
              <span>Microphone Input</span>
            </div>
            <span className="text-xs font-bold bg-white px-2 py-0.5 rounded-full shadow-sm border border-slate-100 text-slate-600">
              -42 dB
            </span>
          </div>

          <WigglyWaveform />

          <p className="text-[11px] text-center text-slate-400 font-medium">Detecting motor frequencies...</p>
        </div>
      </CardContent>
    </Card>
  )
}

function WigglyWaveform() {
  // A CSS-only animated waveform simulation using multiple bars
  return (
    <div className="flex h-16 items-center justify-center gap-[3px] overflow-hidden rounded-xl bg-white shadow-inner px-4 py-2 border border-slate-100">
      {/* Generate multiple bars with different animation delays for the "wiggly" effect */}
      {[...Array(12)].map((_, i) => (
        <div
          key={i}
          className="w-1.5 rounded-full bg-primary/80"
          style={{
            height: "40%",
            animation: `waveform 1s ease-in-out infinite`,
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
      <style jsx>{`
         @keyframes waveform {
           0%, 100% { height: 30%; opacity: 0.5; }
           50% { height: 80%; opacity: 1; }
         }
       `}</style>
    </div>
  )
}
