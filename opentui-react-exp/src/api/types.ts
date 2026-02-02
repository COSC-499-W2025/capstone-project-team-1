export type ConsentLevel = "full" | "no_llm" | "none";
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
