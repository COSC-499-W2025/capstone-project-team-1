import { createContext, useContext, useState, type ReactNode } from "react";

export type ConsentLevel = "full" | "no_llm" | "none";
export type AnalysisStatus = "idle" | "running" | "complete" | "error";

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

export interface AnalysisResponse {
	zip_id: number;
	extraction_path: string;
	repos_found: number;
	repos_analyzed: unknown[];
	rankings: unknown[];
	summaries: unknown[];
	consent_level: string;
	user_email: string;
}

export interface AppState {
	consentLevel: ConsentLevel;
	userEmail: string | null;
	zipId: number | null;
	directories: string[];
	selectedDirectories: string[];
	analysisResult: AnalysisResponse | null;
	analysisStatus: AnalysisStatus;
	resumeItems: ResumeItem[];
	summaries: Summary[];
}

interface AppContextValue {
	state: AppState;
	setConsentLevel: (value: ConsentLevel) => void;
	setUserEmail: (value: string | null) => void;
	setZipId: (value: number | null) => void;
	setDirectories: (value: string[]) => void;
	setSelectedDirectories: (value: string[]) => void;
	setAnalysisResult: (value: AnalysisResponse | null) => void;
	setAnalysisStatus: (value: AnalysisStatus) => void;
	setResumeItems: (value: ResumeItem[]) => void;
	setSummaries: (value: Summary[]) => void;
	reset: () => void;
}

const initialState: AppState = {
	consentLevel: "none",
	userEmail: null,
	zipId: null,
	directories: [],
	selectedDirectories: [],
	analysisResult: null,
	analysisStatus: "idle",
	resumeItems: [],
	summaries: [],
};

const AppContext = createContext<AppContextValue | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
	const [state, setState] = useState<AppState>(initialState);

	const setConsentLevel = (value: ConsentLevel) => setState((prev) => ({ ...prev, consentLevel: value }));
	const setUserEmail = (value: string | null) => setState((prev) => ({ ...prev, userEmail: value }));
	const setZipId = (value: number | null) => setState((prev) => ({ ...prev, zipId: value }));
	const setDirectories = (value: string[]) => setState((prev) => ({ ...prev, directories: value }));
	const setSelectedDirectories = (value: string[]) => setState((prev) => ({ ...prev, selectedDirectories: value }));
	const setAnalysisResult = (value: AnalysisResponse | null) => setState((prev) => ({ ...prev, analysisResult: value }));
	const setAnalysisStatus = (value: AnalysisStatus) => setState((prev) => ({ ...prev, analysisStatus: value }));
	const setResumeItems = (value: ResumeItem[]) => setState((prev) => ({ ...prev, resumeItems: value }));
	const setSummaries = (value: Summary[]) => setState((prev) => ({ ...prev, summaries: value }));
	const reset = () => setState(initialState);

	return (
		<AppContext.Provider
			value={{
				state,
				setConsentLevel,
				setUserEmail,
				setZipId,
				setDirectories,
				setSelectedDirectories,
				setAnalysisResult,
				setAnalysisStatus,
				setResumeItems,
				setSummaries,
				reset,
			}}
		>
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
