"use client";

import {useEffect, useState} from "react";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
	CardDescription
} from "@/components/ui/card";
import {Activity, CheckCircle2, Volume2, AlertCircle} from "lucide-react";

interface LaundryEvent {
	filename: string;
	timestamp: string;
	has_sound: boolean;
	is_knocking: boolean;
	confidence: number;
	processed_at: string;
}

export function LaundryEventsCard() {
	const [events, setEvents] = useState<LaundryEvent[]>([]);
	const [isLoading, setIsLoading] = useState(true);

	useEffect(() => {
		const fetchEvents = async () => {
			try {
				const response = await fetch("/api/laundry-events");
				const data = await response.json();
				setEvents(data.events || []);
			} catch (error) {
				console.error("Failed to fetch events:", error);
			} finally {
				setIsLoading(false);
			}
		};

		// Fetch immediately
		fetchEvents();

		// Poll every 5 seconds for new events
		const interval = setInterval(fetchEvents, 5000);

		return () => clearInterval(interval);
	}, []);

	if (isLoading) {
		return (
			<Card>
				<CardHeader>
					<CardTitle>Recent Events</CardTitle>
				</CardHeader>
				<CardContent>
					<p className="text-muted-foreground">Loading...</p>
				</CardContent>
			</Card>
		);
	}

	return (
		<Card className="border-2 shadow-lg">
			<CardHeader className="pb-3">
				<div className="flex items-center justify-between">
					<div>
						<CardTitle className="text-2xl flex items-center gap-2">
							<Activity className="h-6 w-6 text-primary" />
							Washing Machine Status Monitor
						</CardTitle>
						<CardDescription className="mt-1.5">
							Smart audio detection alerts you when your laundry
							is done • {events.length} cycles monitored
						</CardDescription>
					</div>
					<div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-100 dark:bg-green-900/20">
						<span className="h-2 w-2 rounded-full bg-green-600 animate-pulse" />
						<span className="text-xs font-medium text-green-700 dark:text-green-400">
							Monitoring
						</span>
					</div>
				</div>
			</CardHeader>
			<CardContent>
				{events.length === 0 ? (
					<div className="flex flex-col items-center justify-center py-12 px-4 text-center">
						<div className="rounded-full bg-blue-100 dark:bg-blue-900/20 p-4 mb-4">
							<Volume2 className="h-8 w-8 text-blue-600" />
						</div>
						<h3 className="text-lg font-semibold mb-2">
							Listening for Your Laundry
						</h3>
						<p className="text-muted-foreground max-w-md mb-4">
							Our system listens for the distinctive "knocking"
							sound that washing machines make when they finish a
							cycle. Never forget your laundry again!
						</p>
						<div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-2xl text-sm">
							<div className="p-4 bg-muted/50 rounded-lg">
								<div className="font-semibold mb-1 flex items-center gap-2">
									<Volume2 className="h-4 w-4 text-green-600" />
									Detects Sound
								</div>
								<p className="text-xs text-muted-foreground">
									Monitors if washer is running
								</p>
							</div>
							<div className="p-4 bg-muted/50 rounded-lg">
								<div className="font-semibold mb-1 flex items-center gap-2">
									<AlertCircle className="h-4 w-4 text-orange-600" />
									Hears Knocking
								</div>
								<p className="text-xs text-muted-foreground">
									Identifies cycle complete signal
								</p>
							</div>
							<div className="p-4 bg-muted/50 rounded-lg">
								<div className="font-semibold mb-1 flex items-center gap-2">
									<CheckCircle2 className="h-4 w-4 text-blue-600" />
									Alerts You
								</div>
								<p className="text-xs text-muted-foreground">
									Get notified instantly
								</p>
							</div>
						</div>
						<p className="text-xs text-muted-foreground mt-6">
							🧺 Start a wash cycle and watch as we detect when
							it's ready to move to the dryer
						</p>
					</div>
				) : (
					<div className="space-y-3">
						{events
							.slice()
							.reverse()
							.map((event, index) => (
								<div
									key={`${event.filename}-${index}`}
									className={`group relative border-2 rounded-xl p-5 transition-all hover:shadow-md ${
										event.is_knocking
											? "border-orange-500/50 bg-orange-50 dark:bg-orange-900/10"
											: event.has_sound
											? "border-green-500/30 bg-green-50 dark:bg-green-900/10"
											: "border-gray-200 dark:border-gray-800 bg-card"
									}`}>
									<div className="flex items-start justify-between mb-3">
										<div className="flex items-center gap-3">
											<div
												className={`p-2 rounded-lg ${
													event.is_knocking
														? "bg-orange-500 animate-pulse"
														: event.has_sound
														? "bg-green-500"
														: "bg-gray-300"
												}`}>
												<Volume2 className="h-5 w-5 text-white" />
											</div>
											<div>
												<p
													className={`text-base font-semibold mb-1 ${
														event.is_knocking
															? "text-orange-700 dark:text-orange-400"
															: ""
													}`}>
													{event.is_knocking
														? "🧺 Laundry Cycle Complete!"
														: event.has_sound
														? "🔄 Washer Running"
														: "💤 Machine Idle"}
												</p>
												<p className="text-xs text-muted-foreground">
													{new Date(
														event.timestamp
													).toLocaleString("en-US", {
														month: "short",
														day: "numeric",
														hour: "2-digit",
														minute: "2-digit",
														second: "2-digit"
													})}
												</p>
											</div>
										</div>
										<div
											className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${
												event.confidence > 0.8
													? "bg-green-100 dark:bg-green-900/20"
													: "bg-yellow-100 dark:bg-yellow-900/20"
											}`}>
											<CheckCircle2
												className={`h-3.5 w-3.5 ${
													event.confidence > 0.8
														? "text-green-600"
														: "text-yellow-600"
												}`}
											/>
											<span
												className={`text-sm font-semibold ${
													event.confidence > 0.8
														? "text-green-700 dark:text-green-400"
														: "text-yellow-700 dark:text-yellow-400"
												}`}>
												{(
													event.confidence * 100
												).toFixed(0)}
												%
											</span>
										</div>
									</div>

									{event.is_knocking && (
										<div className="mb-3 p-3 bg-orange-100 dark:bg-orange-900/20 rounded-lg border border-orange-200 dark:border-orange-800">
											<p className="text-sm font-medium text-orange-900 dark:text-orange-200">
												⏰ Your laundry is ready! Move
												it to the dryer to prevent
												wrinkles.
											</p>
										</div>
									)}

									<div className="grid grid-cols-2 gap-3 text-sm">
										<div
											className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
												event.has_sound
													? "bg-green-100 dark:bg-green-900/20"
													: "bg-gray-100 dark:bg-gray-800"
											}`}>
											<div
												className={`h-2.5 w-2.5 rounded-full ${
													event.has_sound
														? "bg-green-600"
														: "bg-gray-400"
												}`}
											/>
											<span className="font-medium">
												{event.has_sound
													? "Active"
													: "Silent"}
											</span>
										</div>
										<div
											className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
												event.is_knocking
													? "bg-orange-100 dark:bg-orange-900/20"
													: "bg-gray-100 dark:bg-gray-800"
											}`}>
											<div
												className={`h-2.5 w-2.5 rounded-full ${
													event.is_knocking
														? "bg-orange-600"
														: "bg-gray-400"
												}`}
											/>
											<span className="font-medium">
												{event.is_knocking
													? "Cycle Done"
													: "In Progress"}
											</span>
										</div>
									</div>
									<p className="text-xs text-muted-foreground mt-2 font-mono">
										{event.filename}
									</p>
								</div>
							))}
					</div>
				)}
			</CardContent>
		</Card>
	);
}
