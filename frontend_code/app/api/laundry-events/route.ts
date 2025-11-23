import {NextRequest, NextResponse} from "next/server";
import fs from "fs";
import path from "path";

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

// File-based storage for persistence across serverless invocations
const EVENTS_FILE = path.join(process.cwd(), "data", "events.json");

// Ensure data directory exists
function ensureDataDir() {
	const dataDir = path.join(process.cwd(), "data");
	if (!fs.existsSync(dataDir)) {
		fs.mkdirSync(dataDir, {recursive: true});
	}
}

// Read events from file
function readEvents(): LaundryEventPayload[] {
	try {
		ensureDataDir();
		if (fs.existsSync(EVENTS_FILE)) {
			const data = fs.readFileSync(EVENTS_FILE, "utf-8");
			return JSON.parse(data);
		}
	} catch (error) {
		console.error("Error reading events file:", error);
	}
	return [];
}

// Write events to file
function writeEvents(events: LaundryEventPayload[]) {
	try {
		ensureDataDir();
		fs.writeFileSync(EVENTS_FILE, JSON.stringify(events, null, 2), "utf-8");
	} catch (error) {
		console.error("Error writing events file:", error);
	}
}

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
				{
					error: "has_sound, is_speech, and is_clapping must be boolean"
				},
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

		// Read existing events
		const events = readEvents();

		// Store event
		events.push(event);

		// Keep only last 100 events to avoid file bloat
		if (events.length > 100) {
			events.shift();
		}

		// Write back to file
		writeEvents(events);

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
	// Read events from file
	const events = readEvents();

	// Return recent events
	return NextResponse.json({
		events: events.slice(-10), // Return last 10 events
		total: events.length
	});
}
