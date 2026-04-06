import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act, useEffect, useState } from "react";
import type { ResumeV3Output } from "../api/types";
import { AppProvider, useAppState } from "../context/AppContext";

type KeyboardEventLike = { name: string };

type KeyboardHandler = ((key: KeyboardEventLike) => void) | null;

function setKeyboardHandler(handler: KeyboardHandler) {
	(globalThis as { __opentuiKeyboardHandler?: KeyboardHandler }).__opentuiKeyboardHandler =
		handler;
}

function getKeyboardHandler(): KeyboardHandler {
	return (
		(globalThis as { __opentuiKeyboardHandler?: KeyboardHandler })
			.__opentuiKeyboardHandler ?? null
	);
}

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		setKeyboardHandler(handler);
	},
}));

const { ResumePreview } = await import("./ResumePreview");

const sampleOutput: ResumeV3Output = {
	professional_summary: "Builder of practical developer tooling.",
	skills_section: "TypeScript, Python",
	developer_profile: "Focus on reliable workflows and user experience.",
	projects: [
		{
			name: "artifact-miner",
			type: "TUI",
			primary_language: "TypeScript",
			frameworks: ["React"],
			contribution_pct: 80,
			commit_breakdown: { feature: 10, refactor: 4 },
			period: {
				first_commit: "2024-01-01",
				last_commit: "2025-01-01",
			},
			description: "Portfolio generation pipeline.",
			bullets: ["Implemented deterministic ranking."],
			bullet_fact_ids: [],
			narrative: null,
		},
	],
	metadata: {
		model_used: "llama3.2",
		models_used: ["llama3.2"],
		stage: "polish",
		generation_time_seconds: 12,
		errors: [],
		quality_metrics: {},
	},
	portfolio_dashboard: {
		skills_timeline: [
			{
				skill: "TypeScript",
				first_seen: "2024-01-01",
				last_seen: "2025-01-01",
				projects_count: 1,
				depth_score: 2.4,
			},
		],
		activity_heatmap: {
			daily_activity: { "2025-01-01": 3 },
			total_days_active: 1,
			max_daily_commits: 3,
			date_range: { start: "2025-01-01", end: "2025-01-01" },
		},
		top_projects: [
			{
				project_name: "artifact-miner",
				project_type: "TUI",
				score: 0.92,
				contribution_pct: 80,
				commit_total: 14,
				first_commit: "2024-01-01",
				last_commit: "2025-01-01",
				recency_score: 0.8,
				activity_focus: "feature 71%",
				latest_change: "add portfolio dashboard",
				evolution_note: "Evolved over 365 days of commits.",
			},
		],
	},
};

function SeededResumePreview() {
	const { setResumeV3Draft, setResumeV3Output } = useAppState();
	const [ready, setReady] = useState(false);

	useEffect(() => {
		setResumeV3Draft(sampleOutput);
		setResumeV3Output(sampleOutput);
		setReady(true);
	}, [setResumeV3Draft, setResumeV3Output]);

	if (!ready) {
		return null;
	}

	return <ResumePreview onRestart={() => {}} onBack={() => {}} />;
}

function pressKey(key: KeyboardEventLike) {
	const keyboardHandler = getKeyboardHandler();
	if (!keyboardHandler) {
		throw new Error("ResumePreview keyboard handler was not registered");
	}
	keyboardHandler(key);
}

let rendered: Awaited<ReturnType<typeof testRender>> | null = null;

afterEach(async () => {
	setKeyboardHandler(null);
	if (rendered) {
		await act(async () => {
			rendered?.renderer.destroy();
		});
		rendered = null;
	}
});

test("ResumePreview switches to portfolio dashboard mode via keyboard", async () => {
	rendered = await testRender(
		<AppProvider>
			<SeededResumePreview />
		</AppProvider>,
		{ width: 140, height: 42 },
	);

	await act(async () => {
		await rendered?.renderOnce();
		await Promise.resolve();
		await rendered?.renderOnce();
	});

	await act(async () => {
		pressKey({ name: "tab" });
		pressKey({ name: "tab" });
		await rendered?.renderOnce();
	});

	const frame = rendered.captureCharFrame();
	expect(frame).toContain("Portfolio");
	expect(frame).toContain("Skills Timeline");
	expect(frame).toContain("Top Projects");
	expect(frame).toContain("artifact-miner");
});
