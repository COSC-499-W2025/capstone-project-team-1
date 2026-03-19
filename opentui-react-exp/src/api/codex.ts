import { ApiClient } from "./client";

const codexClient = new ApiClient({
	baseUrl: process.env.CODEX_SERVER_URL ?? "http://127.0.0.1:8100",
	timeoutMs: 120_000, // generation can take a while
});

export interface CodexAccountResponse {
	account: {
		type: string;
		email: string;
		planType: string;
	} | null;
	requiresOpenaiAuth: boolean;
}

export interface CodexGenerateResponse {
	markdown: string;
	status: string;
	error: string | null;
}

export interface CodexStatusResponse {
	state: "stopped" | "starting" | "running" | "error";
	error: string | null;
}

export const codexApi = {
	health: (): Promise<{ status: string }> => codexClient.get("/health"),

	status: (): Promise<CodexStatusResponse> =>
		codexClient.get("/codex/status"),

	account: (): Promise<CodexAccountResponse> =>
		codexClient.get("/codex/account"),

	login: (): Promise<unknown> => codexClient.post("/codex/account/login"),

	logout: (): Promise<unknown> => codexClient.post("/codex/account/logout"),

	generate: (zipPath: string): Promise<CodexGenerateResponse> =>
		codexClient.post("/codex/generate", { zip_path: zipPath }),
};
