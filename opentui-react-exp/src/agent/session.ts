/**
 * Pi Agent session management for resume generation.
 *
 * Creates an embedded Pi Agent session that explores extracted
 * code repositories and generates a structured resume.
 * Supports GitHub Copilot auth (device flow) for students.
 */
import {
	AuthStorage,
	type AgentSession,
	type AgentSessionEvent,
	createAgentSession,
	createBashTool,
	createReadOnlyTools,
	DefaultResourceLoader,
	ModelRegistry,
	SessionManager,
	SettingsManager,
} from "@mariozechner/pi-coding-agent";
import type { OAuthLoginCallbacks } from "@mariozechner/pi-ai";
import { RESUME_SYSTEM_PROMPT } from "./prompt";

// Shared auth storage instance — persists across the session
let _authStorage: AuthStorage | undefined;
function getAuthStorage(): AuthStorage {
	if (!_authStorage) {
		_authStorage = AuthStorage.create();
	}
	return _authStorage;
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
): Promise<{ session: AgentSession; dispose: () => void }> {
	const authStorage = getAuthStorage();
	const modelRegistry = new ModelRegistry(authStorage);

	// Find the best available model — prefer Copilot models
	const available = modelRegistry.getAvailable();
	if (available.length === 0) {
		throw new Error(
			"No LLM models available. Please log in with GitHub Copilot.",
		);
	}

	// Prefer a Copilot Claude model for best code analysis
	const model =
		available.find((m) => m.provider === "github-copilot" && m.id.includes("sonnet")) ??
		available.find((m) => m.provider === "github-copilot") ??
		available[0];

	// Custom resource loader with resume system prompt
	const loader = new DefaultResourceLoader({
		cwd,
		systemPromptOverride: () => RESUME_SYSTEM_PROMPT,
	});
	await loader.reload();

	const { session } = await createAgentSession({
		cwd,
		model,
		thinkingLevel: "off",
		tools: [...createReadOnlyTools(cwd), createBashTool(cwd)],
		resourceLoader: loader,
		sessionManager: SessionManager.inMemory(),
		settingsManager: SettingsManager.inMemory({
			compaction: { enabled: false },
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
export async function generateResume(
	extractedDir: string,
	onEvent: (event: ResumeEvent) => void,
): Promise<string> {
	const { session, dispose } = await createResumeSession(
		extractedDir,
		onEvent,
	);

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

	try {
		await session.prompt(
			"Explore all the code repositories in this directory and generate a professional resume based on what you find. Your final response must contain ONLY the resume markdown — start with '# Resume' and include nothing else before it. No preamble, no thinking, no narration.",
		);

		// Safety net: strip any filler text before the actual resume
		const resumeStart = fullText.indexOf("# Resume");
		return resumeStart >= 0 ? fullText.slice(resumeStart) : fullText;
	} finally {
		dispose();
	}
}
