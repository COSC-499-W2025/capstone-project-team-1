import { expect, test } from "bun:test";
import { ApiError } from "../api/client";
import type { ResumeV3Output } from "../api/types";
import {
	buildLineDiff,
	createUnifiedDiff,
	keyedLines,
	resumeStats,
	resumeToSections,
	resumeToText,
	toErrorMessage,
} from "./index";

const sampleResume: ResumeV3Output = {
	professional_summary: "Backend-focused software developer",
	skills_section: "Python\nTypeScript",
	developer_profile: "Enjoys shipping practical tooling.",
	projects: [
		{
			name: "Artifact Miner",
			type: "CLI",
			primary_language: "TypeScript",
			frameworks: ["React", "OpenTUI"],
			contribution_pct: 62.4,
			commit_breakdown: { feat: 8 },
			period: { first_commit: "2025-09-01", last_commit: "2025-11-01" },
			description: "Terminal UI for resume generation",
			bullets: ["Built OpenTUI flows", "Added API integration"],
			narrative: "Delivered the frontend migration.",
		},
	],
	metadata: {
		model_used: "qwen",
		models_used: ["qwen", "phi"],
		stage: "POLISH",
		generation_time_seconds: 12.3,
		errors: [],
		quality_metrics: {},
	},
	portfolio: {
		total_projects: 1,
		total_commits: 18,
		languages_used: ["TypeScript"],
		frameworks_used: ["React", "OpenTUI"],
		project_types: { CLI: 1 },
		top_skills: ["TypeScript", "React"],
	},
};

test("resumeToSections builds ordered preview sections", () => {
	const sections = resumeToSections(sampleResume);

	expect(sections.map((section) => section.id)).toEqual([
		"summary",
		"skills",
		"projects",
		"profile",
		"metadata",
	]);
	expect(sections[2]?.lines).toContain("Artifact Miner (CLI)");
	expect(sections[2]?.lines).toContain("- Built OpenTUI flows");
});

test("resumeToText renders a readable document", () => {
	const text = resumeToText(sampleResume);

	expect(text).toContain("PROFESSIONAL SUMMARY");
	expect(text).toContain("Artifact Miner (CLI)");
	expect(text).toContain("Generation Time: 12.3s");
});

test("resumeStats surfaces compact sidebar metrics", () => {
	const stats = resumeStats(sampleResume);

	expect(stats).toEqual([
		{ label: "Projects", value: "1" },
		{ label: "Languages", value: "TypeScript" },
		{ label: "Commits", value: "18" },
		{ label: "Gen time", value: "12.3s" },
		{ label: "Stage", value: "POLISH" },
	]);
});

test("buildLineDiff and createUnifiedDiff mark changed lines", () => {
	const finalResume: ResumeV3Output = {
		...sampleResume,
		professional_summary: "Backend and platform engineer",
	};

	const rows = buildLineDiff(sampleResume, finalResume);
	expect(rows.some((row) => row.changed)).toBe(true);

	const diff = createUnifiedDiff(
		resumeToText(sampleResume),
		resumeToText(finalResume),
	);
	expect(diff).toContain("--- draft");
	expect(diff).toContain("+++ final");
	expect(diff).toContain("+Backend and platform engineer");
});

test("keyedLines disambiguates repeated content", () => {
	const lines = keyedLines(["same", "same", "other"], "draft");

	expect(lines).toEqual([
		{ key: "draft-same-1", text: "same" },
		{ key: "draft-same-2", text: "same" },
		{ key: "draft-other-1", text: "other" },
	]);
});

test("toErrorMessage normalizes API, Error, and unknown inputs", () => {
	expect(toErrorMessage(new ApiError(400, "Bad request"))).toBe("Bad request");
	expect(toErrorMessage(new Error("Broken"))).toBe("Broken");
	expect(toErrorMessage({ nope: true })).toBe("Unexpected error");
});
