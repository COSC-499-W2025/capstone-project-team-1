// Screen types
export type Screen = 
  | "landing"
  | "consent"
  | "file-upload"
  | "project-list"
  | "analysis"
  | "resume-preview";

// Project data types
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

// Resume types
export interface Skill {
  name: string;
  level: "beginner" | "intermediate" | "advanced" | "expert";
  projects: string[]; // project IDs that use this skill
}

export interface ResumeData {
  skills: Skill[];
  projects: Project[];
  summary: string;
}

// Bottom bar action
export interface KeyAction {
  key: string;
  label: string;
}

// Analysis step
export interface AnalysisStep {
  id: string;
  label: string;
  status: "pending" | "in-progress" | "completed";
}

// Theme colors
export const theme = {
  // Primary: Gold
  gold: "#FFD700",
  goldDark: "#B8860B",
  goldDim: "#8B7500",
  
  // Secondary: Cyan
  cyan: "#00CED1",
  cyanDark: "#008B8B",
  cyanDim: "#006666",
  
  // Backgrounds
  bgDark: "#000000",
  bgMedium: "#2a2a2a",
  bgLight: "#3a3a3a",
  
  // Text
  textPrimary: "#FFFFFF",
  textSecondary: "#CCCCCC",
  textDim: "#666666",
  
  // Accents
  success: "#32CD32",
  error: "#FF4444",
  warning: "#FFA500",
} as const;
