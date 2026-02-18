import { ApiClient } from "./client";
import type {
	AnalysisResponse,
	AnswersRequest,
	ConsentLevel,
	ConsentResponse,
	DeleteResponse,
	DirectoriesResponse,
	PipelineCancelResponse,
	PipelineContributorsRequest,
	PipelineContributorsResponse,
	PipelineIntakeResponse,
	PipelinePolishRequest,
	PipelinePolishResponse,
	PipelineStartRequest,
	PipelineStartResponse,
	PipelineStatusResponse,
	ProjectTimelineItem,
	Question,
	ResumeItem,
	SkillChronologyItem,
	Summary,
	UploadResponse,
	UserAnswer,
} from "./types";

const client = new ApiClient();

const withQuery = (
	path: string,
	params: Record<string, string | number | boolean | undefined>,
): string => {
	const searchParams = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) {
			searchParams.set(key, String(value));
		}
	}
	const query = searchParams.toString();
	return query ? `${path}?${query}` : path;
};

export const api = {
	getConsent: (): Promise<ConsentResponse> => client.get("/consent"),
	updateConsent: (consent_level: ConsentLevel): Promise<ConsentResponse> =>
		client.put("/consent", { consent_level }),
	getQuestions: (): Promise<Question[]> => client.get("/questions"),
	submitAnswers: (answers: AnswersRequest["answers"]): Promise<UserAnswer[]> =>
		client.post("/answers", { answers }),
	uploadZip: (file: Blob, portfolioId?: string): Promise<UploadResponse> => {
		const path = portfolioId
			? `/zip/upload?portfolio_id=${encodeURIComponent(portfolioId)}`
			: "/zip/upload";
		return client.uploadFile(path, file);
	},
	listDirectories: (zipId: number): Promise<DirectoriesResponse> =>
		client.get(`/zip/${zipId}/directories`),
	runAnalysis: (zipId: number, directories?: string[]): Promise<AnalysisResponse> =>
		client.post(`/analyze/${zipId}`, directories ? { directories } : undefined),
	getResume: (projectId?: number): Promise<ResumeItem[]> =>
		client.get(withQuery("/resume", { project_id: projectId })),
	getSummaries: (userEmail: string): Promise<Summary[]> =>
		client.get(withQuery("/summaries", { user_email: userEmail })),
	getSkillsChronology: (): Promise<SkillChronologyItem[]> =>
		client.get("/skills/chronology"),
	getProjectsTimeline: (options?: {
		startDate?: string;
		endDate?: string;
		activeOnly?: boolean;
	}): Promise<ProjectTimelineItem[]> =>
		client.get(
			withQuery("/projects/timeline", {
				start_date: options?.startDate,
				end_date: options?.endDate,
				active_only: options?.activeOnly,
			}),
		),
	deleteProject: (projectId: number): Promise<DeleteResponse> =>
		client.delete(`/projects/${projectId}`),
	createPipelineIntake: (zipPath: string): Promise<PipelineIntakeResponse> =>
		client.post("/resume/pipelines/intakes", { zip_path: zipPath }),
	getPipelineContributors: (
		intakeId: string,
		request: PipelineContributorsRequest,
	): Promise<PipelineContributorsResponse> =>
		client.post(`/resume/pipelines/intakes/${intakeId}/contributors`, request),
	startPipeline: (request: PipelineStartRequest): Promise<PipelineStartResponse> =>
		client.post("/resume/pipelines", request),
	getPipelineStatus: (jobId: string): Promise<PipelineStatusResponse> =>
		client.get(`/resume/pipelines/${jobId}`),
	polishPipeline: (
		jobId: string,
		request: PipelinePolishRequest,
	): Promise<PipelinePolishResponse> =>
		client.post(`/resume/pipelines/${jobId}/polish`, request),
	cancelPipeline: (jobId: string): Promise<PipelineCancelResponse> =>
		client.post(`/resume/pipelines/${jobId}/cancel`),
};
