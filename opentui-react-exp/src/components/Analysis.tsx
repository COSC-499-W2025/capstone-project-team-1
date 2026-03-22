import { useKeyboard } from "@opentui/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { type AnalysisMode, theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface AnalysisProps {
	onNext?: (target: string) => void;
	analysisMode?: AnalysisMode;
	onComplete?: () => void;
	onBack?: () => void;
}

const stageOrder = ["ANALYZE", "FACTS", "DRAFT", "POLISH"] as const;

const stageLabel: Record<(typeof stageOrder)[number], string> = {
	ANALYZE: "Analyze   -  Read repos",
	FACTS: "Facts     -  Compile evidence",
	DRAFT: "Draft     -  Write resume",
	POLISH: "Polish    -  Apply feedback",
};

const stageContext: Record<
	(typeof stageOrder)[number],
	{ heading: string; lines: string[] }
> = {
	ANALYZE: {
		heading: "Reading and analyzing your repositories locally",
		lines: [
			"We're reading README files, commit messages, folder",
			"structure, dependency graphs, and code metrics for",
			"every repo you selected. Nothing leaves your machine,",
			"and this step is focused on collecting real signals,",
			"not writing resume text yet.",
		],
	},
	FACTS: {
		heading: "Compiling grounded facts and evidence",
		lines: [
			"We're assembling a concise fact set per project from",
			"commits, constructs, tests, and metrics. These facts",
			"act as the grounding layer for drafting so the output",
			"stays tied to what your repos actually contain.",
		],
	},
	DRAFT: {
		heading: "Writing your resume",
		lines: [
			"The AI is now composing project bullets, technical",
			"summaries, and a portfolio overview - all grounded",
			"in the evidence extracted from your code. Output is",
			"structured as clean Markdown ready to export.",
		],
	},
	POLISH: {
		heading: "Polishing based on your feedback",
		lines: [
			"The AI is refining tone, language, and emphasis",
			"using the notes you provided. This pass targets",
			"the specific gaps you flagged in the draft.",
		],
	},
};

const STEP_MAP: Array<[string, string]> = [
	["Extracting README", "Reading project documentation"],
	["Classifying commits", "Analyzing commit history"],
	["Extracting structure", "Mapping project structure"],
	["Extracting code constructs", "Scanning code constructs"],
	["Inferring project type", "Detecting project type"],
	["Extracting git stats", "Gathering git statistics"],
	["Computing test ratio", "Measuring test coverage"],
	["Scoring commit quality", "Scoring commit quality"],
	["Measuring module breadth", "Measuring module breadth"],
	["Computing style metrics", "Analyzing code style"],
	["Computing complexity metrics", "Measuring code complexity"],
	["Computing skill timeline", "Building skill timeline"],
	["Extracting enriched constructs", "Deep code analysis"],
	["Analyzing import graph", "Mapping dependencies"],
	["Extracting config fingerprint", "Reading project configuration"],
	["Inferring project purpose", "AI: Inferring project purpose"],
	["Running project query", "AI: Writing project bullets"],
	["Running portfolio query", "AI: Composing portfolio summary"],
	["Assembling resume", "Assembling resume document"],
];

const NOISE_PREFIXES = [
	"Pipeline request",
	"Phase 1 worker",
	"Pipeline started",
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
	onNext,
	analysisMode = "phase1",
	onComplete,
	onBack,
}: AnalysisProps) {
	const {
		state,
		setPipelineMessages,
		setPipelineNotice,
		setPipelineStage,
		setPipelineStatus,
		setPipelineTelemetry,
		setResumeV3Draft,
		setResumeV3Output,
	} = useAppState();
	const [error, setError] = useState<string | null>(null);
	const [isCancelling, setIsCancelling] = useState(false);
	const handledStatusRef = useRef<string | null>(null);

	const goTo = useCallback(
		(target: string) => {
			onNext?.(target);
			if (!onNext) {
				if (target === "preview") {
					onComplete?.();
				} else {
					onBack?.();
				}
			}
		},
		[onBack, onComplete, onNext],
	);

	useEffect(() => {
		if (!state.pipelineJobId) {
			setError("No active pipeline job.");
			return;
		}

		setError(null);
	}, [state.pipelineJobId]);

	useEffect(() => {
		if (!state.pipelineJobId) {
			setError("No active pipeline job.");
			return;
		}

		let disposed = false;

		const pollStatus = async () => {
			try {
				const response = await api.getPipelineStatus();
				if (disposed) {
					return;
				}

				setPipelineStatus(response.status);
				setPipelineStage(response.stage);
				setPipelineTelemetry(response.telemetry);
				setPipelineMessages(response.messages);
				setResumeV3Draft(response.draft);
				setResumeV3Output(response.output);

				if (
					response.status === "complete" &&
					handledStatusRef.current !== "complete"
				) {
					handledStatusRef.current = "complete";
					goTo("preview");
					return;
				}

				if (
					response.status === "draft_ready" &&
					analysisMode === "phase1" &&
					handledStatusRef.current !== "draft_ready"
				) {
					handledStatusRef.current = "draft_ready";
					goTo("draft-pause");
					return;
				}

				if (
					response.status === "error" ||
					response.status === "cancelled" ||
					response.status === "failed_resource_guard"
				) {
					setError(
						response.error ||
							(response.status === "cancelled"
								? "Pipeline cancelled."
								: response.status === "failed_resource_guard"
									? "Pipeline stopped because of resource limits."
									: "Pipeline failed."),
					);
					return;
				}

				setError(null);
			} catch (pollError) {
				if (!disposed) {
					setError(toErrorMessage(pollError));
				}
			}
		};

		void pollStatus();
		const interval = setInterval(() => {
			void pollStatus();
		}, 2000);

		return () => {
			disposed = true;
			clearInterval(interval);
		};
	}, [
		analysisMode,
		goTo,
		setPipelineMessages,
		setPipelineStage,
		setPipelineStatus,
		setPipelineTelemetry,
		setResumeV3Draft,
		setResumeV3Output,
		state.pipelineJobId,
	]);

	const cancelJob = async () => {
		if (!state.pipelineJobId || isCancelling) {
			return;
		}

		setIsCancelling(true);
		setError(null);
		try {
			await api.cancelPipeline();
			setPipelineStatus("cancelled");
			setPipelineNotice("Pipeline cancelled.");
			setError("Pipeline cancelled.");
		} catch (cancelError) {
			setError(toErrorMessage(cancelError));
		} finally {
			setIsCancelling(false);
		}
	};

	useKeyboard((key) => {
		if (key.name !== "escape") {
			return;
		}

		if (
			state.pipelineStatus === "queued" ||
			state.pipelineStatus === "running" ||
			state.pipelineStatus === "polishing"
		) {
			void cancelJob();
			return;
		}

		if (
			state.pipelineStatus === "error" ||
			state.pipelineStatus === "cancelled" ||
			state.pipelineStatus === "failed_resource_guard"
		) {
			goTo("project-list");
		}
	});

	const telemetry = state.pipelineTelemetry;
	const activeStage = telemetry?.stage || state.pipelineStage || "ANALYZE";
	const activeIndex = stageOrder.indexOf(
		activeStage as (typeof stageOrder)[number],
	);
	const activeStageInfo = stageContext[activeStage as (typeof stageOrder)[number]];

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

				if (completed) {
					marker = "✓";
					color = theme.success;
				} else if (active) {
					marker = "►";
					color = theme.cyan;
				}

				if (state.pipelineStatus === "cancelled") color = theme.warning;
				if (
					(state.pipelineStatus === "error" ||
						state.pipelineStatus === "failed_resource_guard") &&
					active
				) {
					color = theme.error;
				}

				return { stageName, marker, color };
			}),
		[activeIndex, activeStage, state.pipelineStatus],
	);

	const activitySteps = useMemo(() => {
		const steps: string[] = [];
		let previousStep: string | null = null;

		for (const msg of state.pipelineMessages) {
			const friendly = toFriendlyStep(msg);
			if (!friendly || friendly === previousStep) {
				continue;
			}
			steps.push(friendly);
			previousStep = friendly;
		}

		return steps;
	}, [state.pipelineMessages]);

	const MAX_VISIBLE = 16;
	const visibleSteps = activitySteps.slice(-MAX_VISIBLE);
	const hiddenCount = activitySteps.length - visibleSteps.length;
	const isRunning =
		state.pipelineStatus === "running" ||
		state.pipelineStatus === "queued" ||
		state.pipelineStatus === "polishing";

	const statusColor =
		state.pipelineStatus === "running" || state.pipelineStatus === "queued"
			? theme.cyan
			: state.pipelineStatus === "draft_ready"
				? theme.gold
				: state.pipelineStatus === "complete"
					? theme.success
					: state.pipelineStatus === "error" ||
						  state.pipelineStatus === "failed_resource_guard"
						? theme.error
						: state.pipelineStatus === "cancelled"
							? theme.warning
							: theme.textDim;

	const reposDone = telemetry?.repos_done ?? 0;
	const reposTotal = telemetry?.repos_total ?? 0;
	const elapsed = (telemetry?.elapsed_seconds ?? 0).toFixed(1);
	const subtitle =
		analysisMode === "phase1"
			? "Extract + Stage 1 + Stage 2"
			: "Stage 3  -  Polish from draft";

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar step="Pipeline" title="Live Progress" description={subtitle} />

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
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
					{stageRows.map((row) => (
						<text key={row.stageName}>
							<span fg={row.color}>
								{row.marker} {stageLabel[row.stageName]}
							</span>
						</text>
					))}

					<box
						flexDirection="column"
						gap={1}
						border={["top"]}
						borderColor={theme.bgLight}
						paddingTop={1}
						marginTop={1}
					>
						<text>
							<span fg={theme.textDim}>Status </span>
							<span fg={statusColor}>
								<strong>{state.pipelineStatus.toUpperCase()}</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>Elapsed </span>
							<span fg={theme.textSecondary}>{elapsed}s</span>
						</text>
						<text>
							<span fg={theme.textDim}>Model </span>
							<span fg={theme.textSecondary}>
								{telemetry?.active_model
									? telemetry.active_model.length > 18
										? `${telemetry.active_model.slice(0, 18)}...`
										: telemetry.active_model
									: "—"}
							</span>
						</text>
					</box>

					<box
						flexDirection="column"
						gap={1}
						border={["top"]}
						borderColor={theme.bgLight}
						paddingTop={1}
						marginTop={1}
					>
						<text>
							<span fg={theme.textDim}>Repos </span>
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
									{"  "}
									{Math.round((reposDone / reposTotal) * 100)}%
								</span>
							</text>
						) : null}
						{(telemetry?.facts_total ?? 0) > 0 ? (
							<text>
								<span fg={theme.textDim}>Facts </span>
								<span fg={theme.textSecondary}>{telemetry?.facts_total}</span>
							</text>
						) : null}
					</box>

				</box>

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
					{activeStageInfo ? (
						<box
							flexDirection="column"
							gap={1}
							border={["bottom"]}
							borderColor={theme.bgLight}
							paddingBottom={1}
						>
							<text>
								<span fg={theme.gold}>
									<strong>{activeStageInfo.heading}</strong>
								</span>
							</text>
							{activeStageInfo.lines.map((line) => (
								<text key={line}>
									<span fg={theme.textDim}>{line}</span>
								</text>
							))}
						</box>
					) : null}

					{telemetry?.current_repo ? (
						<box
							flexDirection="column"
							gap={1}
							border={["bottom"]}
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
										{"  -  repo "}
										{reposDone + 1} of {reposTotal}
									</span>
								) : null}
							</text>
						</box>
					) : null}

					{visibleSteps.length > 0 ? (
						<box flexDirection="column" gap={0}>
							{hiddenCount > 0 ? (
								<text>
									<span fg={theme.textDim}>
										. . . {hiddenCount} earlier{" "}
										{hiddenCount === 1 ? "step" : "steps"}
									</span>
								</text>
							) : null}
							{visibleSteps.map((step, index) => {
								const isCurrentStep = isRunning && index === visibleSteps.length - 1;

								return (
									<text key={`${index}-${step}`}>
										<span fg={isCurrentStep ? theme.cyan : theme.success}>
											{isCurrentStep ? "►" : "✓"}
										</span>
										<span
											fg={
												isCurrentStep ? theme.textPrimary : theme.textSecondary
											}
										>
											{"  "}
											{step}
										</span>
									</text>
								);
							})}
						</box>
					) : (
						<box flexDirection="column" gap={1}>
							<text>
								<span fg={theme.textDim}>
									Preparing pipeline - starting shortly...
								</span>
							</text>
						</box>
					)}
				</box>
			</box>

			<box
				height={3}
				border
				borderStyle="single"
				borderColor={error ? theme.error : theme.goldDim}
				paddingLeft={2}
				paddingRight={2}
				paddingTop={1}
				paddingBottom={1}
			>
				<text>
					{error ? (
						<span fg={theme.error}>{error}</span>
					) : isCancelling ? (
						<span fg={theme.warning}>Cancelling pipeline...</span>
					) : (
						<>
							<span fg={theme.textDim}>Press </span>
							<span fg={theme.cyan}>Esc</span>
							<span fg={theme.textDim}> to cancel the pipeline</span>
						</>
					)}
				</text>
			</box>
		</box>
	);
}
