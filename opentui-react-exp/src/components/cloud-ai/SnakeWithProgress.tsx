/**
 * Combined Snake game + generation progress screen.
 * Snake on the left, activity log on the right, 50/50 split.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useKeyboard, useTerminalDimensions } from "@opentui/react";
import { generateResume, type ResumeEvent } from "../../agent";
import { api } from "../../api/endpoints";
import { theme } from "../../types";
import { useToast } from "../Toast";
import { TopBar } from "../TopBar";
import { SnakeGame } from "./SnakeGame";
import { spinnerFrames } from "./shared";

interface SnakeWithProgressProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Phase = "extracting" | "generating" | "done" | "error";

interface ActivityEntry {
	tool: string;
	detail: string;
}

const MAX_ACTIVITY = 20;

const TOOL_COLORS: Record<string, string> = {
	bash: theme.cyan,
	read: theme.gold,
	grep: "#BB86FC",
};

export function SnakeWithProgress({
	zipPath,
	onComplete,
	onBack,
}: SnakeWithProgressProps) {
	const { width: termW, height: termH } = useTerminalDimensions();
	const toast = useToast();

	const [phase, setPhase] = useState<Phase>("extracting");
	const [error, setError] = useState<string | null>(null);
	const [spinnerIndex, setSpinnerIndex] = useState(0);
	const [currentTool, setCurrentTool] = useState<string | null>(null);
	const [toolsUsed, setToolsUsed] = useState<string[]>([]);
	const [activity, setActivity] = useState<ActivityEntry[]>([]);
	const [showSnake, setShowSnake] = useState(false);
	const resultRef = useRef<string>("");
	const phaseRef = useRef(phase);
	phaseRef.current = phase;

	// Spinner — stops when done
	useEffect(() => {
		if (phase === "done" || phase === "error") return;
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, [phase]);

	// Toast when done
	useEffect(() => {
		if (phase === "done") {
			toast.show({
				title: "Resume Ready!",
				message: "Press Enter to view your resume",
				variant: "success",
				duration: 10000,
			});
		}
	}, [phase]);

	function pushActivity(tool: string, detail: string) {
		setActivity((prev) => [...prev, { tool, detail }].slice(-MAX_ACTIVITY));
	}

	// Generation logic
	useEffect(() => {
		let cancelled = false;

		const onEvent = (event: ResumeEvent) => {
			if (cancelled) return;
			switch (event.type) {
				case "text":
					resultRef.current += event.delta;
					break;
				case "tool_start":
					setCurrentTool(event.toolName);
					setToolsUsed((prev) => prev.includes(event.toolName) ? prev : [...prev, event.toolName]);
					pushActivity(event.toolName, `${event.toolName}...`);
					break;
				case "tool_end":
					setCurrentTool(null);
					break;
				case "agent_end":
					pushActivity("system", "Resume complete!");
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
				pushActivity("system", "Starting AI agent...");
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
	}, [zipPath]);

	useKeyboard(
		useCallback((key: { name: string }) => {
			if (key.name === "escape") {
				if (showSnake) {
					setShowSnake(false);
				} else {
					onBack();
				}
				return;
			}
			if (phaseRef.current === "done" && key.name === "return") {
				onComplete(resultRef.current);
			}
			if (!showSnake && (key.name === "s" || key.name === "p")) {
				setShowSnake(true);
			}
		}, [showSnake, onBack, onComplete]),
	);

	// 50/50 split
	const halfW = Math.floor(termW / 2);
	const snakeW = Math.max(6, Math.floor((halfW - 4) / 4));
	const snakeH = Math.max(4, Math.floor((termH - 8) / 2));

	const visibleActivity = useMemo(
		() => activity.slice(-(termH - 8)),
		[activity, termH],
	);

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="AI Resume Generation"
				description="An AI agent is exploring your code repositories, analyzing your skills, and crafting a professional resume. This may take a minute or two depending on the size of your projects."
			/>

			<box flexGrow={1} flexDirection="row">
				{/* Left: Snake game panel */}
				<box flexGrow={1} flexBasis={0} flexDirection="column">
					{showSnake ? (
						<SnakeGame width={snakeW} height={snakeH} />
					) : (
						<box
							flexGrow={1}
							flexDirection="column"
							border
							borderStyle="rounded"
							borderColor={theme.goldDim}
							onMouseDown={() => setShowSnake(true)}
						>
							{Array.from({ length: snakeH * 2 }, (_, i) => (
								<text key={i}>
									<span fg="#222222">
										{(i % 2 === 0 ? " ·" : "  ").repeat(snakeW).slice(0, snakeW * 4)}
									</span>
								</text>
							))}
							<box
								position="absolute"
								top={0}
								left={0}
								right={0}
								bottom={0}
								alignItems="center"
								justifyContent="center"
								flexDirection="column"
								gap={1}
							>
								<ascii-font text="SNAKE" font="tiny" color={theme.goldDim} />
								<box
									border
									borderStyle="rounded"
									borderColor={theme.gold}
									paddingLeft={3}
									paddingRight={3}
									paddingTop={1}
									paddingBottom={1}
									onMouseDown={() => setShowSnake(true)}
								>
									<text>
										<span fg={theme.gold}>
											<strong>Click here or press S to play!</strong>
										</span>
									</text>
								</box>
								<text>
									<span fg={theme.textDim}>
										Play while your resume generates
									</span>
								</text>
							</box>
						</box>
					)}
				</box>

				{/* Right: Activity sidebar */}
				<box
					flexGrow={1}
					flexBasis={0}
					flexDirection="column"
					borderLeft
					borderColor={theme.goldDim}
					paddingLeft={1}
					paddingRight={1}
					paddingTop={1}
				>
					<box marginBottom={1}>
						<text>
							<span fg={theme.gold}>
								<strong>Activity</strong>
							</span>
						</text>
					</box>

					{visibleActivity.map((entry, i) => {
						const isLatest = i === visibleActivity.length - 1;
						const toolColor = TOOL_COLORS[entry.tool] ?? (entry.tool === "system" ? theme.textDim : theme.textSecondary);

						return (
							<text key={i}>
								{isLatest && phase !== "done" ? (
									<span fg={theme.cyan}>{spinnerFrames[spinnerIndex]} </span>
								) : (
									<span fg={theme.textDim}>{"  "}</span>
								)}
								{entry.tool !== "system" && (
									<span fg={toolColor}>{entry.tool.padEnd(5)} </span>
								)}
								<span fg={isLatest ? theme.textSecondary : theme.textDim}>
									{entry.detail.slice(0, halfW - 12)}
								</span>
							</text>
						);
					})}

					{toolsUsed.length > 0 && (
						<box marginTop={1}>
							<text>
								<span fg={theme.textDim}>Tools: </span>
								{toolsUsed.map((t, i) => (
									<span key={t} fg={t === currentTool ? theme.gold : theme.textDim}>
										{t}{i < toolsUsed.length - 1 ? " " : ""}
									</span>
								))}
							</text>
						</box>
					)}

					{phase === "error" && error && (
						<box border borderStyle="single" borderColor={theme.error} padding={1} marginTop={1}>
							<text wrap selectable>
								<span fg={theme.error}>{error}</span>
							</text>
						</box>
					)}
				</box>
			</box>
		</box>
	);
}
