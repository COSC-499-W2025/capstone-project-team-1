import { useEffect, useRef, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { generateResume, type ResumeEvent } from "../../agent";
import { api } from "../../api/endpoints";
import { theme } from "../../types";
import { TopBar } from "../TopBar";
import { spinnerFrames } from "./shared";

interface GenerationProgressProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Phase = "extracting" | "generating" | "done" | "error";

export function GenerationProgress({
	zipPath,
	onComplete,
	onBack,
}: GenerationProgressProps) {
	const [phase, setPhase] = useState<Phase>("extracting");
	const [error, setError] = useState<string | null>(null);
	const [spinnerIndex, setSpinnerIndex] = useState(0);
	const [currentTool, setCurrentTool] = useState<string | null>(null);
	const [toolsUsed, setToolsUsed] = useState<string[]>([]);
	const [streamedText, setStreamedText] = useState("");
	const [modelInfo, setModelInfo] = useState<string | null>(null);
	const resultRef = useRef<string>("");

	// Spinner
	useEffect(() => {
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, []);

	// Navigate when done
	useEffect(() => {
		if (phase === "done" && resultRef.current) {
			const timer = setTimeout(() => onComplete(resultRef.current), 500);
			return () => clearTimeout(timer);
		}
	}, [phase, onComplete]);

	// Start generation on mount
	useEffect(() => {
		let cancelled = false;

		// HACK: fake progress for TUI development
		// TODO: remove this block and uncomment the real flow below
		(async () => {
			setPhase("extracting");
			await new Promise((r) => setTimeout(r, 1500));
			if (cancelled) return;

			setPhase("generating");
			setToolsUsed(["read", "bash", "grep"]);
			setCurrentTool("bash");
			await new Promise((r) => setTimeout(r, 1000));
			if (cancelled) return;
			setCurrentTool("read");
			await new Promise((r) => setTimeout(r, 1000));
			if (cancelled) return;
			setCurrentTool(null);

			const fakeText = "# Resume\n\n## Summary\nFull-stack developer with experience in React, Python, and cloud infrastructure...\n\n## Technical Skills\n- **Languages**: TypeScript, Python, Go\n- **Frameworks**: React, FastAPI, OpenTUI\n\n## Projects\n### Artifact Miner\n- Code analysis and resume generation tool\n- Built with FastAPI + React + OpenTUI";
			for (const char of fakeText) {
				if (cancelled) return;
				resultRef.current += char;
				setStreamedText((prev) => prev + char);
				await new Promise((r) => setTimeout(r, 15));
			}

			if (cancelled) return;
			setPhase("done");
		})();

		return () => { cancelled = true; };

		/* REAL FLOW — uncomment when done with TUI dev
		const onEvent = (event: ResumeEvent) => {
			if (cancelled) return;
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

		(async () => {
			try {
				setPhase("extracting");
				const { extraction_path } = await api.extractLocal(zipPath);
				if (cancelled) return;

				setPhase("generating");
				await generateResume(extraction_path, onEvent);
			} catch (err) {
				if (cancelled) return;
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
		})();

		return () => {
			cancelled = true;
		};
		*/
	}, [zipPath]);

	useKeyboard((key) => {
		if (key.name === "escape") onBack();
	});

	const steps = [
		{ label: "Extract ZIP archive", done: phase !== "extracting", active: phase === "extracting" },
		{ label: "Explore code repositories", done: streamedText.length > 100, active: toolsUsed.length > 0 && streamedText.length <= 100 },
		{ label: "Generate resume", done: phase === "done", active: streamedText.length > 100 && phase !== "done" },
	];

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
					{steps.map((step, index) => (
						<box key={index} flexDirection="row" gap={2}>
							<text>
								{step.done ? (
									<span fg={theme.success}>✓</span>
								) : step.active ? (
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
										step.done
											? theme.success
											: step.active
												? theme.cyan
												: theme.textDim
									}
								>
									{step.label}
								</span>
							</text>
						</box>
					))}
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

				{/* Tools used */}
				{toolsUsed.length > 0 && !currentTool && (
					<text>
						<span fg={theme.textDim}>
							Tools used: {toolsUsed.join(", ")}
						</span>
					</text>
				)}

				{/* Status */}
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
							{spinnerFrames[spinnerIndex]} Analyzing code and generating resume...
						</span>
					</text>
				)}
				{phase === "done" && (
					<text>
						<span fg={theme.success}>✓ Resume generated successfully!</span>
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

				{/* Error */}
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
