"use client";

import {useEffect, useState} from "react";
import {Card, CardContent, CardHeader, CardTitle} from "@/components/ui/card";

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
		<Card>
			<CardHeader>
				<CardTitle>Recent Events ({events.length})</CardTitle>
			</CardHeader>
			<CardContent>
				{events.length === 0 ? (
					<p className="text-muted-foreground">
						No events yet. Waiting for Lambda data...
					</p>
				) : (
					<div className="space-y-4">
						{events
							.slice()
							.reverse()
							.map((event, index) => (
								<div
									key={`${event.filename}-${index}`}
									className="border rounded-lg p-4 space-y-2">
									<div className="flex items-center justify-between">
										<span className="font-mono text-sm">
											{event.filename}
										</span>
										<span className="text-xs text-muted-foreground">
											{new Date(
												event.timestamp
											).toLocaleString()}
										</span>
									</div>
									<div className="grid grid-cols-2 gap-2 text-sm">
										<div>
											<span className="text-muted-foreground">
												Sound:{" "}
											</span>
											<span
												className={
													event.has_sound
														? "text-green-600"
														: "text-gray-500"
												}>
												{event.has_sound ? "Yes" : "No"}
											</span>
										</div>
										<div>
											<span className="text-muted-foreground">
												Knocking:{" "}
											</span>
											<span
												className={
													event.is_knocking
														? "text-orange-600"
														: "text-gray-500"
												}>
												{event.is_knocking
													? "Yes"
													: "No"}
											</span>
										</div>
										<div className="col-span-2">
											<span className="text-muted-foreground">
												Confidence:{" "}
											</span>
											<span className="font-semibold">
												{(
													event.confidence * 100
												).toFixed(1)}
												%
											</span>
										</div>
									</div>
								</div>
							))}
					</div>
				)}
			</CardContent>
		</Card>
	);
}
