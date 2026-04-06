import { expect, test } from "bun:test";
import {
	buildFallbackProfile,
	normalizeDeveloperProfile,
} from "./profileNormalization";

test("normalizeDeveloperProfile backfills missing sections from partial model output", () => {
	const profile = normalizeDeveloperProfile(
		{
			resume_markdown: "# Resume\n\nBuilt cool things",
			developer_dna: {
				archetype: "Full-Stack Builder",
				description: "You ship across the stack.",
			},
			projects: [
				{
					name: "artifactminer",
					what_it_says_about_you: "You like end-to-end product work.",
				},
			],
		},
		"# Resume\n\nFallback resume",
	);

	expect(profile.hidden_strengths).toEqual([]);
	expect(profile.growth_areas).toEqual([]);
	expect(profile.talking_points).toEqual([]);
	expect(profile.impact.languages).toEqual([]);
	expect(profile.impact.collaboration.workflow_style).toBe("");
	expect(profile.impact.complexity.project_types).toEqual([]);
	expect(profile.projects).toEqual([
		{
			name: "artifactminer",
			what_it_says_about_you: "You like end-to-end product work.",
			skills: [],
			standout: "",
			next_level: [],
		},
	]);
	expect(profile.portfolio_dashboard?.skills_timeline).toEqual([]);
	expect(profile.portfolio_dashboard?.top_projects).toEqual([
		{
			project_name: "artifactminer",
			project_type: "",
			score: 0,
			contribution_pct: null,
			commit_total: 0,
			first_commit: null,
			last_commit: null,
			recency_score: 0,
			activity_focus: null,
			latest_change: null,
			evolution_note: null,
		},
	]);
});

test("normalizeDeveloperProfile filters invalid entries and preserves valid nested values", () => {
	const profile = normalizeDeveloperProfile({
		resume_markdown: "# Resume\n\nGenerated",
		developer_dna: {
			archetype: "Systems Thinker",
			description: "You build with structure.",
			defining_traits: ["Testing discipline", 99, "Defensive coding"],
		},
		hidden_strengths: [
			null,
			{
				observation: "You write defensive code",
				evidence: "Fallbacks are present across flows",
			},
		],
		impact: {
			commits: { total: 12, avg_per_week: 3, conventional_commits_pct: 50 },
			languages: [
				"TypeScript",
				{ name: "TypeScript", file_count: 8, projects: ["tui", false, "api"] },
			],
			collaboration: {
				workflow_style: "feature branches with PRs",
				branch_count: 4,
			},
			complexity: { frameworks_used: 2, distinct_tools: ["Docker", 7] },
		},
		projects: [
			"artifactminer",
			{
				name: "capstone",
				what_it_says_about_you: "You can wrangle a large student project.",
				skills: [{ skill: "TypeScript", evidence: "TUI screens" }, null],
				next_level: ["Add schema validation", 123],
			},
		],
	});

	expect(profile.developer_dna.defining_traits).toEqual([
		"Testing discipline",
		"Defensive coding",
	]);
	expect(profile.hidden_strengths).toEqual([
		{
			observation: "You write defensive code",
			evidence: "Fallbacks are present across flows",
			why_it_matters: "",
		},
	]);
	expect(profile.impact.commits).toEqual({
		total: 12,
		avg_per_week: 3,
		most_active_period: "",
		conventional_commits_pct: 50,
	});
	expect(profile.impact.languages).toEqual([
		{ name: "TypeScript", file_count: 8, projects: ["tui", "api"] },
	]);
	expect(profile.impact.collaboration).toEqual({
		branch_count: 4,
		merge_frequency: "",
		workflow_style: "feature branches with PRs",
	});
	expect(profile.impact.complexity).toEqual({
		frameworks_used: 2,
		project_types: [],
		distinct_tools: ["Docker"],
	});
	expect(profile.projects).toEqual([
		{
			name: "capstone",
			what_it_says_about_you: "You can wrangle a large student project.",
			skills: [{ skill: "TypeScript", evidence: "TUI screens" }],
			standout: "",
			next_level: ["Add schema validation"],
		},
	]);
	expect(profile.portfolio_dashboard?.skills_timeline).toEqual([
		{
			skill: "TypeScript",
			first_seen: null,
			last_seen: null,
			projects_count: 2,
			depth_score: 0,
		},
	]);
	expect(profile.portfolio_dashboard?.top_projects[0]?.project_name).toBe("capstone");
});

test("normalizeDeveloperProfile accepts and sanitizes portfolio dashboard payload", () => {
	const profile = normalizeDeveloperProfile({
		resume_markdown: "# Resume\n\nGenerated",
		developer_dna: {
			archetype: "Platform Engineer",
			description: "You build resilient systems.",
			defining_traits: ["Observability"],
		},
		impact: {
			commits: { total: 30, avg_per_week: 5, conventional_commits_pct: 40 },
			languages: [{ name: "Go", file_count: 4, projects: ["svc"] }],
			collaboration: { branch_count: 2, workflow_style: "feature branches" },
			complexity: { frameworks_used: 1, project_types: ["API"] },
		},
		projects: [
			{
				name: "svc",
				what_it_says_about_you: "You ship backend services.",
			},
		],
		portfolio_dashboard: {
			skills_timeline: [
				{
					skill: "Go",
					first_seen: "2024-01-05",
					last_seen: "2025-02-01",
					projects_count: 1,
					depth_score: 2.4,
				},
			],
			activity_heatmap: {
				daily_activity: {
					"2025-01-03": 3,
					"2025-01-04": -2,
				},
				total_days_active: 1,
				max_daily_commits: 3,
				date_range: {
					start: "2025-01-03",
					end: "2025-01-04",
				},
			},
			top_projects: [
				{
					project_name: "svc",
					project_type: "API",
					score: 0.88,
					contribution_pct: 71,
					commit_total: 42,
					first_commit: "2024-01-05",
					last_commit: "2025-02-01",
					recency_score: 0.7,
					activity_focus: "feature 60%",
					latest_change: "add health checks",
					evolution_note: "Evolved over 393 days of commits.",
				},
			],
		},
	});

	expect(profile.portfolio_dashboard?.skills_timeline[0]).toEqual({
		skill: "Go",
		first_seen: "2024-01-05",
		last_seen: "2025-02-01",
		projects_count: 1,
		depth_score: 2.4,
	});
	expect(profile.portfolio_dashboard?.activity_heatmap.daily_activity).toEqual({
		"2025-01-03": 3,
	});
	expect(profile.portfolio_dashboard?.top_projects[0]?.project_name).toBe("svc");
});

test("buildFallbackProfile uses the resume section when present", () => {
	const profile = buildFallbackProfile(
		"Some narration\n# Resume\n\n- Bullet one\n- Bullet two",
	);

	expect(profile.resume_markdown).toBe(
		"# Resume\n\n- Bullet one\n- Bullet two",
	);
	expect(profile.developer_dna.archetype).toBe("Developer");
	expect(profile.impact.commits.total).toBe(0);
	expect(profile.portfolio_dashboard?.top_projects).toEqual([]);
});
