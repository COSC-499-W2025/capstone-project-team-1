import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { type AnalysisMode, theme } from "../types";
import { keyedLines, toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface AnalysisProps {
	mode: AnalysisMode;
	onDraftReady: () => void;
	onReady: () => void;
	onCancelReturn: () => void;
}

const stageOrder = ["EXTRACT", "STAGE_1", "STAGE_2", "STAGE_3"] as const;

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
		if (mode !== "phase1" && mode !== "phase3") {
			return;
		}
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
				if (cancelled) {
					return;
				}

				setPipelineStatus(status.status);
				setPipelineStage(status.stage);
				setPipelineTelemetry(status.telemetry);
				setPipelineMessages(status.messages);
				setResumeV3Draft(status.draft);
				setResumeV3Output(status.output);

				if (status.error) {
					setLocalError(status.error);
				}

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
				if (cancelled) {
					return;
				}
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
		if (!state.pipelineJobId || isCancelling) {
			return;
		}

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
			if (!readyGate) {
				void cancelJob();
			}
			return;
		}

		if ((key.name === "return" || key.name === "enter") && readyGate) {
			onReady();
		}
	});

	const telemetry = state.pipelineTelemetry;
	const keyedMessages = useMemo(
		() => keyedLines(state.pipelineMessages, "log"),
		[state.pipelineMessages],
	);
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

				if (completed) {
					marker = "✓";
					color = theme.success;
				} else if (active) {
					marker = "▶";
					color = theme.cyan;
				}

				if (state.pipelineStatus === "cancelled") {
					color = theme.warning;
				}

				if (state.pipelineStatus === "error" && active) {
					color = theme.error;
				}

				return { stageName, marker, color };
			}),
		[activeIndex, activeStage, state.pipelineStatus],
	);

	const subtitle =
		mode === "phase1"
			? "Extract + Stage 1 + Stage 2"
			: "Stage 3 polish from saved draft";

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Pipeline"
				title="Live Progress"
				description={subtitle}
			/>

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
				<box
					width={44}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Stage Board</strong>
						</span>
					</text>
					{stageRows.map((row) => (
						<text key={row.stageName}>
							<span fg={row.color}>
								{row.marker} {row.stageName.replace("_", " ")}
							</span>
						</text>
					))}

					<box marginTop={1} flexDirection="column" gap={1}>
						<text>
							<span fg={theme.cyan}>
								Status: {state.pipelineStatus.toUpperCase()}
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>
								Model: {telemetry?.active_model || "n/a"}
							</span>
						</text>
					</box>

					<box marginTop={1} flexDirection="column" gap={1}>
						<text>
							<span fg={theme.textDim}>
								Repos: {telemetry?.repos_done || 0}/{telemetry?.repos_total || 0}
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>
								Facts: {telemetry?.facts_total || 0}
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>
								Draft Projects: {telemetry?.draft_projects || 0}
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>
								Polished Projects: {telemetry?.polished_projects || 0}
							</span>
						</text>
						<text>
							<span fg={theme.textDim}>
								Elapsed: {(telemetry?.elapsed_seconds || 0).toFixed(1)}s
							</span>
						</text>
					</box>
				</box>

				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.cyanDim}
					padding={1}
					flexDirection="column"
				>
					<text>
						<span fg={theme.gold}>
							<strong>Live Logs</strong>
						</span>
					</text>

					<scrollbox
						focused
						style={{
							rootOptions: { flexGrow: 1, backgroundColor: theme.bgDark },
							wrapperOptions: { flexGrow: 1, marginTop: 1 },
							viewportOptions: { paddingLeft: 1, paddingRight: 1 },
						}}
					>
						{keyedMessages.length ? (
							keyedMessages.map((line) => (
								<text key={line.key}>
									<span fg={theme.textSecondary}>{line.text}</span>
								</text>
							))
						) : (
							<text>
								<span fg={theme.textDim}>Waiting for pipeline logs...</span>
							</text>
						)}
					</scrollbox>
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column" gap={1}>
				{telemetry?.current_repo ? (
					<text>
						<span fg={theme.cyan}>Current repo: {telemetry.current_repo}</span>
					</text>
				) : null}

				{readyGate ? (
					<text>
						<span fg={theme.success}>
							READY. Press Enter to continue to resume preview.
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
		</box>
	);
}
