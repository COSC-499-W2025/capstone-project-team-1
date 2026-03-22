/**
 * Combined Snake game + generation progress screen.
 * Snake on the left, humanized activity sidebar on the right.
 *
 * The activity sidebar uses a two-layer architecture:
 * - Layer 1: Warm status message + Knight Rider spinner
 * - Layer 2: Scrollable humanized activity log
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useKeyboard, useTerminalDimensions } from "@opentui/react";
import "opentui-spinner/react";
import { generateResume, type ResumeEvent } from "../../agent";
import { api } from "../../api/endpoints";
import { theme } from "../../types";
import { useToast } from "../Toast";
import { TopBar } from "../TopBar";
import { SnakeGame } from "./SnakeGame";
import { createFrames, createColors } from "./knight-rider-spinner";
import {
	humanizeToolCall,
	inferPhase,
	PHASE_LABELS,
	type Phase as HumanPhase,
} from "./humanize";

interface SnakeWithProgressProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type FlowPhase = "extracting" | "generating" | "done" | "error";

interface ActivityEntry {
	tool: string;
	detail: string;
	status: "done" | "active";
}

const MAX_ACTIVITY = 100;

// Knight Rider spinner config — gold theme
const krFrames = createFrames({
	color: theme.gold,
	style: "blocks",
	width: 10,
	inactiveFactor: 0.6,
	minAlpha: 0.3,
});
const krColors = createColors({
	color: theme.gold,
	style: "blocks",
	width: 10,
	inactiveFactor: 0.6,
	minAlpha: 0.3,
});

export function SnakeWithProgress({
	zipPath,
	onComplete,
	onBack,
}: SnakeWithProgressProps) {
	const { width: termW, height: termH } = useTerminalDimensions();
	const toast = useToast();

	const [flowPhase, setFlowPhase] = useState<FlowPhase>("extracting");
	const [error, setError] = useState<string | null>(null);
	const [activity, setActivity] = useState<ActivityEntry[]>([]);
	const [showSnake, setShowSnake] = useState(false);
	const [isStreamingText, setIsStreamingText] = useState(false);
	const [hasNewActivity, setHasNewActivity] = useState(false);
	const resultRef = useRef<string>("");
	const phaseRef = useRef(flowPhase);
	phaseRef.current = flowPhase;

	// Toast when done
	useEffect(() => {
		if (flowPhase === "done") {
			toast.show({
				title: "Resume Ready!",
				message: "Press Enter to view your resume",
				variant: "success",
				duration: 10000,
			});
		}
	}, [flowPhase]);

	function pushActivity(tool: string, detail: string, status: "done" | "active" = "active") {
		setActivity((prev) => {
			// Mark previous active entry as done
			const updated = prev.map((e) =>
				e.status === "active" ? { ...e, status: "done" as const } : e,
			);
			return [...updated, { tool, detail, status }].slice(-MAX_ACTIVITY);
		});
		setHasNewActivity(true);
	}

	// Infer the human-friendly phase from activity
	const humanPhase: HumanPhase = useMemo(() => {
		if (flowPhase === "done") return "done";
		if (flowPhase === "extracting") return "exploring";
		return inferPhase(activity, isStreamingText);
	}, [flowPhase, activity, isStreamingText]);

	// Generation logic
	useEffect(() => {
		let cancelled = false;

		const onEvent = (event: ResumeEvent) => {
			if (cancelled) return;
			switch (event.type) {
				case "text":
					resultRef.current += event.delta;
					if (!isStreamingText) setIsStreamingText(true);
					break;
				case "tool_start": {
					const detail = humanizeToolCall(event.toolName, event.args);
					pushActivity(event.toolName, detail);
					break;
				}
				case "tool_end":
					// Mark the latest entry as done
					setActivity((prev) =>
						prev.map((e) =>
							e.status === "active" ? { ...e, status: "done" as const } : e,
						),
					);
					break;
				case "agent_end":
					pushActivity("system", "Your resume is ready!", "done");
					setFlowPhase("done");
					break;
				case "error":
					setFlowPhase("error");
					setError(event.message);
					break;
			}
		};

		(async () => {
			try {
				setFlowPhase("extracting");
				pushActivity("system", "Unpacking your projects...");
				const { extraction_path } = await api.extractLocal(zipPath);
				if (cancelled) return;
				pushActivity("system", "Found your projects!", "done");

				setFlowPhase("generating");
				pushActivity("system", "Getting the AI started...");
				await generateResume(extraction_path, onEvent);
			} catch (err) {
				if (cancelled) return;
				setFlowPhase("error");
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
	const snakeH = Math.max(4, Math.floor((termH - 14) / 2));

	const isActive = flowPhase !== "done" && flowPhase !== "error";

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
											<strong>LET'S PLAY!</strong>
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

				{/* Right: Activity sidebar — two-layer architecture */}
				<box
					flexGrow={1}
					flexBasis={0}
					flexDirection="column"
					borderLeft
					borderColor={theme.goldDim}
					paddingLeft={2}
					paddingRight={2}
					paddingTop={1}
				>
					{/* Layer 1: Status + Knight Rider spinner */}
					<box flexDirection="column" marginBottom={1}>
						<text>
							<span fg={theme.gold}>
								<strong>{PHASE_LABELS[humanPhase]}</strong>
							</span>
						</text>
						{isActive && (
							<box marginTop={1}>
								<spinner
									frames={krFrames}
									color={krColors}
									interval={40}
								/>
							</box>
						)}
						{flowPhase === "done" && (
							<text>
								<span fg={theme.success}>
									<strong>✓ Complete</strong>
								</span>
								<span fg={theme.textDim}> — press Enter to view</span>
							</text>
						)}
					</box>

					{/* Separator */}
					<box marginBottom={1}>
						<text>
							<span fg={theme.goldDim}>
								{"─".repeat(Math.max(1, halfW - 6))}
							</span>
						</text>
					</box>

					{/* Layer 2: Scrollable humanized activity log */}
					<scrollbox
						flexGrow={1}
						focused={false}
					>
						{activity.map((entry, i) => (
							<box key={i} flexDirection="row" gap={1}>
								<text>
									{entry.status === "done" ? (
										<span fg={theme.success}>✓</span>
									) : (
										<span fg={theme.cyan}>●</span>
									)}
								</text>
								<text>
									<span
										fg={
											entry.status === "active"
												? theme.textPrimary
												: theme.textDim
										}
									>
										{entry.detail}
									</span>
								</text>
							</box>
						))}
					</scrollbox>

					{/* Error display */}
					{flowPhase === "error" && error && (
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
