interface ResumeProjectPeriod {
	first_commit: string | null;
	last_commit: string | null;
}

interface ResumeProject {
	name: string;
	type: string;
	primary_language: string | null;
	frameworks: string[];
	contribution_pct: number | null;
	commit_breakdown: Record<string, number>;
	period: ResumeProjectPeriod;
	description?: string;
	bullets?: string[];
	bullet_fact_ids?: string[][];
	narrative?: string;
}

interface ResumeMetadata {
	model_used: string | null;
	models_used: string[];
	stage: string;
	generation_time_seconds: number;
	errors: string[];
	quality_metrics: Record<string, unknown>;
}

interface ResumePortfolio {
	total_projects: number;
	total_commits: number;
	languages_used: string[];
	frameworks_used: string[];
	project_types: Record<string, number>;
	top_skills: string[];
}

export interface ResumeRenderData {
	professional_summary: string;
	skills_section: string;
	developer_profile: string;
	projects: ResumeProject[];
	metadata: ResumeMetadata;
	portfolio?: ResumePortfolio;
}

export interface ResumeSection {
	id: string;
	tocLabel: string;
	headerText: string;
	lines: string[];
}

export function resumeToSections(data: ResumeRenderData | null): ResumeSection[] {
	if (!data) {
		return [
			{
				id: "summary",
				tocLabel: "Summary",
				headerText: "PROFESSIONAL SUMMARY",
				lines: ["No resume data available yet."],
			},
			{
				id: "skills",
				tocLabel: "Skills",
				headerText: "TECHNICAL SKILLS",
				lines: [],
			},
			{
				id: "projects",
				tocLabel: "Projects",
				headerText: "PROJECTS",
				lines: [],
			},
			{
				id: "profile",
				tocLabel: "Dev Profile",
				headerText: "DEVELOPER PROFILE",
				lines: [],
			},
			{
				id: "metadata",
				tocLabel: "Metadata",
				headerText: "METADATA",
				lines: [],
			},
		];
	}

	const skillsLines = data.skills_section
		? data.skills_section.split("\n")
		: ["(empty)"];

	const projectLines: string[] = [];
	if (!data.projects.length) {
		projectLines.push("(none)");
	} else {
		for (const project of data.projects) {
			const frameworkText = project.frameworks.length
				? project.frameworks.join(", ")
				: "None listed";
			const contribution =
				project.contribution_pct === null
					? "n/a"
					: `${Math.round(project.contribution_pct)}%`;

			projectLines.push(`${project.name} (${project.type})`);
			projectLines.push(`Language: ${project.primary_language || "n/a"}`);
			projectLines.push(`Frameworks: ${frameworkText}`);
			projectLines.push(`Contribution: ${contribution}`);
			if (project.description) {
				projectLines.push(`Description: ${project.description}`);
			}
			if (project.bullets?.length) {
				for (const bullet of project.bullets) {
					projectLines.push(`- ${bullet}`);
				}
			}
			if (project.narrative) {
				projectLines.push(`Narrative: ${project.narrative}`);
			}
			projectLines.push("");
		}
	}

	const metadataLines: string[] = [
		`Stage: ${data.metadata.stage || "unknown"}`,
		`Models: ${data.metadata.models_used.length ? data.metadata.models_used.join(" -> ") : "n/a"}`,
		`Generation Time: ${Number(data.metadata.generation_time_seconds || 0).toFixed(1)}s`,
	];

	if (data.metadata.errors.length) {
		metadataLines.push("Errors:");
		for (const error of data.metadata.errors) {
			metadataLines.push(`- ${error}`);
		}
	}

	return [
		{
			id: "summary",
			tocLabel: "Summary",
			headerText: "PROFESSIONAL SUMMARY",
			lines: data.professional_summary
				? data.professional_summary.split("\n")
				: ["(empty)"],
		},
		{
			id: "skills",
			tocLabel: "Skills",
			headerText: "TECHNICAL SKILLS",
			lines: skillsLines,
		},
		{
			id: "projects",
			tocLabel: "Projects",
			headerText: "PROJECTS",
			lines: projectLines,
		},
		{
			id: "profile",
			tocLabel: "Dev Profile",
			headerText: "DEVELOPER PROFILE",
			lines: data.developer_profile
				? data.developer_profile.split("\n")
				: ["(empty)"],
		},
		{
			id: "metadata",
			tocLabel: "Metadata",
			headerText: "METADATA",
			lines: metadataLines,
		},
	];
}

const EMPTY_PREVIEW_TEXT = "No resume data available yet.";

function section(title: string): string {
	return `${title}\n${"-".repeat(title.length)}`;
}

export function resumeToText(data: ResumeRenderData | null): string {
	if (!data) {
		return EMPTY_PREVIEW_TEXT;
	}

	const lines: string[] = [];

	lines.push(section("PROFESSIONAL SUMMARY"));
	lines.push(data.professional_summary || "(empty)");
	lines.push("");

	lines.push(section("TECHNICAL SKILLS"));
	lines.push(data.skills_section || "(empty)");
	lines.push("");

	lines.push(section("PROJECTS"));
	if (!data.projects.length) {
		lines.push("(none)");
	} else {
		for (const project of data.projects) {
			const frameworkText = project.frameworks.length
				? project.frameworks.join(", ")
				: "None listed";
			const contribution =
				project.contribution_pct === null
					? "n/a"
					: `${Math.round(project.contribution_pct)}%`;

			lines.push("");
			lines.push(`${project.name} (${project.type})`);
			lines.push(`Language: ${project.primary_language || "n/a"}`);
			lines.push(`Frameworks: ${frameworkText}`);
			lines.push(`Contribution: ${contribution}`);

			if (project.description) {
				lines.push(`Description: ${project.description}`);
			}
			if (project.bullets?.length) {
				for (const bullet of project.bullets) {
					lines.push(`- ${bullet}`);
				}
			}
			if (project.narrative) {
				lines.push(`Narrative: ${project.narrative}`);
			}
		}
	}

	lines.push("");
	lines.push(section("DEVELOPER PROFILE"));
	lines.push(data.developer_profile || "(empty)");
	lines.push("");

	lines.push(section("METADATA"));
	lines.push(`Stage: ${data.metadata.stage || "unknown"}`);
	lines.push(
		`Models: ${data.metadata.models_used.length ? data.metadata.models_used.join(" -> ") : "n/a"}`,
	);
	lines.push(
		`Generation Time: ${Number(data.metadata.generation_time_seconds || 0).toFixed(1)}s`,
	);

	if (data.metadata.errors.length) {
		lines.push("Errors:");
		for (const error of data.metadata.errors) {
			lines.push(`- ${error}`);
		}
	}

	return lines.join("\n");
}

export function resumeToLines(data: ResumeRenderData | null): string[] {
	return resumeToText(data).split("\n");
}

export interface DiffRow {
	lineNumber: number;
	left: string;
	right: string;
	changed: boolean;
}

interface KeyedLine {
	key: string;
	text: string;
}

export function keyedLines(lines: string[], prefix: string): KeyedLine[] {
	const counts = new Map<string, number>();
	const keyed: KeyedLine[] = [];

	for (const line of lines) {
		const nextCount = (counts.get(line) || 0) + 1;
		counts.set(line, nextCount);
		keyed.push({
			key: `${prefix}-${line}-${nextCount}`,
			text: line,
		});
	}

	return keyed;
}

export interface StatLine {
	label: string;
	value: string;
}

export function resumeStats(data: ResumeV3Output | null): StatLine[] {
	if (!data) {
		return [];
	}

	const stats: StatLine[] = [];
	stats.push({ label: "Projects", value: String(data.projects.length) });

	const languages = data.portfolio?.languages_used;
	if (languages?.length) {
		stats.push({ label: "Languages", value: languages.join(", ") });
	}

	const totalCommits = data.portfolio?.total_commits;
	if (totalCommits != null) {
		stats.push({ label: "Commits", value: String(totalCommits) });
	}

	const genTime = data.metadata.generation_time_seconds;
	if (genTime) {
		stats.push({ label: "Gen time", value: `${Number(genTime).toFixed(1)}s` });
	}

	if (data.metadata.stage) {
		stats.push({ label: "Stage", value: data.metadata.stage });
	}

	return stats;
}

export function createUnifiedDiff(oldText: string, newText: string): string {
	const oldLines = oldText.split("\n");
	const newLines = newText.split("\n");
	const result: string[] = [];

	result.push("--- draft");
	result.push("+++ final");
	result.push(`@@ -1,${oldLines.length} +1,${newLines.length} @@`);

	const maxLength = Math.max(oldLines.length, newLines.length);
	for (let index = 0; index < maxLength; index += 1) {
		const oldLine = index < oldLines.length ? oldLines[index] : undefined;
		const newLine = index < newLines.length ? newLines[index] : undefined;

		if (oldLine === newLine) {
			result.push(` ${oldLine}`);
			continue;
		}

		if (oldLine !== undefined) {
			result.push(`-${oldLine}`);
		}
		if (newLine !== undefined) {
			result.push(`+${newLine}`);
		}
	}

	return result.join("\n");
}

export function buildLineDiff(
	draft: ResumeRenderData | null,
	finalOutput: ResumeRenderData | null,
): DiffRow[] {
	const leftLines = resumeToLines(draft);
	const rightLines = resumeToLines(finalOutput);
	const maxLength = Math.max(leftLines.length, rightLines.length);

	const rows: DiffRow[] = [];
	for (let index = 0; index < maxLength; index += 1) {
		const left = leftLines[index] ?? "";
		const right = rightLines[index] ?? "";
		rows.push({
			lineNumber: index + 1,
			left,
			right,
			changed: left !== right,
		});
	}

	return rows;
}
