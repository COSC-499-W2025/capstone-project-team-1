import type { ResumeV3Output } from "../api/types";

const EMPTY_PREVIEW_TEXT = "No resume data available yet.";

function section(title: string): string {
	return `${title}\n${"-".repeat(title.length)}`;
}

export function resumeToText(data: ResumeV3Output | null): string {
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

export function resumeToLines(data: ResumeV3Output | null): string[] {
	return resumeToText(data).split("\n");
}

export interface DiffRow {
	lineNumber: number;
	left: string;
	right: string;
	changed: boolean;
}

export interface KeyedLine {
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

export function buildLineDiff(
	draft: ResumeV3Output | null,
	finalOutput: ResumeV3Output | null,
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
