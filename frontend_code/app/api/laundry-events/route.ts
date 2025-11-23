import {NextRequest, NextResponse} from "next/server";

export interface LaundryEventPayload {
	filename: string;
	timestamp: string;
	has_sound: boolean;
	is_speech: boolean;
	is_voice: boolean;
	is_clapping: boolean;
	confidence: number;
	processed_at?: string;
}

// In-memory storage (replace with database/Redis in production)
const events: LaundryEventPayload[] = [];

export async function POST(request: NextRequest) {
	try {
		const body: LaundryEventPayload = await request.json();

		// Validate required fields
		if (!body.filename || !body.timestamp) {
			return NextResponse.json(
				{error: "Missing required fields: filename, timestamp"},
				{status: 400}
			);
		}

		// Validate types
		if (
			typeof body.has_sound !== "boolean" ||
			typeof body.is_speech !== "boolean" ||
			typeof body.is_clapping !== "boolean"
		) {
			return NextResponse.json(
				{error: "has_sound, is_speech, and is_clapping must be boolean"},
				{status: 400}
			);
		}

		if (
			typeof body.confidence !== "number" ||
			body.confidence < 0 ||
			body.confidence > 1
		) {
			return NextResponse.json(
				{error: "confidence must be a number between 0 and 1"},
				{status: 400}
			);
		}

		// Add processed_at if not provided
		const event: LaundryEventPayload = {
			...body,
			processed_at: body.processed_at || new Date().toISOString()
		};

		// Store event (in-memory for now)
		events.push(event);

		// Keep only last 100 events to avoid memory issues
		if (events.length > 100) {
			events.shift();
		}

		console.log("Received laundry event:", event);

		return NextResponse.json({success: true, event}, {status: 201});
	} catch (error) {
		console.error("Error processing laundry event:", error);
		return NextResponse.json(
			{error: "Invalid JSON payload"},
			{status: 400}
		);
	}
}

export async function GET() {
	// Optional: endpoint to retrieve recent events
	return NextResponse.json({
		events: events.slice(-10), // Return last 10 events
		total: events.length
	});
}
