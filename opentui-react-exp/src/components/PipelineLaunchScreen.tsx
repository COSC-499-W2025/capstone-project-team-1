import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/endpoints";
import type { LocalLlmSetupResponse } from "../api/types";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface PipelineLaunchScreenProps {
	onStarted: () => void;
	onBack: () => void;
}

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
	const [setup, setSetup] = useState<LocalLlmSetupResponse | null>(null);
	const [setupError, setSetupError] = useState<string | null>(null);
	const [isLoadingSetup, setIsLoadingSetup] = useState(true);

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
	const setupBlocked =
		setup !== null &&
		(!setup.llama_server_found || !setup.selected_default_model);
	const preferredModel =
		setup?.supported_models.find(
			(model) => model.name === setup.preferred_default_model,
		) ?? null;

	useEffect(() => {
		let ignore = false;

		setIsLoadingSetup(true);
		setSetupError(null);

		api
			.getLocalLlmSetup()
			.then((response) => {
				if (!ignore) {
					setSetup(response);
				}
			})
			.catch((loadError) => {
				if (!ignore) {
					setSetupError(toErrorMessage(loadError));
				}
			})
			.finally(() => {
				if (!ignore) {
					setIsLoadingSetup(false);
				}
			});

		return () => {
			ignore = true;
		};
	}, []);

	const startPipeline = async () => {
		if (!canStart || isStarting || !state.intakeId || !state.selectedEmail) {
			if (!canStart) {
				setError("Missing intake, repo selection, or identity.");
			}
			return;
		}
		if (isLoadingSetup) {
			setError("Still checking local model setup. Try again in a moment.");
			return;
		}
		if (setupBlocked) {
			if (setup && !setup.llama_server_found) {
				setError("llama-server is not on PATH. Install llama.cpp first.");
				return;
			}
			if (setup && !setup.selected_default_model) {
				const missingFile =
					preferredModel?.filename ??
					"qwen2.5-coder-3b-instruct-q4_k_m.gguf";
				setError(
					`No supported local model found in ~/.artifactminer/models. Expected ${missingFile}.`,
				);
				return;
			}
		}

		setError(null);
		setIsStarting(true);

		try {
			const response = await api.startPipeline({
				intake_id: state.intakeId,
				repo_ids: state.selectedRepoIds,
				user_email: state.selectedEmail,
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
						{isLoadingSetup ? (
							<text>
								<span fg={theme.cyan}>Checking local model setup...</span>
							</text>
						) : null}
						{setup ? (
							<>
								<text>
									<span
										fg={
											setup.selected_default_model
												? theme.success
												: theme.warning
										}
									>
										{setup.selected_default_model
											? `Detected model: ${setup.selected_default_model}`
											: "No supported local model detected"}
									</span>
								</text>
								<text>
									<span
										fg={
											setup.llama_server_found ? theme.success : theme.warning
										}
									>
										{setup.llama_server_found
											? "llama-server found on PATH"
											: "llama-server missing from PATH"}
									</span>
								</text>
								<text>
									<span fg={theme.textDim}>Models dir: {setup.models_dir}</span>
								</text>
								{!setup.selected_default_model && preferredModel?.filename ? (
									<text>
										<span fg={theme.warning}>
											Install {preferredModel.filename} into ~/.artifactminer/models
										</span>
									</text>
								) : null}
							</>
						) : null}
						{setupError ? (
							<text>
								<span fg={theme.warning}>
									Could not load setup status: {setupError}
								</span>
							</text>
						) : null}
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
