import { afterEach, expect, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import type { PortfolioDashboard as PortfolioDashboardData } from "../api/types";
import { PortfolioDashboard } from "./PortfolioDashboard";

let rendered: Awaited<ReturnType<typeof testRender>> | null = null;

afterEach(async () => {
	if (rendered) {
		rendered.renderer.destroy();
		rendered = null;
	}
});

test("PortfolioDashboard renders timeline, heatmap, and ranked projects", async () => {
	const dashboard: PortfolioDashboardData = {
		skills_timeline: [
			{
				skill: "TypeScript",
				first_seen: "2024-01-01",
				last_seen: "2025-03-01",
				projects_count: 3,
				depth_score: 2.91,
			},
		],
		activity_heatmap: {
			daily_activity: {
				"2025-02-01": 2,
				"2025-02-02": 5,
				"2025-02-03": 1,
			},
			total_days_active: 3,
			max_daily_commits: 5,
			date_range: { start: "2025-02-01", end: "2025-02-03" },
		},
		top_projects: [
			{
				project_name: "artifact-miner",
				project_type: "TUI",
				score: 0.93,
				contribution_pct: 77.5,
				commit_total: 128,
				first_commit: "2024-01-01",
				last_commit: "2025-03-01",
				recency_score: 0.96,
				activity_focus: "feature 61%, refactor 23%",
				latest_change: "add dashboard preview mode",
				evolution_note: "Evolved over 425 days of commits.",
			},
		],
	};

	rendered = await testRender(<PortfolioDashboard dashboard={dashboard} />, {
		width: 130,
		height: 40,
	});
	await rendered.renderOnce();
	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Skills Timeline");
	expect(frame).toContain("Activity Heatmap");
	expect(frame).toContain("Top Projects");
	expect(frame).toContain("TypeScript");
	expect(frame).toContain("artifact-miner");
	expect(frame).toContain("Evolved over 425 days of commits.");
});

test("PortfolioDashboard shows a clear empty state without data", async () => {
	rendered = await testRender(<PortfolioDashboard />, {
		width: 90,
		height: 20,
	});
	await rendered.renderOnce();
	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Portfolio insights unavailable for this run.");
});

test("PortfolioDashboard shows unavailable state when any section is missing", async () => {
	const partial: PortfolioDashboardData = {
		skills_timeline: [
			{
				skill: "TypeScript",
				first_seen: "2024-01-01",
				last_seen: "2025-01-01",
				projects_count: 1,
				depth_score: 2.2,
			},
		],
		activity_heatmap: {
			daily_activity: {},
			total_days_active: 0,
			max_daily_commits: 0,
			date_range: { start: null, end: null },
		},
		top_projects: [],
	};

	rendered = await testRender(<PortfolioDashboard dashboard={partial} />, {
		width: 90,
		height: 20,
	});
	await rendered.renderOnce();

	expect(rendered.captureCharFrame()).toContain(
		"Portfolio insights unavailable for this run.",
	);
});
