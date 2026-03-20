import { spawn } from "node:child_process";
import { platform } from "node:os";
import { useEffect, useRef, useState } from "react";
import { useKeyboard } from "@opentui/react";
import {
	checkAvailableModels,
	generateResume,
	isCopilotLoggedIn,
	loginCopilot,
	type ResumeEvent,
} from "../agent";
import { api } from "../api/endpoints";
import { theme } from "../types";
import { TopBar } from "./TopBar";

/** Open a URL in the user's default browser (macOS, Linux, Windows). */
function openInBrowser(url: string): void {
	const os = platform();
	const cmd =
		os === "darwin" ? "open"
		: os === "win32" ? "cmd"
		: "xdg-open";
	const args =
		os === "win32" ? ["/c", "start", "", url]
		: [url];
	spawn(cmd, args, { detached: true, stdio: "ignore" }).unref();
}

interface CloudGenerationProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Phase =
	| "checking-auth"
	| "copilot-login"
	| "extracting"
	| "generating"
	| "done"
	| "error";

const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export function CloudGeneration({
	zipPath,
	onComplete,
	onBack,
}: CloudGenerationProps) {
	const [phase, setPhase] = useState<Phase>("checking-auth");
	const [error, setError] = useState<string | null>(null);
	const [spinnerIndex, setSpinnerIndex] = useState(0);

	// Copilot login state
	const [deviceUrl, setDeviceUrl] = useState<string | null>(null);
	const [deviceCode, setDeviceCode] = useState<string | null>(null);
	const [loginProgress, setLoginProgress] = useState<string | null>(null);

	// Generation state
	const [currentTool, setCurrentTool] = useState<string | null>(null);
	const [toolsUsed, setToolsUsed] = useState<string[]>([]);
	const [streamedText, setStreamedText] = useState("");
	const [modelInfo, setModelInfo] = useState<string | null>(null);
	const resultRef = useRef<string>("");
	const abortRef = useRef<AbortController | null>(null);

	// Spinner animation
	useEffect(() => {
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, []);

	// Check auth on mount
	useEffect(() => {
		// HACK: skip real auth check for TUI development
		// TODO: remove this and restore the real flow
		setPhase("copilot-login");
		setDeviceUrl("https://github.com/login/device");
		setDeviceCode("ABCD-1234");
		return;

		let cancelled = false;

		async function check() {
			try {
				const result = await checkAvailableModels();
				if (cancelled) return;

				if (result.available) {
					// Already have auth (Copilot, API key, or env var)
					const m = result.models[0];
					setModelInfo(`${m.name}`);
					startGeneration();
				} else {
					// Need to log in — start Copilot device flow
					startCopilotLogin();
				}
			} catch (err) {
				if (cancelled) return;
				startCopilotLogin();
			}
		}

		check();
		return () => {
			cancelled = true;
		};
	}, []);

	// Navigate when done
	useEffect(() => {
		if (phase === "done" && resultRef.current) {
			const timer = setTimeout(() => onComplete(resultRef.current), 500);
			return () => clearTimeout(timer);
		}
	}, [phase, onComplete]);

	// Cleanup abort controller on unmount
	useEffect(() => {
		return () => {
			abortRef.current?.abort();
		};
	}, []);

	async function startCopilotLogin() {
		setPhase("copilot-login");
		const abortController = new AbortController();
		abortRef.current = abortController;

		try {
			await loginCopilot({
				onAuth: (info) => {
					setDeviceUrl(info.url);
					// openInBrowser(info.url); // TODO: restore after TUI dev
					if (info.instructions) {
						// Extract just the code from "Enter code: XXXX-XXXX"
						const code = info.instructions.replace("Enter code: ", "");
						setDeviceCode(code);
					}
				},
				onPrompt: async (prompt) => {
					// For GitHub Enterprise domain prompt — students use github.com
					// Return empty string to use github.com
					return "";
				},
				onProgress: (message) => {
					setLoginProgress(message);
				},
				signal: abortController.signal,
			});

			// Login succeeded — check models again and start generation
			const result = await checkAvailableModels();
			if (result.available) {
				const m = result.models[0];
				setModelInfo(`${m.name}`);
				startGeneration();
			} else {
				setPhase("error");
				setError("Login succeeded but no models are available. Your GitHub account may not have Copilot access.");
			}
		} catch (err) {
			if (abortController.signal.aborted) return;
			setPhase("error");
			setError(err instanceof Error ? err.message : String(err));
		}
	}

	async function startGeneration() {
		setStreamedText("");
		setToolsUsed([]);
		setCurrentTool(null);
		resultRef.current = "";

		const onEvent = (event: ResumeEvent) => {
			switch (event.type) {
				case "text":
					resultRef.current += event.delta;
					setStreamedText((prev) => prev + event.delta);
					break;
				case "tool_start":
					setCurrentTool(event.toolName);
					setToolsUsed((prev) =>
						prev.includes(event.toolName)
							? prev
							: [...prev, event.toolName],
					);
					break;
				case "tool_end":
					setCurrentTool(null);
					break;
				case "agent_end":
					setPhase("done");
					break;
				case "error":
					setPhase("error");
					setError(event.message);
					break;
			}
		};

		try {
			// 1. Extract ZIP via FastAPI backend
			setPhase("extracting");
			const { extraction_path } = await api.extractLocal(zipPath);

			// 2. Generate resume with Pi Agent
			setPhase("generating");
			await generateResume(extraction_path, onEvent);
		} catch (err) {
			setPhase("error");
			const msg = err instanceof Error ? err.message : String(err);
			const isConnErr =
				msg.includes("Unable to connect") ||
				msg.includes("ECONNREFUSED") ||
				msg.includes("fetch failed");
			setError(
				isConnErr
					? "Backend server is not running. Start it with:\n  uv run uvicorn artifactminer.api.app:app"
					: msg,
			);
		}
	}

	useKeyboard((key) => {
		if (key.name === "escape") {
			abortRef.current?.abort();
			onBack();
		}
	});

	// ── Copilot Login ──────────────────────────────────────────────
	if (phase === "copilot-login") {
		return (
			<box
				flexGrow={1}
				flexDirection="column"
				backgroundColor={theme.bgDark}
			>
				<TopBar
					title="GitHub Copilot Login"
					description="Sign in with your GitHub account to use AI-powered resume generation."
				/>

				<box
					flexGrow={1}
					flexDirection="column"
					alignItems="center"
					justifyContent="center"
					gap={3}
				>
					{deviceUrl && deviceCode ? (
						<>
							{/* Browser opened notice */}
							<text>
								<span fg={theme.success}>
									✓ Opened GitHub in your browser
								</span>
							</text>

							{/* Fallback URL */}
							<box flexDirection="column" alignItems="center" gap={1}>
								<text>
									<span fg={theme.textDim}>
										If it didn't open, go to:
									</span>
								</text>
								<text selectable>
									<span fg={theme.cyan}>
										<strong><u>{deviceUrl}</u></strong>
									</span>
								</text>
							</box>

							{/* Device code */}
							<box
								border
								borderStyle="rounded"
								borderColor={theme.gold}
								paddingLeft={4}
								paddingRight={4}
								paddingTop={1}
								paddingBottom={1}
							>
								<text selectable>
									<span fg={theme.textDim}>Enter code: </span>
									<span fg={theme.gold}>
										<strong>{deviceCode}</strong>
									</span>
								</text>
							</box>

							{/* Waiting indicator */}
							<text>
								<span fg={theme.cyan}>
									{spinnerFrames[spinnerIndex]} Waiting for
									authorization...
								</span>
							</text>

							{loginProgress && (
								<text>
									<span fg={theme.textDim}>{loginProgress}</span>
								</text>
							)}
						</>
					) : (
						<text>
							<span fg={theme.cyan}>
								{spinnerFrames[spinnerIndex]} Connecting to GitHub...
							</span>
						</text>
					)}

					{/* Info for students */}
					<box
						border
						borderStyle="rounded"
						borderColor={theme.textDim}
						padding={1}
						width={55}
					>
						<text wrap>
							<span fg={theme.textDim}>
								Students with GitHub Education get free access to
								Copilot, which includes Claude and GPT models at no
								cost.
							</span>
						</text>
					</box>
				</box>

				<box paddingLeft={2} paddingBottom={1}>
					<text>
						<span fg={theme.textDim}>
							Press <span fg={theme.cyan}>Esc</span> to cancel
						</span>
					</text>
				</box>
			</box>
		);
	}

	// ── Generating / Done / Error ──────────────────────────────────
	const steps: { label: string; doneAt: Phase[] }[] = [
		{ label: "Authenticate with GitHub Copilot", doneAt: ["extracting", "generating", "done"] },
		{ label: "Extract ZIP archive", doneAt: ["generating", "done"] },
		{ label: "Explore code repositories", doneAt: ["done"] },
		{ label: "Generate resume", doneAt: ["done"] },
	];

	const isExploring = toolsUsed.length > 0;
	const isWriting = streamedText.length > 100;

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="AI Resume Generation"
				description={
					modelInfo
						? `Generating your resume using ${modelInfo} via GitHub Copilot.`
						: "Generating your resume with AI."
				}
			/>

			<box
				flexGrow={1}
				flexDirection="column"
				alignItems="center"
				justifyContent="center"
				gap={2}
			>
				{/* Step checklist */}
				<box
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					width={55}
				>
					{steps.map((step, index) => {
						let isDone = false;
						let isCurrent = false;

						if (phase === "done") {
							isDone = true;
						} else if (index === 0) {
							// Auth
							isDone = phase !== "checking-auth" && phase !== "copilot-login";
							isCurrent = phase === "checking-auth";
						} else if (index === 1) {
							// Extract
							isDone = phase === "generating";
							isCurrent = phase === "extracting";
						} else if (index === 2) {
							// Explore
							isDone = isWriting;
							isCurrent = isExploring && !isWriting;
						} else if (index === 3) {
							// Generate
							isCurrent = isWriting;
						}

						return (
							<box key={index} flexDirection="row" gap={2}>
								<text>
									{isDone ? (
										<span fg={theme.success}>✓</span>
									) : isCurrent ? (
										<span fg={theme.cyan}>
											{spinnerFrames[spinnerIndex]}
										</span>
									) : (
										<span fg={theme.textDim}>○</span>
									)}
								</text>
								<text>
									<span
										fg={
											isDone
												? theme.success
												: isCurrent
													? theme.cyan
													: theme.textDim
										}
									>
										{step.label}
									</span>
								</text>
							</box>
						);
					})}
				</box>

				{/* Active tool indicator */}
				{currentTool && (
					<text>
						<span fg={theme.cyan}>
							{spinnerFrames[spinnerIndex]} Using tool:{" "}
						</span>
						<span fg={theme.gold}>{currentTool}</span>
					</text>
				)}

				{/* Tools used so far */}
				{toolsUsed.length > 0 && !currentTool && (
					<text>
						<span fg={theme.textDim}>
							Tools used: {toolsUsed.join(", ")}
						</span>
					</text>
				)}

				{/* Status line */}
				{phase === "extracting" && (
					<text>
						<span fg={theme.cyan}>
							{spinnerFrames[spinnerIndex]} Extracting ZIP archive...
						</span>
					</text>
				)}

				{phase === "generating" && (
					<text>
						<span fg={theme.cyan}>
							{spinnerFrames[spinnerIndex]} Analyzing code and generating
							resume...
						</span>
					</text>
				)}

				{phase === "done" && (
					<text>
						<span fg={theme.success}>
							✓ Resume generated successfully!
						</span>
					</text>
				)}

				{/* Streamed text preview */}
				{streamedText && phase === "generating" && (
					<box
						border
						borderStyle="rounded"
						borderColor={theme.textDim}
						padding={1}
						width={60}
						height={6}
					>
						<text wrap selectable>
							<span fg={theme.textDim}>
								{streamedText.slice(-200)}
							</span>
						</text>
					</box>
				)}

				{/* Error display */}
				{phase === "error" && error && (
					<box
						border
						borderStyle="single"
						borderColor={theme.error}
						padding={2}
						width={60}
					>
						<text wrap selectable>
							<span fg={theme.error}>{error}</span>
						</text>
					</box>
				)}
			</box>

			{/* Footer */}
			<box paddingLeft={2} paddingBottom={1}>
				<text>
					<span fg={theme.textDim}>
						Press <span fg={theme.cyan}>Esc</span> to go back
					</span>
				</text>
			</box>
		</box>
	);
}
