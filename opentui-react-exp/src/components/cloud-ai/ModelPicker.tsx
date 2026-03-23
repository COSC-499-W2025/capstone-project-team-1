/**
 * Model definitions for the cloud AI flow.
 *
 * The UI is rendered inline by CopilotLogin (post-auth model list)
 * and CloudAuth (already-authenticated model list).
 */

export interface ModelOption {
	id: string;
	name: string;
	provider: string;
	description: string;
}

export const CLOUD_MODELS: ModelOption[] = [
	{
		id: "claude-haiku-4-5",
		name: "Haiku 4.5",
		provider: "Anthropic",
		description: "Fast & lightweight",
	},
	{
		id: "claude-sonnet-4-6",
		name: "Sonnet 4.6",
		provider: "Anthropic",
		description: "Best code analysis",
	},
	{
		id: "gpt-5.4",
		name: "GPT 5.4",
		provider: "OpenAI",
		description: "Strong all-rounder",
	},
	{
		id: "gemini-3.1-pro",
		name: "Gemini 3.1 Pro",
		provider: "Google",
		description: "Multimodal capable",
	},
];

export const DEFAULT_MODEL_ID = "claude-haiku-4-5";
