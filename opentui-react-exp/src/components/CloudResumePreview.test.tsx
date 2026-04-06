import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type { DeveloperProfile } from "../api/types";

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

const { CloudResumePreview } = await import("./CloudResumePreview");

const profileFixture: DeveloperProfile = {
	resume_markdown: "# Resume\n\nGenerated profile",
	developer_dna: {
		archetype: "Tooling Engineer",
		description: "You build practical development tools.",
		defining_traits: ["Pragmatic", "Iterative"],
	},
	hidden_strengths: [],
	growth_areas: [],
	talking_points: [],
	impact: {
		commits: {
			total: 42,
			avg_per_week: 3,
			most_active_period: "Jan-Mar 2025",
			conventional_commits_pct: 65,
		},
		languages: [{ name: "TypeScript", file_count: 30, projects: ["artifact-miner"] }],
		collaboration: {
			branch_count: 8,
			merge_frequency: "weekly",
			workflow_style: "feature branches with PRs",
		},
		complexity: {
			frameworks_used: 3,
			project_types: ["TUI", "API"],
			distinct_tools: ["Bun", "FastAPI"],
		},
	},
	projects: [
		{
			name: "artifact-miner",
			what_it_says_about_you: "You can ship complete product loops.",
			skills: [{ skill: "TypeScript", evidence: "OpenTUI components" }],
			standout: "Deterministic portfolio ranking",
			next_level: ["Add staged rollout support"],
		},
	],
	portfolio_dashboard: {
		skills_timeline: [
			{
				skill: "TypeScript",
				first_seen: "2024-02-01",
				last_seen: "2025-02-01",
				projects_count: 2,
				depth_score: 2.9,
			},
		],
		activity_heatmap: {
			daily_activity: {
				"2025-02-01": 3,
				"2025-02-02": 5,
			},
			total_days_active: 2,
			max_daily_commits: 5,
			date_range: {
				start: "2025-02-01",
				end: "2025-02-02",
			},
		},
		top_projects: [
			{
				project_name: "artifact-miner",
				project_type: "TUI",
				score: 0.9,
				contribution_pct: 82,
				commit_total: 70,
				first_commit: "2024-02-01",
				last_commit: "2025-02-01",
				recency_score: 0.95,
				activity_focus: "feature 63%",
				latest_change: "wire dashboard tab",
				evolution_note: "Evolved over 365 days of commits.",
			},
		],
	},
};

function pressKey(key: KeyboardEventLike) {
	const keyboardHandler = getKeyboardHandler();
	if (!keyboardHandler) {
		throw new Error("CloudResumePreview keyboard handler was not registered");
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

test("CloudResumePreview switches tabs and renders dashboard via 1 key", async () => {
	rendered = await testRender(
		<CloudResumePreview
			profile={profileFixture}
			onBack={() => {}}
			onRestart={() => {}}
		/>,
		{ width: 140, height: 42 },
	);

	await act(async () => {
		await rendered?.renderOnce();
	});

	await act(async () => {
		pressKey({ name: "1" });
		await rendered?.renderOnce();
	});

	const frame = rendered.captureCharFrame();
	expect(frame).toContain("Dashboard");
	expect(frame).toContain("Skills Timeline");
	expect(frame).toContain("Top Projects");
	expect(frame).toContain("artifact-miner");
});
