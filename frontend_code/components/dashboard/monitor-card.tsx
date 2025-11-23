"use client"

import { useState, useEffect } from "react"
import { BellOff, Waves, CheckCircle2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

export function MonitorCard() {
  // Mock state to toggle between 'monitoring' and 'ready'
  // In a real app, this would be driven by websocket or polling data
  const [status, setStatus] = useState<"monitoring" | "ready">("monitoring")
  const [duration, setDuration] = useState(0)

  // Circular progress calculation
  const radius = 100
  const circumference = 2 * Math.PI * radius
  // Simulate progress based on a 60 minute cycle for the visual
  const progress = Math.min((duration / 3600) * 100, 100)
  const strokeDashoffset = circumference - (progress / 100) * circumference

  // Simulate cycle timer
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (status === "monitoring") {
      interval = setInterval(() => {
        setDuration((prev) => prev + 1)
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [status])

  // Mock auto-switch for demo purposes after 10 seconds
  useEffect(() => {
    if (status === "monitoring") {
      const timeout = setTimeout(() => {
        setStatus("ready")
      }, 15000)
      return () => clearTimeout(timeout)
    }
  }, [status])

  const formatTime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`
    return `${mins}m ${secs}s`
  }

  return (
    <Card className="relative h-full overflow-hidden border-0 bg-white shadow-xl ring-1 ring-slate-900/5 dark:bg-card dark:ring-white/10 rounded-3xl">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-transparent to-transparent opacity-50" />

      <CardContent className="relative flex h-full flex-col items-center justify-center p-8 text-center">
        <div className="absolute top-8 left-8 flex items-center gap-2 rounded-full bg-slate-100 px-4 py-1.5 text-sm font-medium text-slate-600 shadow-sm">
          <Waves className="h-4 w-4" />
          Washing Machine
        </div>

        {status === "monitoring" ? (
          <div className="flex flex-col items-center gap-10 animate-in fade-in zoom-in duration-500">
            {/* Prominent Circular Ring Progress Bar */}
            <div className="relative flex h-72 w-72 items-center justify-center">
              {/* Outer Glow */}
              <div className="absolute inset-0 rounded-full bg-primary/5 blur-2xl transform scale-90" />

              <svg className="h-full w-full -rotate-90 transform">
                {/* Track */}
                <circle
                  cx="144"
                  cy="144"
                  r={radius}
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="12"
                  className="text-slate-100"
                />
                {/* Progress */}
                <circle
                  cx="144"
                  cy="144"
                  r={radius}
                  fill="transparent"
                  stroke="currentColor"
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={circumference}
                  strokeDashoffset={strokeDashoffset}
                  className="text-primary transition-all duration-1000 ease-in-out"
                />
              </svg>

              {/* Inner Content */}
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                <div className="flex flex-col items-center">
                  <span className="text-5xl font-bold tracking-tighter text-slate-700 tabular-nums">
                    {formatTime(duration)}
                  </span>
                  <span className="text-sm font-semibold text-slate-400 uppercase tracking-widest mt-1">Elapsed</span>
                </div>
                {/* Pulse Indicator */}
                <div className="absolute bottom-16 flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-600">
                  <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                  Listening
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <h2 className="text-3xl font-bold text-slate-700 tracking-tight">Cycle In Progress</h2>
              <p className="text-slate-500 text-lg">Analyzing sound patterns...</p>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => setStatus("ready")}
              className="mt-4 rounded-full px-6 text-xs text-slate-400 hover:text-slate-600 hover:bg-slate-50"
            >
              (Click to simulate cycle end)
            </Button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-8 animate-in fade-in zoom-in duration-500 w-full max-w-md">
            {/* Success State with Glow */}
            <div className="relative">
              <div className="absolute inset-0 animate-ping rounded-full bg-success/20 opacity-75 duration-[2000ms]" />
              <div className="relative flex h-48 w-48 items-center justify-center rounded-full bg-success/10 text-success ring-8 ring-success/10 shadow-[0_0_40px_-10px_var(--color-success)]">
                <CheckCircle2 className="h-24 w-24" />
              </div>
            </div>

            <div className="space-y-4">
              <h2 className="text-5xl font-bold tracking-tight text-success md:text-6xl drop-shadow-sm">
                LAUNDRY IS READY!
              </h2>
              <p className="text-xl text-slate-500 font-medium">Cycle finished just now</p>
            </div>

            <div className="grid w-full grid-cols-2 gap-4 pt-4">
              <Button
                size="lg"
                className="h-14 rounded-full bg-success text-white hover:bg-success/90 shadow-lg shadow-success/25 text-lg font-semibold transition-transform active:scale-95"
                onClick={() => {
                  setStatus("monitoring")
                  setDuration(0)
                }}
              >
                Dismiss
              </Button>
              <Button
                size="lg"
                variant="outline"
                className="h-14 rounded-full border-2 border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300 text-lg font-semibold bg-transparent transition-colors"
              >
                <BellOff className="mr-2 h-5 w-5" />
                Snooze
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
