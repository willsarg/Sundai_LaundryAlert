import { Clock, CalendarDays } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function RecentActivityCard() {
  const activities = [
    {
      id: 1,
      type: "Cycle Completed",
      duration: "45m 12s",
      time: "Today, 2:30 PM",
      status: "success",
    },
    {
      id: 2,
      type: "Cycle Completed",
      duration: "1h 12m",
      time: "Yesterday, 8:15 PM",
      status: "success",
    },
    {
      id: 3,
      type: "Interrupted",
      duration: "15m 00s",
      time: "Yesterday, 6:00 PM",
      status: "warning",
    },
    {
      id: 4,
      type: "Cycle Completed",
      duration: "52m 30s",
      time: "Oct 24, 10:00 AM",
      status: "success",
    },
  ]

  return (
    <Card className="h-full border-0 shadow-lg ring-1 ring-slate-900/5 dark:bg-card dark:ring-white/10 rounded-3xl overflow-hidden flex flex-col">
      <CardHeader className="border-b border-slate-50 bg-slate-50/50 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base font-semibold text-slate-700">
            <Clock className="h-4 w-4 text-primary" />
            Recent Activity
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 rounded-full px-3 text-xs font-medium text-primary hover:text-primary hover:bg-primary/10"
          >
            View All
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-4 overflow-auto flex-1">
        <div className="space-y-3">
          {activities.map((activity, i) => (
            <div
              key={activity.id}
              className="group flex items-center justify-between rounded-2xl border border-slate-100 bg-white p-3 shadow-sm transition-all hover:border-primary/20 hover:shadow-md"
            >
              <div className="flex items-center gap-3">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full shadow-inner ${
                    activity.status === "success" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                  }`}
                >
                  <CalendarDays className="h-5 w-5" />
                </div>
                <div className="space-y-0.5">
                  <p className="text-sm font-bold text-slate-700">{activity.type}</p>
                  <p className="text-xs font-medium text-slate-400">{activity.time}</p>
                </div>
              </div>
              <div className="text-right">
                <div className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-bold tabular-nums text-slate-600">
                  {activity.duration}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
