import {
	createContext,
	useCallback,
	useContext,
	useMemo,
	useState,
	type ReactNode,
} from "react";
import type {
	PipelineContributorIdentity,
	PipelineJobStatus,
	PipelineRepoCandidate,
	PipelineStage,
	PipelineTelemetry,
	ResumeV3Output,
} from "../api/types";

export interface AppState {
	zipPath: string;
	intakeId: string | null;
	detectedRepos: PipelineRepoCandidate[];
	selectedRepoIds: string[];
	contributors: PipelineContributorIdentity[];
	selectedEmail: string | null;
	pipelineJobId: string | null;
	pipelineStatus: PipelineJobStatus | "idle";
	pipelineStage: PipelineStage | null;
	pipelineTelemetry: PipelineTelemetry | null;
	pipelineMessages: string[];
	resumeV3Draft: ResumeV3Output | null;
	resumeV3Output: ResumeV3Output | null;
	pipelineNotice: string | null;
}

interface AppContextValue {
	state: AppState;
	setZipPath: (value: string) => void;
	setIntakeId: (value: string | null) => void;
	setDetectedRepos: (value: PipelineRepoCandidate[]) => void;
	setSelectedRepoIds: (value: string[]) => void;
	setContributors: (value: PipelineContributorIdentity[]) => void;
	setSelectedEmail: (value: string | null) => void;
	setPipelineJobId: (value: string | null) => void;
	setPipelineStatus: (value: PipelineJobStatus | "idle") => void;
	setPipelineStage: (value: PipelineStage | null) => void;
	setPipelineTelemetry: (value: PipelineTelemetry | null) => void;
	setPipelineMessages: (value: string[]) => void;
	setResumeV3Draft: (value: ResumeV3Output | null) => void;
	setResumeV3Output: (value: ResumeV3Output | null) => void;
	setPipelineNotice: (value: string | null) => void;
	resetRunState: () => void;
	reset: () => void;
}

const initialState: AppState = {
	zipPath: "",
	intakeId: null,
	detectedRepos: [],
	selectedRepoIds: [],
	contributors: [],
	selectedEmail: null,
	pipelineJobId: null,
	pipelineStatus: "idle",
	pipelineStage: null,
	pipelineTelemetry: null,
	pipelineMessages: [],
	resumeV3Draft: null,
	resumeV3Output: null,
	pipelineNotice: null,
};

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
	const [state, setState] = useState<AppState>(initialState);

	const setZipPath = useCallback((value: string) => {
		setState((prev) => ({ ...prev, zipPath: value }));
	}, []);
	const setIntakeId = useCallback((value: string | null) => {
		setState((prev) => ({ ...prev, intakeId: value }));
	}, []);
	const setDetectedRepos = useCallback((value: PipelineRepoCandidate[]) => {
		setState((prev) => ({ ...prev, detectedRepos: value }));
	}, []);
	const setSelectedRepoIds = useCallback((value: string[]) => {
		setState((prev) => ({ ...prev, selectedRepoIds: value }));
	}, []);
	const setContributors = useCallback((value: PipelineContributorIdentity[]) => {
		setState((prev) => ({ ...prev, contributors: value }));
	}, []);
	const setSelectedEmail = useCallback((value: string | null) => {
		setState((prev) => ({ ...prev, selectedEmail: value }));
	}, []);
	const setPipelineJobId = useCallback((value: string | null) => {
		setState((prev) => ({ ...prev, pipelineJobId: value }));
	}, []);
	const setPipelineStatus = useCallback((value: PipelineJobStatus | "idle") => {
		setState((prev) => ({ ...prev, pipelineStatus: value }));
	}, []);
	const setPipelineStage = useCallback((value: PipelineStage | null) => {
		setState((prev) => ({ ...prev, pipelineStage: value }));
	}, []);
	const setPipelineTelemetry = useCallback((value: PipelineTelemetry | null) => {
		setState((prev) => ({ ...prev, pipelineTelemetry: value }));
	}, []);
	const setPipelineMessages = useCallback((value: string[]) => {
		setState((prev) => ({ ...prev, pipelineMessages: value }));
	}, []);
	const setResumeV3Draft = useCallback((value: ResumeV3Output | null) => {
		setState((prev) => ({ ...prev, resumeV3Draft: value }));
	}, []);
	const setResumeV3Output = useCallback((value: ResumeV3Output | null) => {
		setState((prev) => ({ ...prev, resumeV3Output: value }));
	}, []);
	const setPipelineNotice = useCallback((value: string | null) => {
		setState((prev) => ({ ...prev, pipelineNotice: value }));
	}, []);

	const resetRunState = useCallback(
		() =>
		setState((prev) => ({
			...prev,
			pipelineJobId: null,
			pipelineStatus: "idle",
			pipelineStage: null,
			pipelineTelemetry: null,
			pipelineMessages: [],
			resumeV3Draft: null,
			resumeV3Output: null,
		})),
		[],
	);

	const reset = useCallback(() => setState(initialState), []);

	const value = useMemo(
		() => ({
			state,
			setZipPath,
			setIntakeId,
			setDetectedRepos,
			setSelectedRepoIds,
			setContributors,
			setSelectedEmail,
			setPipelineJobId,
			setPipelineStatus,
			setPipelineStage,
			setPipelineTelemetry,
			setPipelineMessages,
			setResumeV3Draft,
			setResumeV3Output,
			setPipelineNotice,
			resetRunState,
			reset,
		}),
		[
			reset,
			resetRunState,
			setContributors,
			setDetectedRepos,
			setIntakeId,
			setPipelineJobId,
			setPipelineMessages,
			setPipelineNotice,
			setPipelineStage,
			setPipelineStatus,
			setPipelineTelemetry,
			setResumeV3Draft,
			setResumeV3Output,
			setSelectedEmail,
			setSelectedRepoIds,
			setZipPath,
			state,
		],
	);

	return (
		<AppContext.Provider value={value}>
			{children}
		</AppContext.Provider>
	);
}

export function useAppState() {
	const context = useContext(AppContext);
	if (!context) {
		throw new Error("useAppState must be used within an AppProvider");
	}
	return context;
}
