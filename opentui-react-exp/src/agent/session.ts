/**
 * Pi Agent session management for resume generation.
 *
 * Creates an embedded Pi Agent session that explores extracted
 * code repositories and generates a structured resume.
 * Supports GitHub Copilot auth (device flow) for students.
 */
import type { OAuthLoginCallbacks } from "@mariozechner/pi-ai";
import {
	type AgentSession,
	type AgentSessionEvent,
	AuthStorage,
	createAgentSession,
	createExtensionRuntime,
	createReadOnlyTools,
	ModelRegistry,
	type ResourceLoader,
	SessionManager,
	SettingsManager,
} from "@mariozechner/pi-coding-agent";
import type { DeveloperProfile } from "../api/types";
import {
	buildFallbackProfile,
	normalizeDeveloperProfile,
} from "./profileNormalization";
import { RESUME_SYSTEM_PROMPT } from "./prompt";

// Shared auth storage instance — persists across the session
let _authStorage: AuthStorage | undefined;
function getAuthStorage(): AuthStorage {
	if (!_authStorage) {
		_authStorage = AuthStorage.create();
	}
	return _authStorage;
}

function createPromptOnlyResourceLoader(): ResourceLoader {
	return {
		getExtensions: () => ({
			extensions: [],
			errors: [],
			runtime: createExtensionRuntime(),
		}),
		getSkills: () => ({ skills: [], diagnostics: [] }),
		getPrompts: () => ({ prompts: [], diagnostics: [] }),
		getThemes: () => ({ themes: [], diagnostics: [] }),
		getAgentsFiles: () => ({ agentsFiles: [] }),
		getSystemPrompt: () => RESUME_SYSTEM_PROMPT,
		getAppendSystemPrompt: () => [],
		getPathMetadata: () => new Map(),
		extendResources: () => {},
		reload: async () => {},
	};
}

/** Result of checking available API keys / models. */
export interface ModelCheckResult {
	available: boolean;
	hasCopilot: boolean;
	models: Array<{ provider: string; id: string; name: string }>;
}

/** Events emitted during resume generation. */
export type ResumeEvent =
	| { type: "text"; delta: string }
	| { type: "thinking"; delta: string }
	| { type: "tool_start"; toolName: string; args: Record<string, unknown> }
	| { type: "tool_end"; toolName: string; isError: boolean }
	| { type: "agent_start" }
	| { type: "agent_end" }
	| { type: "error"; message: string };

/**
 * Check what LLM models are available based on configured API keys / OAuth.
 */
export async function checkAvailableModels(): Promise<ModelCheckResult> {
	const authStorage = getAuthStorage();
	const modelRegistry = new ModelRegistry(authStorage);
	const available = modelRegistry.getAvailable();

	return {
		available: available.length > 0,
		hasCopilot: authStorage.hasAuth("github-copilot"),
		models: available.map((m) => ({
			provider: m.provider,
			id: m.id,
			name: m.name ?? m.id,
		})),
	};
}

/**
 * Login to GitHub Copilot using the device flow.
 *
 * The callbacks let the TUI display the device code and URL to the user.
 * Credentials are automatically persisted via AuthStorage.
 */
export async function loginCopilot(callbacks: OAuthLoginCallbacks): Promise<void> {
	const authStorage = getAuthStorage();
	await authStorage.login("github-copilot", callbacks);
}

/**
 * Check if the user is already logged in to GitHub Copilot.
 */
export function isCopilotLoggedIn(): boolean {
	return getAuthStorage().hasAuth("github-copilot");
}

/** GitHub user profile fetched from the API. */
export interface GitHubUser {
	login: string;
	name: string | null;
	email: string | null;
}

/**
 * Fetch the authenticated user's GitHub profile.
 *
 * Uses the OAuth refresh token (ghu_* format) which has `read:user` scope.
 */
export async function fetchGitHubUser(): Promise<GitHubUser> {
	const authStorage = getAuthStorage();
	const cred = authStorage.get("github-copilot");
	if (!cred || cred.type !== "oauth") {
		throw new Error("Not logged in to GitHub Copilot");
	}

	const token = (cred as { refresh?: string }).refresh;
	if (!token) {
		throw new Error("No GitHub token available");
	}

	const resp = await fetch("https://api.github.com/user", {
		headers: {
			Authorization: `token ${token}`,
			Accept: "application/vnd.github+json",
		},
	});

	if (!resp.ok) {
		throw new Error(`GitHub API error: ${resp.status}`);
	}

	const data = (await resp.json()) as { login: string; name?: string; email?: string };
	let email = data.email ?? null;

	// Email is null when set to private — try /user/emails as fallback
	if (!email) {
		try {
			const emailResp = await fetch("https://api.github.com/user/emails", {
				headers: {
					Authorization: `token ${token}`,
					Accept: "application/vnd.github+json",
				},
			});
			if (emailResp.ok) {
				const emails = (await emailResp.json()) as Array<{
					email: string;
					primary: boolean;
					verified: boolean;
				}>;
				const primary = emails.find((e) => e.primary && e.verified);
				email = primary?.email ?? emails[0]?.email ?? null;
			}
		} catch {
			// Non-fatal — user can enter email manually
		}
	}

	return {
		login: data.login,
		name: data.name ?? null,
		email,
	};
}

/**
 * Create a Pi Agent session configured for resume generation.
 *
 * @param cwd - The directory containing extracted code
 * @param onEvent - Callback for streaming events
 * @returns The session and a cleanup function
 */
export async function createResumeSession(
	cwd: string,
	onEvent: (event: ResumeEvent) => void,
	modelId?: string,
): Promise<{ session: AgentSession; dispose: () => void }> {
	const authStorage = getAuthStorage();
	const modelRegistry = new ModelRegistry(authStorage);

	// Find the best available model — prefer user-selected, then Copilot models
	const available = modelRegistry.getAvailable();
	if (available.length === 0) {
		throw new Error(
			"No LLM models available. Please log in with GitHub Copilot.",
		);
	}

	const model =
		(modelId ? available.find((m) => m.id === modelId || m.id.includes(modelId)) : undefined) ??
		available.find((m) => m.provider === "github-copilot" && m.id.includes("sonnet")) ??
		available.find((m) => m.provider === "github-copilot") ??
		available[0];

	// Only provide the custom system prompt. Do not scan project resources.
	const loader = createPromptOnlyResourceLoader();
	await loader.reload();

	const { session } = await createAgentSession({
		cwd,
		model,
		thinkingLevel: "off",
		tools: createReadOnlyTools(cwd),
		resourceLoader: loader,
		sessionManager: SessionManager.inMemory(),
		settingsManager: SettingsManager.inMemory({
			retry: { enabled: true, maxRetries: 2 },
		}),
		authStorage,
		modelRegistry,
	});

	// Wire up event streaming
	session.subscribe((event: AgentSessionEvent) => {
		switch (event.type) {
			case "message_update":
				if (event.assistantMessageEvent.type === "text_delta") {
					onEvent({ type: "text", delta: event.assistantMessageEvent.delta });
				} else if (event.assistantMessageEvent.type === "thinking_delta") {
					onEvent({ type: "thinking", delta: event.assistantMessageEvent.delta });
				}
				break;
			case "tool_execution_start":
				onEvent({ type: "tool_start", toolName: event.toolName, args: event.args ?? {} });
				break;
			case "tool_execution_end":
				onEvent({ type: "tool_end", toolName: event.toolName, isError: event.isError });
				break;
			case "agent_start":
				onEvent({ type: "agent_start" });
				break;
			case "agent_end":
				onEvent({ type: "agent_end" });
				break;
		}
	});

	return {
		session,
		dispose: () => session.dispose(),
	};
}

/**
 * Run the full resume generation flow.
 *
 * Creates a session, sends the analysis prompt, and returns
 * the generated resume markdown. Events are streamed via onEvent.
 */
/** Git identity for attributing contributions in collaborative projects. */
export interface GitIdentity {
	login: string;
	name: string | null;
	email: string;
}

export interface GenerateResumeOptions {
	signal?: AbortSignal;
}

function createAbortError(): Error {
	const error = new Error("Resume generation was aborted.");
	error.name = "AbortError";
	return error;
}

function throwIfAborted(signal?: AbortSignal): void {
	if (signal?.aborted) {
		throw createAbortError();
	}
}

export async function generateResume(
	extractedDir: string,
	onEvent: (event: ResumeEvent) => void,
	modelId?: string,
	gitIdentity?: GitIdentity,
	options?: GenerateResumeOptions,
): Promise<DeveloperProfile> {
	const signal = options?.signal;
	throwIfAborted(signal);

	const { session, dispose } = await createResumeSession(
		extractedDir,
		onEvent,
		modelId,
	);
	let removeAbortListener: (() => void) | undefined;
	let abortPromise: Promise<void> | undefined;

	const abortSession = (): Promise<void> => {
		if (!abortPromise) {
			abortPromise = session.abort();
		}
		return abortPromise;
	};

	const generationAborted = signal
		? new Promise<never>((_, reject) => {
			if (signal.aborted) {
				void abortSession();
				reject(createAbortError());
				return;
			}

			const onAbort = () => {
				void abortSession();
				reject(createAbortError());
			};

			signal.addEventListener("abort", onAbort, { once: true });
			removeAbortListener = () => signal.removeEventListener("abort", onAbort);
		})
		: undefined;

	// Collect the full response text
	let fullText = "";
	session.subscribe((event: AgentSessionEvent) => {
		if (
			event.type === "message_update" &&
			event.assistantMessageEvent.type === "text_delta"
		) {
			fullText += event.assistantMessageEvent.delta;
		}
	});

	// Build the prompt with user identity context
	let identityContext = "";
	if (gitIdentity?.email) {
		identityContext = `\n\nIMPORTANT: The user's email is ${gitIdentity.email}. You are creating a resume for this user. Some projects may be collaborative — use git log and git blame to identify commits and code authored by this email. Focus only on their contributions, not the entire project.`;
	}

	try {
		const runGeneration = async (): Promise<DeveloperProfile> => {
			await session.prompt(
				`Explore all the code repositories in this directory and generate a comprehensive developer profile as structured JSON.${identityContext} Your final response must contain ONLY valid JSON — start with '{' and end with '}'. No preamble, no thinking, no narration, no markdown fences.`,
			);
			throwIfAborted(signal);

			// Extract JSON from the response — find the outermost { ... }
			const jsonStart = fullText.indexOf("{");
			const jsonEnd = fullText.lastIndexOf("}");
			if (jsonStart < 0 || jsonEnd < 0 || jsonEnd <= jsonStart) {
				throw new Error("LLM did not return valid JSON. Raw response saved as resume markdown.");
			}

			const jsonStr = fullText.slice(jsonStart, jsonEnd + 1);
			const parsed = JSON.parse(jsonStr) as unknown;
			return normalizeDeveloperProfile(parsed, fullText);
		};

		return generationAborted
			? await Promise.race([runGeneration(), generationAborted])
			: await runGeneration();
	} catch (err) {
		// Fallback: if JSON parsing fails, wrap the raw text as a markdown-only profile
		if (err instanceof SyntaxError) {
			return buildFallbackProfile(fullText);
		}
		throw err;
	} finally {
		removeAbortListener?.();
		if (abortPromise) {
			await abortPromise.catch(() => {});
		}
		dispose();
	}
}
