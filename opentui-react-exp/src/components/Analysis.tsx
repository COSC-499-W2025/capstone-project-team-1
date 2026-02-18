import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { type AnalysisMode, theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface AnalysisProps {
	mode: AnalysisMode;
	onDraftReady: () => void;
	onReady: () => void;
	onCancelReturn: () => void;
}

const stageOrder = ["EXTRACT", "STAGE_1", "STAGE_2", "STAGE_3"] as const;

const stageLabel: Record<string, string> = {
	EXTRACT:  "Extract   —  Read repos",
	STAGE_1:  "Stage 1   —  Analyze",
	STAGE_2:  "Stage 2   —  Draft",
	STAGE_3:  "Stage 3   —  Polish",
};

// Context shown in the Activity panel while each stage is active
const stageContext: Record<string, { heading: string; lines: string[] }> = {
	EXTRACT: {
		heading: "Gathering raw data from your repositories",
		lines: [
			"We're reading README files, commit messages, folder",
			"structure, dependency graphs, and code metrics for",
			"every repo you selected. No AI runs at this stage —",
			"just thorough, local extraction. Nothing leaves your",
			"machine.",
		],
	},
	STAGE_1: {
		heading: "Understanding what you built and how",
		lines: [
			"A small local AI model is now analysing each project.",
			"It scores commit quality, maps your skill timeline,",
			"measures complexity, and infers what each repo is",
			"actually for — so your resume reflects real depth,",
			"not just a list of technologies.",
		],
	},
	STAGE_2: {
		heading: "Writing your resume",
		lines: [
			"The AI is now composing project bullets, technical",
			"summaries, and a portfolio overview — all grounded",
			"in the evidence extracted from your code. Output is",
			"structured as clean Markdown ready to export.",
		],
	},
	STAGE_3: {
		heading: "Polishing based on your feedback",
		lines: [
			"The AI is refining tone, language, and emphasis",
			"using the notes you provided. This pass targets",
			"the specific gaps you flagged in the draft.",
		],
	},
};

// Maps technical log prefixes → human-readable activity descriptions
const STEP_MAP: Array<[string, string]> = [
	["Extracting README",                "Reading project documentation"],
	["Classifying commits",              "Analyzing commit history"],
	["Extracting structure",             "Mapping project structure"],
	["Extracting code constructs",       "Scanning code constructs"],
	["Inferring project type",           "Detecting project type"],
	["Extracting git stats",             "Gathering git statistics"],
	["Computing test ratio",             "Measuring test coverage"],
	["Scoring commit quality",           "Scoring commit quality"],
	["Measuring module breadth",         "Measuring module breadth"],
	["Computing style metrics",          "Analyzing code style"],
	["Computing complexity metrics",     "Measuring code complexity"],
	["Computing skill timeline",         "Building skill timeline"],
	["Extracting enriched constructs",   "Deep code analysis"],
	["Analyzing import graph",           "Mapping dependencies"],
	["Extracting config fingerprint",    "Reading project configuration"],
	["Inferring project purpose",        "AI: Inferring project purpose"],
	["Running project query",            "AI: Writing project bullets"],
	["Running portfolio query",          "AI: Composing portfolio summary"],
	["Assembling resume",                "Assembling resume document"],
];

const NOISE_PREFIXES = [
	"Pipeline request",
	"Phase 1 worker",
	"Phase 1 started",
	"Phase 3 worker",
	"Phase 3 started",
	"Checking model",
	"Found ",
	"Analyzing [",
];

function toFriendlyStep(msg: string): string | null {
	for (const [prefix, friendly] of STEP_MAP) {
		if (msg.startsWith(prefix)) return friendly;
	}
	for (const noise of NOISE_PREFIXES) {
		if (msg.startsWith(noise)) return null;
	}
	const trimmed = msg.replace(/\.{2,}$/, "").trim();
	return trimmed.length > 0 ? trimmed : null;
}

function repoBar(done: number, total: number, width = 14): string {
	if (total === 0) return "░".repeat(width);
	const filled = Math.round((done / total) * width);
	return "█".repeat(filled) + "░".repeat(width - filled);
}

export function Analysis({
	mode,
	onDraftReady,
	onReady,
	onCancelReturn,
}: AnalysisProps) {
	const {
		state,
		setPipelineStatus,
		setPipelineStage,
		setPipelineTelemetry,
		setPipelineMessages,
		setResumeV3Draft,
		setResumeV3Output,
		setPipelineNotice,
	} = useAppState();

	const [readyGate, setReadyGate] = useState(false);
	const [localError, setLocalError] = useState<string | null>(null);
	const [isCancelling, setIsCancelling] = useState(false);
	const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

	useEffect(() => {
		if (mode !== "phase1" && mode !== "phase3") return;
		void state.pipelineJobId;
		setReadyGate(false);
		setLocalError(null);
	}, [mode, state.pipelineJobId]);

	useEffect(() => {
		const jobId = state.pipelineJobId;
		if (!jobId) {
			setLocalError("No pipeline job is active.");
			return;
		}

		let cancelled = false;

		const scheduleNext = () => {
			if (!cancelled) {
				pollTimerRef.current = setTimeout(pollStatus, 600);
			}
		};

		const pollStatus = async () => {
			try {
				const status = await api.getPipelineStatus(jobId);
				if (cancelled) return;

				setPipelineStatus(status.status);
				setPipelineStage(status.stage);
				setPipelineTelemetry(status.telemetry);
				setPipelineMessages(status.messages);
				setResumeV3Draft(status.draft);
				setResumeV3Output(status.output);

				if (status.error) setLocalError(status.error);

				if (status.status === "draft_ready" && mode === "phase1") {
					onDraftReady();
					return;
				}
				if (status.status === "complete") {
					setReadyGate(true);
					return;
				}
				if (status.status === "cancelled") {
					setPipelineNotice("Pipeline cancelled.");
					onCancelReturn();
					return;
				}
				if (status.status === "error") {
					setReadyGate(false);
					return;
				}

				scheduleNext();
			} catch (error) {
				if (cancelled) return;
				setLocalError(toErrorMessage(error));
				scheduleNext();
			}
		};

		void pollStatus();

		return () => {
			cancelled = true;
			if (pollTimerRef.current) {
				clearTimeout(pollTimerRef.current);
				pollTimerRef.current = null;
			}
		};
	}, [
		mode,
		onCancelReturn,
		onDraftReady,
		setPipelineMessages,
		setPipelineNotice,
		setPipelineStage,
		setPipelineStatus,
		setPipelineTelemetry,
		setResumeV3Draft,
		setResumeV3Output,
		state.pipelineJobId,
	]);

	const cancelJob = async () => {
		if (!state.pipelineJobId || isCancelling) return;
		setIsCancelling(true);
		try {
			await api.cancelPipeline(state.pipelineJobId);
			setPipelineStatus("cancelled");
			setPipelineNotice("Pipeline cancelled by user.");
			onCancelReturn();
		} catch (error) {
			setLocalError(toErrorMessage(error));
		} finally {
			setIsCancelling(false);
		}
	};

	useKeyboard((key) => {
		if (key.name === "escape") {
			if (!readyGate) void cancelJob();
			return;
		}
		if ((key.name === "return" || key.name === "enter") && readyGate) {
			onReady();
		}
	});

	const telemetry = state.pipelineTelemetry;
	const activeStage = telemetry?.stage || state.pipelineStage || "EXTRACT";
	const activeIndex = stageOrder.indexOf(activeStage as (typeof stageOrder)[number]);

	const stageRows = useMemo(
		() =>
			stageOrder.map((stageName, index) => {
				const completed =
					state.pipelineStatus === "complete" ||
					(activeIndex >= 0 && index < activeIndex);
				const active =
					state.pipelineStatus !== "complete" &&
					state.pipelineStatus !== "cancelled" &&
					state.pipelineStatus !== "error" &&
					activeStage === stageName;

				let marker = "○";
				let color: string = theme.textDim;

				if (completed) { marker = "✓"; color = theme.success; }
				else if (active) { marker = "▶"; color = theme.cyan; }

				if (state.pipelineStatus === "cancelled") color = theme.warning;
				if (state.pipelineStatus === "error" && active) color = theme.error;

				return { stageName, marker, color };
			}),
		[activeIndex, activeStage, state.pipelineStatus],
	);

	// Transform raw log messages → friendly activity steps
	const activitySteps = useMemo(() => {
		const steps: string[] = [];
		for (const msg of state.pipelineMessages) {
			const friendly = toFriendlyStep(msg);
			if (friendly) steps.push(friendly);
		}
		return steps;
	}, [state.pipelineMessages]);

	const MAX_VISIBLE = 16;
	const visibleSteps = activitySteps.slice(-MAX_VISIBLE);
	const hiddenCount = activitySteps.length - visibleSteps.length;
	const isRunning =
		state.pipelineStatus === "running" || state.pipelineStatus === "idle";

	const statusColor =
		state.pipelineStatus === "running" ? theme.cyan
		: state.pipelineStatus === "complete" ? theme.success
		: state.pipelineStatus === "error" ? theme.error
		: state.pipelineStatus === "cancelled" ? theme.warning
		: theme.textDim;

	const reposDone = telemetry?.repos_done ?? 0;
	const reposTotal = telemetry?.repos_total ?? 0;
	const elapsed = (telemetry?.elapsed_seconds ?? 0).toFixed(1);

	const subtitle =
		mode === "phase1"
			? "Extract + Stage 1 + Stage 2"
			: "Stage 3  —  Polish from draft";

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar step="Pipeline" title="Live Progress" description={subtitle} />

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>

				{/* ── Left: mission control panel ── */}
				<box
					width={36}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					title="  Pipeline  "
					titleAlignment="center"
					padding={2}
					gap={1}
				>
					{/* Stage timeline */}
					{stageRows.map((row) => (
						<text key={row.stageName}>
							<span fg={row.color}>
								{row.marker}  {stageLabel[row.stageName] ?? row.stageName}
							</span>
						</text>
					))}

					{/* Status + timing */}
					<box
						flexDirection="column"
						gap={1}
						borderTop
						borderColor={theme.bgLight}
						paddingTop={1}
						marginTop={1}
					>
						<text>
							<span fg={theme.textDim}>Status   </span>
							<span fg={statusColor}>
								<strong>{state.pipelineStatus.toUpperCase()}</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>Elapsed  </span>
							<span fg={theme.textSecondary}>{elapsed}s</span>
						</text>
						<text>
							<span fg={theme.textDim}>Model    </span>
							<span fg={theme.textSecondary}>
								{telemetry?.active_model
									? telemetry.active_model.length > 18
										? telemetry.active_model.slice(0, 18) + "…"
										: telemetry.active_model
									: "—"}
							</span>
						</text>
					</box>

					{/* Repo progress */}
					<box
						flexDirection="column"
						gap={1}
						borderTop
						borderColor={theme.bgLight}
						paddingTop={1}
						marginTop={1}
					>
						<text>
							<span fg={theme.textDim}>Repos    </span>
							<span fg={reposDone > 0 ? theme.textPrimary : theme.textDim}>
								{reposDone}
							</span>
							<span fg={theme.textDim}> / {reposTotal}</span>
						</text>
						{reposTotal > 0 ? (
							<text>
								<span fg={reposDone > 0 ? theme.gold : theme.textDim}>
									{repoBar(reposDone, reposTotal)}
								</span>
								<span fg={theme.textDim}>
									{"  "}{reposTotal > 0
										? Math.round((reposDone / reposTotal) * 100)
										: 0}%
								</span>
							</text>
						) : null}
						{(telemetry?.facts_total ?? 0) > 0 ? (
							<text>
								<span fg={theme.textDim}>Facts    </span>
								<span fg={theme.textSecondary}>{telemetry?.facts_total}</span>
							</text>
						) : null}
					</box>
				</box>

				{/* ── Right: activity feed ── */}
				<box
					flexGrow={1}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.cyanDim}
					title="  Activity  "
					titleAlignment="center"
					padding={2}
					gap={1}
				>
					{/* Stage context: heading + description */}
					{stageContext[activeStage] ? (
						<box
							flexDirection="column"
							gap={1}
							borderBottom
							borderColor={theme.bgLight}
							paddingBottom={1}
						>
							<text>
								<span fg={theme.gold}>
									<strong>{stageContext[activeStage].heading}</strong>
								</span>
							</text>
							{stageContext[activeStage].lines.map((line, i) => (
								<text key={i}>
									<span fg={theme.textDim}>{line}</span>
								</text>
							))}
						</box>
					) : null}

					{/* Current repo header */}
					{telemetry?.current_repo ? (
						<box
							flexDirection="column"
							gap={1}
							borderBottom
							borderColor={theme.bgLight}
							paddingBottom={1}
						>
							<text>
								<span fg={theme.textDim}>Now analyzing</span>
							</text>
							<text>
								<span fg={theme.gold}>
									<strong>{telemetry.current_repo}</strong>
								</span>
								{reposTotal > 0 ? (
									<span fg={theme.textDim}>
										{"  —  repo "}
										{reposDone + 1} of {reposTotal}
									</span>
								) : null}
							</text>
						</box>
					) : null}

					{/* Activity checklist */}
					{visibleSteps.length > 0 ? (
						<box flexDirection="column" gap={0}>
							{hiddenCount > 0 ? (
								<text>
									<span fg={theme.textDim}>
										  · · ·  {hiddenCount} earlier {hiddenCount === 1 ? "step" : "steps"}
									</span>
								</text>
							) : null}
							{visibleSteps.map((step, i) => {
								const isCurrentStep =
									isRunning && i === visibleSteps.length - 1;
								return (
									<text key={`${step}-${i}`}>
										<span fg={isCurrentStep ? theme.cyan : theme.success}>
											{isCurrentStep ? "▶" : "✓"}
										</span>
										<span
											fg={
												isCurrentStep
													? theme.textPrimary
													: theme.textSecondary
											}
										>
											{"  "}{step}
										</span>
									</text>
								);
							})}
						</box>
					) : (
						<box flexDirection="column" gap={1}>
							<text>
								<span fg={theme.textDim}>
									Preparing pipeline — starting shortly...
								</span>
							</text>
						</box>
					)}
				</box>
			</box>

			{/* Status line */}
			{(readyGate || localError || isCancelling) ? (
				<box
					paddingLeft={2}
					paddingRight={2}
					paddingBottom={1}
					flexDirection="column"
				>
					{readyGate ? (
						<text>
							<span fg={theme.success}>
								✓  Done — press Enter to view your resume.
							</span>
						</text>
					) : null}
					{localError ? (
						<text>
							<span fg={theme.error}>{localError}</span>
						</text>
					) : null}
					{isCancelling ? (
						<text>
							<span fg={theme.warning}>Cancelling pipeline...</span>
						</text>
					) : null}
				</box>
			) : null}
		</box>
	);
}
