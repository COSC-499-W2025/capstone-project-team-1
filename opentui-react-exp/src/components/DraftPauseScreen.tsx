import { useKeyboard } from "@opentui/react";
import { useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { resumeToSections, toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface DraftPauseScreenProps {
	onSubmitted: () => void;
	onCancelReturn: () => void;
}

function parseList(value: string): string[] {
	return value
		.split(",")
		.map((item) => item.trim())
		.filter(Boolean);
}

export function DraftPauseScreen({
	onSubmitted,
	onCancelReturn,
}: DraftPauseScreenProps) {
	const { state, setPipelineNotice, setPipelineStatus } = useAppState();
	const [selectedSection, setSelectedSection] = useState(0);
	const [focusedField, setFocusedField] = useState(-1); // -1 = TOC mode, 0-3 = feedback field
	const [generalNotes, setGeneralNotes] = useState("");
	const [tone, setTone] = useState("");
	const [additionsText, setAdditionsText] = useState("");
	const [removalsText, setRemovalsText] = useState("");
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [isCancelling, setIsCancelling] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const sections = useMemo(
		() => resumeToSections(state.resumeV3Draft),
		[state.resumeV3Draft],
	);

	const submitFeedback = async () => {
		if (!state.pipelineJobId || isSubmitting) return;
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
		if (!state.pipelineJobId || isCancelling) return;
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
			void submitFeedback();
			return;
		}

		if (key.name === "tab") {
			if (key.shift) {
				setFocusedField((f) => (f <= 0 ? -1 : f - 1));
			} else {
				setFocusedField((f) => (f === -1 ? 0 : (f + 1) % 4));
			}
			return;
		}

		// TOC navigation — only active when no feedback field is focused
		if (focusedField === -1) {
			if (key.name === "up") {
				setSelectedSection((s) => Math.max(0, s - 1));
				return;
			}
			if (key.name === "down") {
				setSelectedSection((s) => Math.min(sections.length - 1, s + 1));
				return;
			}
		}
	});

	const current = sections[selectedSection] ?? sections[0]!;

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Draft"
				title="Stage 2 Pause"
				description="Review draft and add feedback, then submit for Stage 3"
			/>

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
				{/* Column 1: Section TOC */}
				<box
					width={22}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					title="  Sections  "
					titleAlignment="center"
					padding={1}
					gap={1}
				>
					{sections.map((section, i) => (
						<text key={section.id}>
							<span fg={i === selectedSection ? theme.gold : theme.textSecondary}>
								{i === selectedSection ? "▶ " : "  "}{section.tocLabel}
							</span>
						</text>
					))}
				</box>

				{/* Column 2: Section content */}
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					title={`  ${current.headerText}  `}
					titleAlignment="center"
					padding={1}
				>
					<scrollbox
						key={current.id}
						style={{
							rootOptions: { flexGrow: 1, backgroundColor: theme.bgDark },
							wrapperOptions: { flexGrow: 1 },
							viewportOptions: { paddingLeft: 1, paddingRight: 1 },
						}}
					>
						{current.lines.map((line, i) => (
							<text key={`${current.id}-${i}`}>
								<span fg={theme.textSecondary}>{line || " "}</span>
							</text>
						))}
					</scrollbox>
				</box>

				{/* Column 3: Feedback form */}
				<box
					width={54}
					border
					borderStyle="rounded"
					borderColor={theme.cyanDim}
					title="  Feedback  "
					titleAlignment="center"
					padding={2}
					gap={1}
				>
					<LabelledInput
						label="General Notes"
						value={generalNotes}
						onChange={setGeneralNotes}
						focused={focusedField === 0}
						placeholder="e.g. emphasize backend impact"
					/>

					<LabelledInput
						label="Tone"
						value={tone}
						onChange={setTone}
						focused={focusedField === 1}
						placeholder="e.g. more technical"
					/>

					<LabelledInput
						label="Additions (comma-separated)"
						value={additionsText}
						onChange={setAdditionsText}
						focused={focusedField === 2}
						placeholder="e.g. deployed to production"
					/>

					<LabelledInput
						label="Removals (comma-separated)"
						value={removalsText}
						onChange={setRemovalsText}
						focused={focusedField === 3}
						placeholder="e.g. inaccurate ML claim"
					/>

					<text>
						<span fg={theme.textDim}>
							Tab cycles fields · Enter submits · Esc cancels
						</span>
					</text>
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column" gap={0}>
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
				width={48}
			/>
		</box>
	);
}
