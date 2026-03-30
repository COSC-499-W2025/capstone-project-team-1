import { afterEach, expect, test } from "bun:test";
import { api } from "../api/endpoints";
import type { AnalysisResponse } from "../api/types";
import { prepareAndGenerateCloudPortfolio } from "./cloudPortfolioPrep";

const originalUpdateConsent = api.updateConsent;
const originalSubmitAnswers = api.submitAnswers;
const originalRunAnalysis = api.runAnalysis;
const originalGeneratePortfolio = api.generatePortfolio;

const baseAnalysisResponse: AnalysisResponse = {
	zip_id: 24,
	extraction_path: "/tmp/extracted/24",
	repos_found: 2,
	repos_analyzed: [
		{
			project_name: "apps/web",
			project_path: "/tmp/extracted/24/apps/web",
			frameworks: ["React"],
			languages: ["TypeScript"],
			skills_count: 4,
			insights_count: 3,
			user_contribution_pct: 82,
			user_total_commits: 18,
			user_commit_frequency: 2.5,
			user_first_commit: "2025-01-10T00:00:00",
			user_last_commit: "2025-03-10T00:00:00",
			error: null,
		},
	],
	rankings: [],
	summaries: [],
	consent_level: "cloud",
	user_email: "dev@example.com",
};

afterEach(() => {
	api.updateConsent = originalUpdateConsent;
	api.submitAnswers = originalSubmitAnswers;
	api.runAnalysis = originalRunAnalysis;
	api.generatePortfolio = originalGeneratePortfolio;
});

test("prepareAndGenerateCloudPortfolio syncs consent, answers, analysis, and generation in order", async () => {
	const calls: string[] = [];

	api.updateConsent = async (consentLevel) => {
		calls.push(`consent:${consentLevel}`);
		return { consent_level: consentLevel, accepted_at: "2026-03-30T00:00:00Z" };
	};

	api.submitAnswers = async (answers) => {
		calls.push("answers");
		expect(answers).toEqual({
			email: "dev@example.com",
			artifacts_focus: "code files, documentation, configs",
			end_goal: "Generate portfolio and resume",
			repository_priority: "prioritize git repository analysis",
			file_patterns_include: "",
			file_patterns_exclude: "",
		});
		return [];
	};

	api.runAnalysis = async (zipId, directories) => {
		calls.push("analysis");
		expect(zipId).toBe(24);
		expect(directories).toEqual(["apps/web", "packages/core"]);
		return baseAnalysisResponse;
	};

	api.generatePortfolio = async (portfolioId) => {
		calls.push("generate");
		expect(portfolioId).toBe("portfolio-24");
		return {
			success: true,
			artifact: "portfolio",
			path: "/tmp/portfolio.html",
			generated_at: "2026-03-30T00:00:00Z",
			warnings: ["Some selected projects do not have summaries yet."],
		};
	};

	const statusMessages: string[] = [];
	const result = await prepareAndGenerateCloudPortfolio(
		{
			portfolioId: "portfolio-24",
			zipId: 24,
			email: "Dev@Example.com",
			selectedRepoIds: ["apps/web", "packages/core"],
		},
		{
			onStatusChange: (message) => {
				statusMessages.push(message);
			},
		},
	);

	expect(calls).toEqual(["consent:cloud", "answers", "analysis", "generate"]);
	expect(statusMessages).toEqual([
		"Saving portfolio settings...",
		"Analyzing selected repositories...",
		"Generating portfolio HTML...",
	]);
	expect(result).toEqual({
		path: "/tmp/portfolio.html",
		warnings: ["Some selected projects do not have summaries yet."],
		analysisWarnings: [],
		prepared: true,
	});
});

test("prepareAndGenerateCloudPortfolio treats missing user commit matches as a warning, not a failure", async () => {
	api.updateConsent = async (consentLevel) => ({
		consent_level: consentLevel,
		accepted_at: "2026-03-30T00:00:00Z",
	});
	api.submitAnswers = async () => [];
	api.runAnalysis = async () => ({
		...baseAnalysisResponse,
		repos_analyzed: [
			{
				project_name: "apps/web",
				project_path: "/tmp/extracted/24/apps/web",
				frameworks: ["React"],
				languages: ["TypeScript"],
				skills_count: 3,
				insights_count: 2,
				user_contribution_pct: null,
				user_total_commits: null,
				user_commit_frequency: null,
				user_first_commit: null,
				user_last_commit: null,
				error: null,
			},
			{
				project_name: "packages/core",
				project_path: "/tmp/extracted/24/packages/core",
				frameworks: ["Bun"],
				languages: ["TypeScript"],
				skills_count: 2,
				insights_count: 1,
				user_contribution_pct: null,
				user_total_commits: null,
				user_commit_frequency: null,
				user_first_commit: null,
				user_last_commit: null,
				error:
					"No commits found for the specified user in this collaborative repo",
			},
		],
	});
	api.generatePortfolio = async () => ({
		success: true,
		artifact: "portfolio",
		path: "/tmp/portfolio.html",
		generated_at: "2026-03-30T00:00:00Z",
		warnings: [],
	});

	const result = await prepareAndGenerateCloudPortfolio({
		portfolioId: "portfolio-24",
		zipId: 24,
		email: "dev@example.com",
		selectedRepoIds: ["apps/web", "packages/core"],
	});

	expect(result.prepared).toBe(true);
	expect(result.analysisWarnings).toEqual([
		"No commits matched dev@example.com; portfolio will use mostly repo-level data and may have an empty heatmap.",
	]);
	expect(result.warnings).toEqual([]);
});
