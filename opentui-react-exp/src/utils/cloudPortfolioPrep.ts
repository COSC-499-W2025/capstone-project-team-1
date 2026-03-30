import { api } from "../api/endpoints";
import type {
	AnalysisResponse,
	AnswersRequest,
	RepoAnalysisResult,
} from "../api/types";

const NO_MATCHING_COMMITS_FRAGMENT = "No commits found for the specified user";

const CLOUD_PORTFOLIO_DEFAULT_ANSWERS = {
	artifacts_focus: "code files, documentation, configs",
	end_goal: "Generate portfolio and resume",
	repository_priority: "prioritize git repository analysis",
	file_patterns_include: "",
	file_patterns_exclude: "",
} satisfies Omit<AnswersRequest["answers"], "email">;

export interface PrepareAndGenerateCloudPortfolioInput {
	portfolioId: string;
	zipId: number;
	email: string;
	selectedRepoIds: string[];
}

export interface CloudPortfolioPrepResult {
	path: string;
	warnings: string[];
	analysisWarnings: string[];
	prepared: boolean;
}

interface PrepareAndGenerateCloudPortfolioOptions {
	onStatusChange?: (message: string) => void;
	onPrepared?: () => void;
}

function hasNoMatchingCommitError(repo: RepoAnalysisResult): boolean {
	return repo.error?.includes(NO_MATCHING_COMMITS_FRAGMENT) ?? false;
}

function hasUserLevelData(repo: RepoAnalysisResult): boolean {
	return [
		repo.user_contribution_pct,
		repo.user_total_commits,
		repo.user_commit_frequency,
		repo.user_first_commit,
		repo.user_last_commit,
	].some((value) => value !== null && value !== undefined);
}

function detectAnalysisWarnings(
	analysis: AnalysisResponse,
	email: string,
): string[] {
	if (analysis.repos_analyzed.length === 0) {
		return [];
	}

	const allReposMissingUserData = analysis.repos_analyzed.every(
		(repo) =>
			!hasUserLevelData(repo) &&
			(repo.error === null || hasNoMatchingCommitError(repo)),
	);

	const allReposReportNoMatchingCommits = analysis.repos_analyzed.every(
		hasNoMatchingCommitError,
	);

	if (!allReposMissingUserData && !allReposReportNoMatchingCommits) {
		return [];
	}

	return [
		`No commits matched ${email}; portfolio will use mostly repo-level data and may have an empty heatmap.`,
	];
}

export async function prepareAndGenerateCloudPortfolio(
	input: PrepareAndGenerateCloudPortfolioInput,
	options: PrepareAndGenerateCloudPortfolioOptions = {},
): Promise<CloudPortfolioPrepResult> {
	const email = input.email.trim().toLowerCase();
	const answers: AnswersRequest["answers"] = {
		email,
		...CLOUD_PORTFOLIO_DEFAULT_ANSWERS,
	};

	options.onStatusChange?.("Saving portfolio settings...");
	await api.updateConsent("cloud");
	await api.submitAnswers(answers);

	options.onStatusChange?.("Analyzing selected repositories...");
	const analysis = await api.runAnalysis(input.zipId, input.selectedRepoIds);
	options.onPrepared?.();

	options.onStatusChange?.("Generating portfolio HTML...");
	const generated = await api.generatePortfolio(input.portfolioId);

	return {
		path: generated.path,
		warnings: generated.warnings,
		analysisWarnings: detectAnalysisWarnings(analysis, email),
		prepared: true,
	};
}

export const cloudPortfolioPrep = {
	NO_MATCHING_COMMITS_FRAGMENT,
	detectAnalysisWarnings,
};
