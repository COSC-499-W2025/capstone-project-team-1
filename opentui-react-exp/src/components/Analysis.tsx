import { useKeyboard } from "@opentui/react";
import { useEffect, useRef, useState } from "react";
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

const steps = [
	{ id: "analyze", label: "Analyze repositories" },
	{ id: "facts", label: "Compile technical facts" },
	{ id: "draft", label: "Generate draft resume" },
	{ id: "polish", label: "Apply final polish" },
];

const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

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
	const [currentStep, setCurrentStep] = useState(0);
	const [spinnerIndex, setSpinnerIndex] = useState(0);
	const [progress, setProgress] = useState(0);
	const [logs, setLogs] = useState<string[]>([]);
	const [error, setError] = useState<string | null>(null);
	const [isCancelling, setIsCancelling] = useState(false);
	const handledStatusRef = useRef<string | null>(null);

	const goTo = (target: string) => {
		onNext?.(target);
		if (!onNext) {
			if (target === "preview") {
				onComplete?.();
			} else {
				onBack?.();
			}
		}
	};

	useEffect(() => {
		const interval = setInterval(() => {
			setSpinnerIndex((i: number) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, []);

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
				setLogs(response.messages.slice(-3));

				const stageIndex =
					response.stage === "FACTS"
						? 1
						: response.stage === "DRAFT"
							? 2
							: response.stage === "POLISH"
								? 3
								: 0;

				setCurrentStep(response.status === "complete" ? steps.length : stageIndex);

				if (response.status === "complete") {
					setProgress(100);
				} else if (response.status === "draft_ready") {
					setProgress(75);
				} else if (
					response.status === "error" ||
					response.status === "cancelled" ||
					response.status === "failed_resource_guard"
				) {
					setProgress(0);
				} else {
					const repoRatio =
						(response.telemetry.repos_total ?? 0) > 0
							? response.telemetry.repos_done / response.telemetry.repos_total
							: 0;

					setProgress(
						stageIndex === 0
							? Math.round(repoRatio * 25)
							: stageIndex === 1
								? 25 + Math.round(repoRatio * 25)
								: stageIndex === 2
									? analysisMode === "phase3"
										? 75
										: 70
									: 90,
					);
				}

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
		onNext,
		onBack,
		onComplete,
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
			const response = await api.cancelPipeline();
			setPipelineStatus(response.status);
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

	const progressBarWidth = 50;
	const filledWidth = Math.round((progress / 100) * progressBarWidth);
	const progressBar =
		"█".repeat(filledWidth) + "░".repeat(progressBarWidth - filledWidth);

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 3"
				title="Analysis"
				description="Mining artifacts and generating insights..."
			/>

			<box
				flexGrow={1}
				flexDirection="column"
				alignItems="center"
				justifyContent="center"
				gap={3}
			>
				<box
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					width={50}
				>
					{steps.map((step, index) => {
						const isCompleted = index < currentStep;
						const isCurrent =
							index === currentStep &&
							!error &&
							state.pipelineStatus !== "cancelled";

						return (
							<box key={step.id} flexDirection="row" gap={2}>
								<text>
									{isCompleted ? (
										<span fg={theme.success}>✓</span>
									) : isCurrent ? (
										<span fg={theme.cyan}>{spinnerFrames[spinnerIndex]}</span>
									) : (
										<span fg={theme.textDim}>○</span>
									)}
								</text>
								<text>
									<span
										fg={
											isCompleted
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

				<box flexDirection="column" alignItems="center" gap={1}>
					<text>
						<span fg={theme.gold}>{progressBar}</span>
					</text>
					<text>
						<span fg={theme.textPrimary}>
							<strong>{progress}%</strong>
						</span>
						<span fg={theme.textDim}> complete</span>
					</text>
				</box>

				{logs.length ? (
					<box
						flexDirection="column"
						width={60}
						backgroundColor={theme.bgMedium}
						padding={1}
						border
						borderStyle="single"
						borderColor={theme.textDim}
					>
						<text>
							<span fg={theme.textDim}>
								<strong>Status</strong>
							</span>
						</text>
						{logs.map((log: string, i: number) => (
							<text key={`${i}-${log}`}>
								<span fg={theme.textDim}>{log}</span>
							</text>
						))}
					</box>
				) : null}
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
