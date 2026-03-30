import type {
	CollaborationStats,
	CommitStats,
	ComplexityStats,
	DeveloperDNA,
	DeveloperProfile,
	GrowthArea,
	HiddenStrength,
	Impact,
	LanguageStat,
	ProjectCard,
	ProjectSkillEvidence,
	TalkingPoint,
} from "../api/types";

type JsonRecord = Record<string, unknown>;

function asRecord(value: unknown): JsonRecord | null {
	if (typeof value !== "object" || value === null || Array.isArray(value)) {
		return null;
	}

	return value as JsonRecord;
}

function pick(record: JsonRecord, ...keys: string[]): unknown {
	for (const key of keys) {
		if (key in record) {
			return record[key];
		}
	}
	return undefined;
}

function asString(value: unknown, fallback = ""): string {
	return typeof value === "string" ? value : fallback;
}

function asNumber(value: unknown, fallback = 0): number {
	return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asStringArray(value: unknown): string[] {
	if (!Array.isArray(value)) {
		return [];
	}

	return value.filter((item): item is string => typeof item === "string");
}

function normalizeArray<T>(
	value: unknown,
	normalizeItem: (item: JsonRecord) => T,
): T[] {
	if (!Array.isArray(value)) {
		return [];
	}

	return value.flatMap((item) => {
		const record = asRecord(item);
		return record ? [normalizeItem(record)] : [];
	});
}

function normalizeDeveloperDNA(
	value: unknown,
	fallback: DeveloperDNA,
): DeveloperDNA {
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		archetype: asString(pick(record, "archetype"), fallback.archetype),
		description: asString(pick(record, "description"), fallback.description),
		defining_traits: asStringArray(
			pick(record, "defining_traits", "definingTraits"),
		),
	};
}

function normalizeHiddenStrength(value: JsonRecord): HiddenStrength {
	return {
		observation: asString(pick(value, "observation")),
		evidence: asString(pick(value, "evidence")),
		why_it_matters: asString(
			pick(value, "why_it_matters", "whyItMatters"),
		),
	};
}

function normalizeGrowthArea(value: JsonRecord): GrowthArea {
	return {
		area: asString(pick(value, "area")),
		observation: asString(pick(value, "observation")),
		suggestion: asString(pick(value, "suggestion")),
	};
}

function normalizeTalkingPoint(value: JsonRecord): TalkingPoint {
	return {
		topic: asString(pick(value, "topic")),
		story: asString(pick(value, "story")),
	};
}

function normalizeCommitStats(
	value: unknown,
	fallback: CommitStats,
): CommitStats {
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		total: asNumber(pick(record, "total"), fallback.total),
		avg_per_week: asNumber(
			pick(record, "avg_per_week", "avgPerWeek"),
			fallback.avg_per_week,
		),
		most_active_period: asString(
			pick(record, "most_active_period", "mostActivePeriod"),
			fallback.most_active_period,
		),
		conventional_commits_pct: asNumber(
			pick(record, "conventional_commits_pct", "conventionalCommitsPct"),
			fallback.conventional_commits_pct,
		),
	};
}

function normalizeLanguageStat(value: JsonRecord): LanguageStat {
	return {
		name: asString(pick(value, "name")),
		file_count: asNumber(pick(value, "file_count", "fileCount")),
		projects: asStringArray(pick(value, "projects")),
	};
}

function normalizeCollaborationStats(
	value: unknown,
	fallback: CollaborationStats,
): CollaborationStats {
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		branch_count: asNumber(
			pick(record, "branch_count", "branchCount"),
			fallback.branch_count,
		),
		merge_frequency: asString(
			pick(record, "merge_frequency", "mergeFrequency"),
			fallback.merge_frequency,
		),
		workflow_style: asString(
			pick(record, "workflow_style", "workflowStyle"),
			fallback.workflow_style,
		),
	};
}

function normalizeComplexityStats(
	value: unknown,
	fallback: ComplexityStats,
): ComplexityStats {
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		frameworks_used: asNumber(
			pick(record, "frameworks_used", "frameworksUsed"),
			fallback.frameworks_used,
		),
		project_types: asStringArray(
			pick(record, "project_types", "projectTypes"),
		),
		distinct_tools: asStringArray(
			pick(record, "distinct_tools", "distinctTools"),
		),
	};
}

function normalizeImpact(value: unknown, fallback: Impact): Impact {
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		commits: normalizeCommitStats(pick(record, "commits"), fallback.commits),
		languages: normalizeArray(
			pick(record, "languages"),
			normalizeLanguageStat,
		),
		collaboration: normalizeCollaborationStats(
			pick(record, "collaboration"),
			fallback.collaboration,
		),
		complexity: normalizeComplexityStats(
			pick(record, "complexity"),
			fallback.complexity,
		),
	};
}

function normalizeProjectSkillEvidence(
	value: JsonRecord,
): ProjectSkillEvidence {
	return {
		skill: asString(pick(value, "skill")),
		evidence: asString(pick(value, "evidence")),
	};
}

function normalizeProjectCard(value: JsonRecord): ProjectCard {
	return {
		name: asString(pick(value, "name")),
		what_it_says_about_you: asString(
			pick(value, "what_it_says_about_you", "whatItSaysAboutYou"),
		),
		skills: normalizeArray(
			pick(value, "skills"),
			normalizeProjectSkillEvidence,
		),
		standout: asString(pick(value, "standout")),
		next_level: asStringArray(pick(value, "next_level", "nextLevel")),
	};
}

export function buildFallbackProfile(rawText: string): DeveloperProfile {
	const resumeStart = rawText.indexOf("# Resume");
	const markdown = resumeStart >= 0 ? rawText.slice(resumeStart) : rawText;

	return {
		resume_markdown: markdown,
		developer_dna: {
			archetype: "Developer",
			description: "Profile generated from your code repositories.",
			defining_traits: [],
		},
		hidden_strengths: [],
		growth_areas: [],
		talking_points: [],
		impact: {
			commits: {
				total: 0,
				avg_per_week: 0,
				most_active_period: "",
				conventional_commits_pct: 0,
			},
			languages: [],
			collaboration: {
				branch_count: 0,
				merge_frequency: "",
				workflow_style: "",
			},
			complexity: { frameworks_used: 0, project_types: [], distinct_tools: [] },
		},
		projects: [],
	};
}

export function normalizeDeveloperProfile(
	value: unknown,
	rawText = "",
): DeveloperProfile {
	const fallback = buildFallbackProfile(rawText);
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		resume_markdown: asString(
			pick(record, "resume_markdown", "resumeMarkdown"),
			fallback.resume_markdown,
		),
		developer_dna: normalizeDeveloperDNA(
			pick(record, "developer_dna", "developerDNA"),
			fallback.developer_dna,
		),
		hidden_strengths: normalizeArray(
			pick(record, "hidden_strengths", "hiddenStrengths"),
			normalizeHiddenStrength,
		),
		growth_areas: normalizeArray(
			pick(record, "growth_areas", "growthAreas"),
			normalizeGrowthArea,
		),
		talking_points: normalizeArray(
			pick(record, "talking_points", "talkingPoints"),
			normalizeTalkingPoint,
		),
		impact: normalizeImpact(pick(record, "impact"), fallback.impact),
		projects: normalizeArray(pick(record, "projects"), normalizeProjectCard),
	};
}
