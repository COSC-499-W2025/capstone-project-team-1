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
});
