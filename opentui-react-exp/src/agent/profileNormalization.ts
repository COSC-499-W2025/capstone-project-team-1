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
		archetype: asString(record.archetype, fallback.archetype),
		description: asString(record.description, fallback.description),
		defining_traits: asStringArray(record.defining_traits),
	};
}

function normalizeHiddenStrength(value: JsonRecord): HiddenStrength {
	return {
		observation: asString(value.observation),
		evidence: asString(value.evidence),
		why_it_matters: asString(value.why_it_matters),
	};
}

function normalizeGrowthArea(value: JsonRecord): GrowthArea {
	return {
		area: asString(value.area),
		observation: asString(value.observation),
		suggestion: asString(value.suggestion),
	};
}

function normalizeTalkingPoint(value: JsonRecord): TalkingPoint {
	return {
		topic: asString(value.topic),
		story: asString(value.story),
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
		total: asNumber(record.total, fallback.total),
		avg_per_week: asNumber(record.avg_per_week, fallback.avg_per_week),
		most_active_period: asString(
			record.most_active_period,
			fallback.most_active_period,
		),
		conventional_commits_pct: asNumber(
			record.conventional_commits_pct,
			fallback.conventional_commits_pct,
		),
	};
}

function normalizeLanguageStat(value: JsonRecord): LanguageStat {
	return {
		name: asString(value.name),
		file_count: asNumber(value.file_count),
		projects: asStringArray(value.projects),
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
		branch_count: asNumber(record.branch_count, fallback.branch_count),
		merge_frequency: asString(record.merge_frequency, fallback.merge_frequency),
		workflow_style: asString(record.workflow_style, fallback.workflow_style),
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
		frameworks_used: asNumber(record.frameworks_used, fallback.frameworks_used),
		project_types: asStringArray(record.project_types),
		distinct_tools: asStringArray(record.distinct_tools),
	};
}

function normalizeImpact(value: unknown, fallback: Impact): Impact {
	const record = asRecord(value);
	if (!record) {
		return fallback;
	}

	return {
		commits: normalizeCommitStats(record.commits, fallback.commits),
		languages: normalizeArray(record.languages, normalizeLanguageStat),
		collaboration: normalizeCollaborationStats(
			record.collaboration,
			fallback.collaboration,
		),
		complexity: normalizeComplexityStats(
			record.complexity,
			fallback.complexity,
		),
	};
}

function normalizeProjectSkillEvidence(
	value: JsonRecord,
): ProjectSkillEvidence {
	return {
		skill: asString(value.skill),
		evidence: asString(value.evidence),
	};
}

function normalizeProjectCard(value: JsonRecord): ProjectCard {
	return {
		name: asString(value.name),
		what_it_says_about_you: asString(value.what_it_says_about_you),
		skills: normalizeArray(value.skills, normalizeProjectSkillEvidence),
		standout: asString(value.standout),
		next_level: asStringArray(value.next_level),
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
		resume_markdown: asString(record.resume_markdown, fallback.resume_markdown),
		developer_dna: normalizeDeveloperDNA(
			record.developer_dna,
			fallback.developer_dna,
		),
		hidden_strengths: normalizeArray(
			record.hidden_strengths,
			normalizeHiddenStrength,
		),
		growth_areas: normalizeArray(record.growth_areas, normalizeGrowthArea),
		talking_points: normalizeArray(
			record.talking_points,
			normalizeTalkingPoint,
		),
		impact: normalizeImpact(record.impact, fallback.impact),
		projects: normalizeArray(record.projects, normalizeProjectCard),
	};
}
