export type Screen =
	| "landing"
	| "consent"
	| "consent-policy"
	| "file-upload"
	| "project-list"
	| "identity"
	| "pipeline-launch"
	| "analysis"
	| "draft-pause"
	| "feedback"
	| "resume-preview";

export type AnalysisMode = "phase1" | "phase3";

export interface Project {
	id: string;
	name: string;
	language: string;
	description: string;
	technologies: string[];
	commits: number;
	files: number;
	lastUpdated: string;
}

export interface Skill {
	name: string;
	level: "beginner" | "intermediate" | "advanced" | "expert";
	projects: string[];
}

export interface ResumeData {
	skills: Skill[];
	projects: Project[];
	summary: string;
}

export interface KeyAction {
	key: string;
	label: string;
}

export interface AnalysisStep {
	id: string;
	label: string;
	status: "pending" | "in-progress" | "completed";
}

export const theme = {
	gold: "#FFD700",
	goldDark: "#B8860B",
	goldDim: "#8B7500",
	cyan: "#00CED1",
	cyanDark: "#008B8B",
	cyanDim: "#006666",
	bgDark: "#000000",
	bgMedium: "#2a2a2a",
	bgLight: "#3a3a3a",
	textPrimary: "#FFFFFF",
	textSecondary: "#CCCCCC",
	textDim: "#b2b0b0b4",
	success: "#32CD32",
	error: "#FF4444",
	warning: "#FFA500",
} as const;
