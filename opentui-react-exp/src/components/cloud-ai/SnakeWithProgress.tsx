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
import { generateResume, type ResumeEvent } from "../../agent";
import { api } from "../../api/endpoints";
import type { DeveloperProfile } from "../../api/types";
import { theme } from "../../types";
import { useToast } from "../Toast";
import { TopBar } from "../TopBar";
import { SnakeGame } from "./SnakeGame";
import {
	humanizeToolCall,
	inferPhase,
	PHASE_LABELS,
	type Phase as HumanPhase,
} from "./humanize";

interface GitIdentity {
	login: string;
	name: string | null;
	email: string;
}

interface SnakeWithProgressProps {
	zipPath: string;
	modelId: string;
	gitIdentity: GitIdentity | null;
	onComplete: (profile: DeveloperProfile) => void;
	onBack: () => void;
}

type FlowPhase = "extracting" | "generating" | "done" | "error";

interface ActivityEntry {
	tool: string;
	detail: string;
	status: "done" | "active";
}

const MAX_ACTIVITY = 100;

// Gold color cycle for pulsing glow on status text — wide range for visible pulse
const glowColors = [
	"#8B7500", // dim gold
	"#B8960B",
	"#DAB520",
	"#FFD700", // bright gold
	"#FFED66", // near-white gold
	"#FFD700",
	"#DAB520",
	"#B8960B",
];

export function SnakeWithProgress({
	zipPath,
	modelId,
	gitIdentity,
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
	const [glowIndex, setGlowIndex] = useState(0);
	const resultRef = useRef<DeveloperProfile | null>(null);
	const phaseRef = useRef(flowPhase);
	phaseRef.current = flowPhase;

	// Pulsing glow on status text
	useEffect(() => {
		if (flowPhase === "done" || flowPhase === "error") return;
		const interval = setInterval(() => {
			setGlowIndex((i) => (i + 1) % glowColors.length);
		}, 250);
		return () => clearInterval(interval);
	}, [flowPhase]);

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
					pushActivity("system", "Your developer profile is ready!", "done");
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
				const profile = await generateResume(extraction_path, onEvent, modelId, gitIdentity ?? undefined);
				resultRef.current = profile;
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
			if (phaseRef.current === "done" && key.name === "return" && resultRef.current) {
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
					{/* Layer 1: Glowing status label + divider */}
					<box flexDirection="column" marginBottom={1}>
						{flowPhase === "done" ? (
							<text>
								<span fg={theme.success}>
									<strong>✓ Complete</strong>
								</span>
								<span fg={theme.textDim}> — press Enter to view</span>
							</text>
						) : (
							<text>
								<span fg={isActive ? glowColors[glowIndex] : theme.gold}>
									<strong>{PHASE_LABELS[humanPhase]}</strong>
								</span>
							</text>
						)}
					</box>

					{/* Gold divider */}
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
						flexShrink={1}
						overflow="hidden"
						focused={false}
					>
						{activity.map((entry, i) => {
							const maxLen = Math.max(10, halfW - 10);
							const text = entry.detail.length > maxLen
								? `${entry.detail.slice(0, maxLen - 3)}...`
								: entry.detail;
							return (
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
											{text}
										</span>
									</text>
								</box>
							);
						})}
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
