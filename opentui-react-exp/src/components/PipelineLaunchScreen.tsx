import { useKeyboard } from "@opentui/react";
import { useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface PipelineLaunchScreenProps {
	onStarted: () => void;
	onBack: () => void;
}

const DEFAULT_STAGE1_MODEL = "qwen2.5-coder-3b-q4";
const DEFAULT_STAGE2_MODEL = "lfm2.5-1.2b-bf16";
const DEFAULT_STAGE3_MODEL = "lfm2.5-1.2b-bf16";

export function PipelineLaunchScreen({
	onStarted,
	onBack,
}: PipelineLaunchScreenProps) {
	const {
		state,
		setPipelineJobId,
		setPipelineMessages,
		setPipelineStatus,
		setPipelineTelemetry,
		setPipelineStage,
		setPipelineNotice,
		resetRunState,
	} = useAppState();

	const [isStarting, setIsStarting] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const selectedRepos = useMemo(
		() =>
			state.detectedRepos.filter((repo) =>
				state.selectedRepoIds.includes(repo.id),
			),
		[state.detectedRepos, state.selectedRepoIds],
	);

	const canStart =
		Boolean(state.intakeId) &&
		Boolean(state.selectedEmail) &&
		state.selectedRepoIds.length > 0;

	const startPipeline = async () => {
		if (!canStart || isStarting || !state.intakeId || !state.selectedEmail) {
			if (!canStart) {
				setError("Missing intake, repo selection, or identity.");
			}
			return;
		}

		setError(null);
		setIsStarting(true);

		try {
			const response = await api.startPipeline({
				intake_id: state.intakeId,
				repo_ids: state.selectedRepoIds,
				user_email: state.selectedEmail,
				stage1_model: DEFAULT_STAGE1_MODEL,
				stage2_model: DEFAULT_STAGE2_MODEL,
				stage3_model: DEFAULT_STAGE3_MODEL,
			});

			resetRunState();
			setPipelineNotice(null);
			setPipelineJobId(response.job_id);
			setPipelineStatus(response.status);
			setPipelineStage("ANALYZE");
			setPipelineTelemetry(null);
			setPipelineMessages(["Pipeline start requested."]);
			onStarted();
		} catch (startError) {
			setError(toErrorMessage(startError));
		} finally {
			setIsStarting(false);
		}
	};

	useKeyboard((key) => {
		if (key.name === "escape" && !isStarting) {
			onBack();
			return;
		}

		if (key.name === "return" || key.name === "enter") {
			void startPipeline();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar title="Launch" />

			<box flexGrow={1} padding={2} justifyContent="center" alignItems="center">
				<box
					width={88}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Pipeline Configuration</strong>
						</span>
					</text>

					<text>
						<span fg={theme.textSecondary}>
							Email: {state.selectedEmail || "(none)"}
						</span>
					</text>
					<text>
						<span fg={theme.textSecondary}>
							Selected repos: {selectedRepos.length}
						</span>
					</text>

					{selectedRepos.slice(0, 8).map((repo) => (
						<text key={repo.id}>
							<span fg={theme.textDim}>- {repo.name}</span>
						</text>
					))}

					<box marginTop={1} flexDirection="column" gap={1}>
						<text>
							<span fg={theme.cyan}>Stage 1 model: {DEFAULT_STAGE1_MODEL}</span>
						</text>
						<text>
							<span fg={theme.cyan}>Stage 2 model: {DEFAULT_STAGE2_MODEL}</span>
						</text>
						<text>
							<span fg={theme.cyan}>Stage 3 model: {DEFAULT_STAGE3_MODEL}</span>
						</text>
					</box>

					<box marginTop={1}>
						<text>
							<span fg={theme.success}>
								Press Enter to start. Nothing starts before this screen.
							</span>
						</text>
					</box>
				</box>
			</box>

			<box
				paddingLeft={2}
				paddingRight={2}
				paddingBottom={1}
				flexDirection="column"
				gap={1}
			>
				{isStarting ? (
					<text>
						<span fg={theme.cyan}>Starting pipeline...</span>
					</text>
				) : null}
				{error ? (
					<text>
						<span fg={theme.error}>{error}</span>
					</text>
				) : null}
			</box>
		</box>
	);
}
