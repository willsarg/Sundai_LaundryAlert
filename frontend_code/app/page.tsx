import {MonitorCard} from "@/components/dashboard/monitor-card";
import {SystemHealthCard} from "@/components/dashboard/system-health-card";
import {RecentActivityCard} from "@/components/dashboard/recent-activity-card";
import {LaundryEventsCard} from "@/components/dashboard/laundry-events-card";
import {Settings} from "lucide-react";
import {Button} from "@/components/ui/button";

export default function DashboardPage() {
	return (
		<div className="min-h-screen bg-background p-6 md:p-10 transition-colors">
			<div className="mx-auto max-w-[1600px] space-y-8">
				<header className="flex items-center justify-between">
					<div className="space-y-1">
						<h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
							Laundry Monitor
						</h1>
						<p className="text-muted-foreground">
							Real-time audio monitoring for your home appliances.
						</p>
					</div>
					<div className="flex items-center gap-2">
						<div className="hidden items-center gap-2 text-sm font-medium text-muted-foreground md:flex">
							<span className="h-2.5 w-2.5 rounded-full bg-success shadow-[0_0_8px_2px_var(--color-success)] animate-pulse" />
							System Online
						</div>
					</div>
				</header>

				{/* Laundry Events Front and Center */}
				<main className="space-y-6">
					{/* Featured: Recent Events - Full width, prominent */}
					<div className="w-full">
						<LaundryEventsCard />
					</div>

					{/* Secondary cards in grid below */}
					<div className="grid gap-6 md:grid-cols-3">
						<div className="md:col-span-2">
							<MonitorCard />
						</div>
						<div className="space-y-6">
							<SystemHealthCard />
							<RecentActivityCard />
						</div>
					</div>
				</main>

				<footer className="flex justify-center py-6 md:justify-end">
					<Button
						variant="outline"
						className="group gap-2 rounded-full px-6 shadow-sm text-muted-foreground hover:text-foreground hover:bg-white hover:shadow-md transition-all bg-transparent">
						<Settings className="h-4 w-4 transition-transform group-hover:rotate-90" />
						Manage Devices & Zones
					</Button>
				</footer>
			</div>
		</div>
	);
}
