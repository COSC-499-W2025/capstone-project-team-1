import { useKeyboard } from "@opentui/react";
import { useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { keyedLines, resumeToLines, toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface DraftPauseScreenProps {
	onContinue: () => void;
	onCancelReturn: () => void;
}

export function DraftPauseScreen({
	onContinue,
	onCancelReturn,
}: DraftPauseScreenProps) {
	const { state, setPipelineNotice, setPipelineStatus } = useAppState();
	const [isCancelling, setIsCancelling] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const draftLines = useMemo(() => resumeToLines(state.resumeV3Draft), [state.resumeV3Draft]);
	const keyedDraftLines = useMemo(() => keyedLines(draftLines, "draft"), [draftLines]);

	const cancelJob = async () => {
		if (!state.pipelineJobId || isCancelling) {
			return;
		}
		setIsCancelling(true);
		setError(null);
		try {
			await api.cancelPipeline(state.pipelineJobId);
			setPipelineStatus("cancelled");
			setPipelineNotice("Pipeline cancelled at draft pause.");
			onCancelReturn();
		} catch (cancelError) {
			setError(toErrorMessage(cancelError));
		} finally {
			setIsCancelling(false);
		}
	};

	useKeyboard((key) => {
		if (key.name === "escape") {
			void cancelJob();
			return;
		}

		if (key.name === "return" || key.name === "enter") {
			onContinue();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Draft"
				title="Stage 2 Pause"
				description="Review the full draft before feedback and Stage 3"
			/>

			<box flexGrow={1} padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={1}
				>
					<scrollbox
						focused
						style={{
							rootOptions: { flexGrow: 1, backgroundColor: theme.bgDark },
							wrapperOptions: { flexGrow: 1 },
							viewportOptions: { paddingLeft: 1, paddingRight: 1 },
						}}
					>
						{keyedDraftLines.map((line) => (
							<text key={line.key}>
								<span fg={theme.textSecondary}>{line.text || " "}</span>
							</text>
						))}
					</scrollbox>
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column" gap={1}>
				<text>
					<span fg={theme.success}>Press Enter to proceed to Feedback.</span>
				</text>
				<text>
					<span fg={theme.warning}>Press Esc to cancel the job immediately.</span>
				</text>
				{isCancelling ? (
					<text>
						<span fg={theme.warning}>Cancelling pipeline...</span>
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
