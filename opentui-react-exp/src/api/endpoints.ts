import { ApiClient } from "./client";
import type {
	AnalysisResponse,
	AnswersRequest,
	Award,
	AwardCreateRequest,
	ConsentLevel,
	ConsentResponse,
	DeleteResponse,
	DirectoriesResponse,
	Education,
	EducationCreateRequest,
	ExtractLocalResponse,
	LocalLlmSetupResponse,
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
	uploadZip: (file: Blob, portfolioId?: string, filename = "upload.zip"): Promise<UploadResponse> => {
		const path = portfolioId
			? `/zip/upload?portfolio_id=${encodeURIComponent(portfolioId)}`
			: "/zip/upload";
		return client.uploadFile(path, file, "file", undefined, filename);
	},
	listDirectories: (zipId: number): Promise<DirectoriesResponse> =>
		client.get(`/zip/${zipId}/directories`),
	runAnalysis: (
		zipId: number,
		directories?: string[],
	): Promise<AnalysisResponse> =>
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
		client.post("/local-llm/context", { zip_path: zipPath }),
	getPipelineContributors: (
		request: PipelineContributorsRequest,
	): Promise<PipelineContributorsResponse> =>
		client.post("/local-llm/context/contributors", request),
	getLocalLlmSetup: (): Promise<LocalLlmSetupResponse> =>
		client.get("/local-llm/setup"),
	startPipeline: (
		request: PipelineStartRequest,
	): Promise<PipelineStartResponse> =>
		client.post("/local-llm/generation/start", request),
	getPipelineStatus: (): Promise<PipelineStatusResponse> =>
		client.get("/local-llm/generation/status"),
	polishPipeline: (
		request: PipelinePolishRequest,
	): Promise<PipelinePolishResponse> =>
		client.post("/local-llm/generation/polish", request),
	cancelPipeline: (): Promise<PipelineCancelResponse> =>
		client.post("/local-llm/generation/cancel"),

	extractLocal: (zipId: number): Promise<ExtractLocalResponse> =>
		client.post("/zip/extract-local", { zip_id: zipId }),

	// Education endpoints
	listEducation: (portfolioId: string): Promise<Education[]> =>
		client.get(withQuery("/education", { portfolio_id: portfolioId })),
	getEducation: (id: number, portfolioId?: string): Promise<Education> =>
		client.get(withQuery(`/education/${id}`, { portfolio_id: portfolioId })),
	createEducation: (portfolioId: string, data: EducationCreateRequest): Promise<Education> =>
		client.post(withQuery("/education", { portfolio_id: portfolioId }), data),
	updateEducation: (id: number, portfolioId: string, data: EducationCreateRequest): Promise<Education> =>
		client.put(withQuery(`/education/${id}`, { portfolio_id: portfolioId }), data),
	deleteEducation: (id: number, portfolioId: string): Promise<DeleteResponse> =>
		client.delete(withQuery(`/education/${id}`, { portfolio_id: portfolioId })),

	// Award endpoints
	listAwards: (portfolioId: string): Promise<Award[]> =>
		client.get(withQuery("/awards", { portfolio_id: portfolioId })),
	getAward: (id: number, portfolioId?: string): Promise<Award> =>
		client.get(withQuery(`/awards/${id}`, { portfolio_id: portfolioId })),
	createAward: (portfolioId: string, data: AwardCreateRequest): Promise<Award> =>
		client.post(withQuery("/awards", { portfolio_id: portfolioId }), data),
	updateAward: (id: number, portfolioId: string, data: AwardCreateRequest): Promise<Award> =>
		client.put(withQuery(`/awards/${id}`, { portfolio_id: portfolioId }), data),
	deleteAward: (id: number, portfolioId: string): Promise<DeleteResponse> =>
		client.delete(withQuery(`/awards/${id}`, { portfolio_id: portfolioId })),
};
