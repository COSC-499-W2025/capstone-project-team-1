import { useEffect, useRef, useState } from "react";
import { useKeyboard, useTimeline } from "@opentui/react";
import { generateResume, type ResumeEvent } from "../../agent";
import { api } from "../../api/endpoints";
import { theme } from "../../types";
import { spinnerFrames } from "./shared";

interface GenerationProgressProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Phase = "extracting" | "generating" | "done" | "error";

interface ActivityEntry {
	tool: string;
	detail: string;
	timestamp: number;
}

const MAX_ACTIVITY_LINES = 8;
const PROGRESS_BAR_WIDTH = 40;

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
	const [activity, setActivity] = useState<ActivityEntry[]>([]);
	const [progressPct, setProgressPct] = useState(0);
	const [animatedPct, setAnimatedPct] = useState(0);
	const resultRef = useRef<string>("");

	// Spinner
	useEffect(() => {
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, []);

	// Animate progress bar smoothly
	const timeline = useTimeline();
	useEffect(() => {
		timeline.add(
			{ value: animatedPct },
			{
				value: progressPct,
				duration: 400,
				ease: "easeOutCubic",
				onUpdate: (anim) => {
					setAnimatedPct(Math.round(anim.targets[0].value));
				},
			},
		);
	}, [progressPct]);

	// Derive progress from phase + activity
	useEffect(() => {
		if (phase === "extracting") setProgressPct(10);
		else if (phase === "generating") {
			// Scale from 20 to 90 based on streamed text length
			const textProgress = Math.min(streamedText.length / 300, 1);
			setProgressPct(20 + Math.round(textProgress * 70));
		} else if (phase === "done") setProgressPct(100);
	}, [phase, streamedText.length]);

	// Navigate when done
	useEffect(() => {
		if (phase === "done" && resultRef.current) {
			const timer = setTimeout(() => onComplete(resultRef.current), 1500);
			return () => clearTimeout(timer);
		}
	}, [phase, onComplete]);

	// Helper to push activity
	function pushActivity(tool: string, detail: string) {
		setActivity((prev) => {
			const next = [...prev, { tool, detail, timestamp: Date.now() }];
			return next.slice(-MAX_ACTIVITY_LINES);
		});
	}

	// Start generation on mount
	useEffect(() => {
		let cancelled = false;

		// HACK: fake progress for TUI development
		// TODO: remove this block and uncomment the real flow below
		(async () => {
			setPhase("extracting");
			pushActivity("system", "Extracting ZIP archive...");
			await new Promise((r) => setTimeout(r, 1200));
			if (cancelled) return;
			pushActivity("system", "Extraction complete — 3 repositories found");

			setPhase("generating");
			pushActivity("system", "Connecting to Claude Sonnet 4 via Copilot...");
			await new Promise((r) => setTimeout(r, 800));
			if (cancelled) return;

			const fakeActions = [
				["bash", "Running: ls -la"],
				["read", "Reading README.md"],
				["bash", "Running: git log --oneline -20"],
				["grep", "Searching for: import|require"],
				["read", "Reading package.json"],
				["read", "Reading src/index.tsx"],
				["bash", "Running: find . -name '*.py' | head -20"],
				["read", "Reading pyproject.toml"],
				["bash", "Running: git shortlog -sn"],
				["read", "Reading src/artifactminer/api/app.py"],
			];

			for (const [tool, detail] of fakeActions) {
				if (cancelled) return;
				setCurrentTool(tool);
				setToolsUsed((prev) =>
					prev.includes(tool) ? prev : [...prev, tool],
				);
				pushActivity(tool, detail);
				await new Promise((r) => setTimeout(r, 600 + Math.random() * 400));
			}
			if (cancelled) return;
			setCurrentTool(null);
			pushActivity("system", "Writing resume...");

			const fakeText = "# Resume\n\n## Summary\nFull-stack developer with experience in React, Python, and cloud infrastructure. Demonstrated proficiency in building modern web applications with FastAPI, React, and terminal UI frameworks.\n\n## Technical Skills\n- **Languages**: TypeScript, Python, Go, SQL\n- **Frameworks**: React 19, FastAPI, OpenTUI, SQLAlchemy\n- **Tools**: Git, Docker, SQLite, Alembic, Bun\n\n## Projects\n### Artifact Miner\n- Automated code analysis and resume generation platform\n- Built with FastAPI + React + OpenTUI terminal interface\n- Implemented deep repository analysis with skill extraction\n- Designed evidence-driven resume pipeline with LLM integration";
			for (const char of fakeText) {
				if (cancelled) return;
				resultRef.current += char;
				setStreamedText((prev) => prev + char);
				await new Promise((r) => setTimeout(r, 12));
			}

			if (cancelled) return;
			pushActivity("system", "Resume generation complete!");
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
						prev.includes(event.toolName) ? prev : [...prev, event.toolName],
					);
					pushActivity(event.toolName, `Using ${event.toolName}...`);
					break;
				case "tool_end":
					setCurrentTool(null);
					break;
				case "agent_end":
					pushActivity("system", "Resume generation complete!");
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
				pushActivity("system", "Extracting ZIP archive...");
				const { extraction_path } = await api.extractLocal(zipPath);
				if (cancelled) return;
				pushActivity("system", "Extraction complete");

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

		return () => { cancelled = true; };
		*/
	}, [zipPath]);

	useKeyboard((key) => {
		if (key.name === "escape") onBack();
	});

	// ── steps ───────────────────────────────────────────────────
	const steps = [
		{ label: "Extract ZIP archive", done: phase !== "extracting", active: phase === "extracting" },
		{ label: "Connect to AI model", done: phase === "generating" && toolsUsed.length > 0 || phase === "done", active: phase === "generating" && toolsUsed.length === 0 },
		{ label: "Explore code repositories", done: streamedText.length > 50, active: toolsUsed.length > 0 && streamedText.length <= 50 },
		{ label: "Generate resume", done: phase === "done", active: streamedText.length > 50 && phase !== "done" },
	];

	// ── progress bar chars ──────────────────────────────────────
	const filled = Math.round((animatedPct / 100) * PROGRESS_BAR_WIDTH);
	const empty = PROGRESS_BAR_WIDTH - filled;
	const barFilled = "█".repeat(filled);
	const barEmpty = "░".repeat(empty);

	// ── tool badges ─────────────────────────────────────────────
	const toolBadges = toolsUsed.map((t) => {
		const isActive = t === currentTool;
		return { name: t, isActive };
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			{/* Header */}
			<box
				paddingLeft={3}
				paddingRight={3}
				paddingTop={1}
				paddingBottom={1}
				borderBottom
				borderColor={theme.goldDim}
			>
				<box flexDirection="column" gap={0}>
					<text>
						<span fg={theme.gold}>
							<strong>AI Resume Generation</strong>
						</span>
						{modelInfo && (
							<span fg={theme.textDim}> — {modelInfo}</span>
						)}
					</text>
					<text>
						<span fg={theme.textDim}>
							Powered by GitHub Copilot
						</span>
					</text>
				</box>
			</box>

			{/* Main content */}
			<box
				flexGrow={1}
				flexDirection="column"
				paddingLeft={3}
				paddingRight={3}
				paddingTop={2}
				gap={2}
			>
				{/* Progress bar */}
				<box flexDirection="column" gap={1}>
					<box flexDirection="row" justifyContent="space-between">
						<text>
							<span fg={theme.textSecondary}>
								<strong>Progress</strong>
							</span>
						</text>
						<text>
							<span fg={phase === "done" ? theme.success : theme.gold}>
								<strong>{animatedPct}%</strong>
							</span>
						</text>
					</box>
					<text>
						<span fg={phase === "done" ? theme.success : theme.gold}>{barFilled}</span>
						<span fg="#333333">{barEmpty}</span>
					</text>
				</box>

				{/* Steps */}
				<box
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					paddingLeft={2}
					paddingRight={2}
					paddingTop={1}
					paddingBottom={1}
				>
					{steps.map((step, i) => (
						<box key={i} flexDirection="row" gap={2}>
							<text>
								{step.done ? (
									<span fg={theme.success}>✓</span>
								) : step.active ? (
									<span fg={theme.cyan}>{spinnerFrames[spinnerIndex]}</span>
								) : (
									<span fg="#555555">○</span>
								)}
							</text>
							<text>
								<span fg={step.done ? theme.success : step.active ? theme.textPrimary : "#555555"}>
									{step.label}
								</span>
							</text>
						</box>
					))}
				</box>

				{/* Tool badges */}
				{toolsUsed.length > 0 && (
					<box flexDirection="row" gap={1}>
						<text>
							<span fg={theme.textDim}>Tools: </span>
						</text>
						{toolBadges.map((t) => (
							<text key={t.name}>
								<span fg={t.isActive ? theme.gold : theme.textDim}>
									{t.isActive ? `[${t.name}]` : t.name}
								</span>
							</text>
						))}
					</box>
				)}

				{/* Activity log */}
				<box flexDirection="column" flexGrow={1}>
					<text>
						<span fg={theme.textSecondary}>
							<strong>Agent Activity</strong>
						</span>
					</text>
					<box
						flexDirection="column"
						border
						borderStyle="rounded"
						borderColor="#333333"
						paddingLeft={1}
						paddingRight={1}
						paddingTop={1}
						paddingBottom={1}
						flexGrow={1}
					>
						{activity.length === 0 ? (
							<text>
								<span fg="#555555">Waiting...</span>
							</text>
						) : (
							activity.map((entry, i) => {
								const isLatest = i === activity.length - 1;
								const toolColor =
									entry.tool === "system" ? theme.textDim
									: entry.tool === "bash" ? theme.cyan
									: entry.tool === "read" ? theme.gold
									: entry.tool === "grep" ? "#BB86FC"
									: theme.textSecondary;
								return (
									<text key={i}>
										<span fg={toolColor}>
											{entry.tool === "system" ? "  " : `${entry.tool.padEnd(5)} `}
										</span>
										<span fg={isLatest ? theme.textPrimary : theme.textDim}>
											{isLatest && phase !== "done" ? `${spinnerFrames[spinnerIndex]} ` : "  "}
										</span>
										<span fg={isLatest ? theme.textSecondary : theme.textDim}>
											{entry.detail}
										</span>
									</text>
								);
							})
						)}
					</box>
				</box>

				{/* Done message */}
				{phase === "done" && (
					<text>
						<span fg={theme.success}>
							<strong>✓ Resume generated successfully!</strong>
						</span>
					</text>
				)}

				{/* Error */}
				{phase === "error" && error && (
					<box
						border
						borderStyle="single"
						borderColor={theme.error}
						padding={1}
					>
						<text wrap selectable>
							<span fg={theme.error}>{error}</span>
						</text>
					</box>
				)}
			</box>

			{/* Footer */}
			<box paddingLeft={3} paddingBottom={1}>
				<text>
					<span fg={theme.textDim}>
						Press <span fg={theme.cyan}>Esc</span> to cancel
					</span>
				</text>
			</box>
		</box>
	);
}
