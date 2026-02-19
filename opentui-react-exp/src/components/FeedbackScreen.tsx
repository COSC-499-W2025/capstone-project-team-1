import { useKeyboard } from "@opentui/react";
import { useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { keyedLines, resumeToLines, toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface FeedbackScreenProps {
	onSubmitted: () => void;
	onCancelReturn: () => void;
}

function parseList(value: string): string[] {
	return value
		.split(",")
		.map((item) => item.trim())
		.filter(Boolean);
}

export function FeedbackScreen({
	onSubmitted,
	onCancelReturn,
}: FeedbackScreenProps) {
	const { state, setPipelineNotice, setPipelineStatus } = useAppState();
	const [focusIndex, setFocusIndex] = useState(0);
	const [generalNotes, setGeneralNotes] = useState("");
	const [tone, setTone] = useState("");
	const [additionsText, setAdditionsText] = useState("");
	const [removalsText, setRemovalsText] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [isCancelling, setIsCancelling] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const draftLines = useMemo(() => resumeToLines(state.resumeV3Draft), [state.resumeV3Draft]);
	const keyedDraftLines = useMemo(() => keyedLines(draftLines, "feedback-draft"), [draftLines]);

	const submitFeedback = async () => {
		if (!state.pipelineJobId || isSubmitting) {
			return;
		}

		setError(null);
		setIsSubmitting(true);
		try {
			await api.polishPipeline(state.pipelineJobId, {
				general_notes: generalNotes.trim(),
				tone: tone.trim(),
				additions: parseList(additionsText),
				removals: parseList(removalsText),
			});
			onSubmitted();
		} catch (submitError) {
			setError(toErrorMessage(submitError));
		} finally {
			setIsSubmitting(false);
		}
	};

	const cancelJob = async () => {
		if (!state.pipelineJobId || isCancelling) {
			return;
		}
		setIsCancelling(true);
		setError(null);
		try {
			await api.cancelPipeline(state.pipelineJobId);
			setPipelineStatus("cancelled");
			setPipelineNotice("Pipeline cancelled from feedback screen.");
			onCancelReturn();
		} catch (cancelError) {
			setError(toErrorMessage(cancelError));
		} finally {
			setIsCancelling(false);
		}
	};

	useKeyboard((key) => {
		if (key.name === "tab") {
			if (key.shift) {
				setFocusIndex((prev) => (prev + 3) % 4);
			} else {
				setFocusIndex((prev) => (prev + 1) % 4);
			}
			return;
		}

		if (key.name === "escape") {
			void cancelJob();
			return;
		}

		if (key.name === "return" || key.name === "enter") {
			void submitFeedback();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Feedback"
				title="Refine Before Stage 3"
				description="Set tone and notes, then run local polish"
			/>

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.cyanDim}
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Draft Preview</strong>
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
						{keyedDraftLines.map((line) => (
							<text key={line.key}>
								<span fg={theme.textSecondary}>{line.text || " "}</span>
							</text>
						))}
					</scrollbox>
				</box>

				<box
					width={56}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Feedback Inputs</strong>
						</span>
					</text>

					<LabelledInput
						label="General Notes"
						value={generalNotes}
						onChange={setGeneralNotes}
						focused={focusIndex === 0}
						placeholder="e.g. emphasize backend impact"
					/>

					<LabelledInput
						label="Tone"
						value={tone}
						onChange={setTone}
						focused={focusIndex === 1}
						placeholder="e.g. more technical"
					/>

					<LabelledInput
						label="Additions (comma-separated)"
						value={additionsText}
						onChange={setAdditionsText}
						focused={focusIndex === 2}
						placeholder="e.g. deployed to production, mentored team"
					/>

					<LabelledInput
						label="Removals (comma-separated)"
						value={removalsText}
						onChange={setRemovalsText}
						focused={focusIndex === 3}
						placeholder="e.g. inaccurate ML claim"
					/>

					<text>
						<span fg={theme.textDim}>
							Tab cycles fields, Enter submits polish, Esc cancels job.
						</span>
					</text>
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column" gap={1}>
				{isSubmitting ? (
					<text>
						<span fg={theme.cyan}>Submitting feedback and starting Stage 3...</span>
					</text>
				) : null}
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

interface LabelledInputProps {
	label: string;
	value: string;
	onChange: (value: string) => void;
	focused: boolean;
	placeholder: string;
}

function LabelledInput({
	label,
	value,
	onChange,
	focused,
	placeholder,
}: LabelledInputProps) {
	return (
		<box flexDirection="column" gap={0}>
			<text>
				<span fg={focused ? theme.cyan : theme.textDim}>{label}</span>
			</text>
			<input
				value={value}
				onChange={onChange}
				focused={focused}
				placeholder={placeholder}
				width={50}
			/>
		</box>
	);
}
