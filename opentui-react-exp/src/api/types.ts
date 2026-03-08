export type ConsentLevel =
	| "none"
	| "local"
	| "local-llm"
	| "cloud"
	| "full"
	| "no_llm";

export interface ConsentResponse {
	consent_level: ConsentLevel;
	accepted_at: string | null;
}

export interface Question {
	id: number;
	key: string | null;
	question_text: string;
	order: number;
	required: boolean;
	answer_type: string;
}

export interface UserAnswer {
	id: number;
	question_id: number;
	answer_text: string;
	answered_at: string;
}

export interface AnswersRequest {
	answers: Record<string, string>;
}

export interface UploadResponse {
	zip_id: number;
	filename: string;
	portfolio_id: string;
}

export interface DirectoriesResponse {
	zip_id: number;
	filename: string;
	directories: string[];
	cleanedfilespath: string[];
}

export interface ProjectTimelineItem {
	id: number;
	project_name: string;
	first_commit: string;
	last_commit: string;
	duration_days: number;
	was_active: boolean;
}

export interface SkillChronologyItem {
	date: string | null;
	skill: string;
	project: string;
	proficiency: number | null;
	category: string | null;
}

export interface ResumeItem {
	id: number;
	title: string;
	content: string;
	category: string | null;
	project_name: string | null;
	created_at: string;
}

export interface Summary {
	id: number;
	repo_path: string;
	user_email: string;
	summary_text: string;
	generated_at: string;
}

export interface DeleteResponse {
	success: boolean;
	message: string;
	deleted_id: number;
}

export interface RepoAnalysisResult {
	project_name: string;
	project_path: string;
	frameworks: string[] | null;
	languages: string[] | null;
	skills_count: number;
	insights_count: number;
	user_contribution_pct: number | null;
	user_total_commits: number | null;
	user_commit_frequency: number | null;
	user_first_commit: string | null;
	user_last_commit: string | null;
	error: string | null;
}

export interface RankingResult {
	name: string;
	score: number;
	total_commits: number;
	user_commits: number;
}

export interface SummaryResult {
	project_name: string;
	summary: string;
}

export interface AnalysisResponse {
	zip_id: number;
	extraction_path: string;
	repos_found: number;
	repos_analyzed: RepoAnalysisResult[];
	rankings: RankingResult[];
	summaries: SummaryResult[];
	consent_level: ConsentLevel;
	user_email: string;
}

export type PipelineJobStatus =
	| "queued"
	| "running"
	| "draft_ready"
	| "polishing"
	| "complete"
	| "error"
	| "cancelled"
	| "failed_resource_guard";

export type PipelineStage =
	| "ANALYZE"
	| "FACTS"
	| "DRAFT"
	| "POLISH";

export interface PipelineRepoCandidate {
	id: string;
	name: string;
	rel_path: string;
}

export interface PipelineIntakeResponse {
	intake_id: string;
	zip_path: string;
	repos: PipelineRepoCandidate[];
}

export interface PipelineContributorsRequest {
	repo_ids: string[];
}

export interface PipelineContributorIdentity {
	email: string;
	name: string | null;
	repo_count: number;
	commit_count: number;
	candidate_username: string;
}

export interface PipelineContributorsResponse {
	contributors: PipelineContributorIdentity[];
}

export interface PipelineStartRequest {
	intake_id?: string | null;
	repo_ids: string[];
	user_email: string;
	stage1_model: string;
	stage2_model: string;
	stage3_model: string;
}

export interface PipelineStartResponse {
	job_id: string;
	status: PipelineJobStatus;
}

export interface ResumeV3ProjectPeriod {
	first_commit: string | null;
	last_commit: string | null;
}

export interface ResumeV3Project {
	name: string;
	type: string;
	primary_language: string | null;
	frameworks: string[];
	contribution_pct: number | null;
	commit_breakdown: Record<string, number>;
	period: ResumeV3ProjectPeriod;
	description?: string;
	bullets?: string[];
	bullet_fact_ids?: string[][];
	narrative?: string;
}

export interface ResumeV3Metadata {
	model_used: string | null;
	models_used: string[];
	stage: string;
	generation_time_seconds: number;
	errors: string[];
	quality_metrics: Record<string, unknown>;
}

export interface ResumeV3Portfolio {
	total_projects: number;
	total_commits: number;
	languages_used: string[];
	frameworks_used: string[];
	project_types: Record<string, number>;
	top_skills: string[];
}

export interface ResumeV3Output {
	professional_summary: string;
	skills_section: string;
	developer_profile: string;
	projects: ResumeV3Project[];
	metadata: ResumeV3Metadata;
	portfolio?: ResumeV3Portfolio;
}

export interface PipelineTelemetry {
	stage: PipelineStage;
	active_model: string | null;
	repos_total: number;
	repos_done: number;
	current_repo: string | null;
	facts_total: number;
	draft_projects: number;
	polished_projects: number;
	elapsed_seconds: number;
	model_check_seconds: number;
	selected_repos: string[];
}

export interface PipelineStatusResponse {
	status: PipelineJobStatus;
	stage: PipelineStage;
	messages: string[];
	telemetry: PipelineTelemetry;
	draft: ResumeV3Output | null;
	output: ResumeV3Output | null;
	error: string | null;
}

export interface PipelinePolishRequest {
	general_notes: string;
	tone: string;
	additions: string[];
	removals: string[];
}

export interface PipelinePolishResponse {
	ok: boolean;
	status: PipelineJobStatus;
}

export interface PipelineCancelResponse {
	ok: boolean;
	status: PipelineJobStatus;
}
