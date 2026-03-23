import { useKeyboard } from "@opentui/react";
import { useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { resumeToSections, toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface DraftPauseScreenProps {
	onNext: (target: string) => void;
}

function parseList(value: string): string[] {
	return value
		.split(",")
		.map((item) => item.trim())
		.filter(Boolean);
}

function getSectionShortcutIndex(
	key: { name: string; sequence?: string },
	sectionCount: number,
): number | null {
	const shortcutText = key.sequence ?? key.name;
	if (!/^[1-9]$/.test(shortcutText)) {
		return null;
	}

	const shortcutIndex = Number(shortcutText) - 1;
	return shortcutIndex < sectionCount ? shortcutIndex : null;
}

export function DraftPauseScreen({ onNext }: DraftPauseScreenProps) {
	const { state, setPipelineNotice, setPipelineStatus } = useAppState();
	const [selectedSection, setSelectedSection] = useState(0);
	const [focusArea, setFocusArea] = useState<"content" | "feedback">("content");
	const [focusedField, setFocusedField] = useState(0);
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
		if (!state.pipelineJobId) {
			setError("No active pipeline job.");
			return;
		}
		if (isSubmitting || isCancelling) {
			return;
		}

		setError(null);
		setIsSubmitting(true);
		try {
			await api.polishPipeline({
				general_notes: generalNotes.trim(),
				tone: tone.trim(),
				additions: parseList(additionsText),
				removals: parseList(removalsText),
			});
			onNext("analysis");
		} catch (submitError) {
			setError(toErrorMessage(submitError));
		} finally {
			setIsSubmitting(false);
		}
	};

	const cancelJob = async () => {
		if (!state.pipelineJobId) {
			setError("No active pipeline job to cancel.");
			return;
		}
		if (isCancelling || isSubmitting) {
			return;
		}

		setIsCancelling(true);
		setError(null);
		try {
			await api.cancelPipeline();
			setPipelineStatus("cancelled");
			setPipelineNotice("Pipeline cancelled at draft pause.");
			onNext("project-list");
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
			setFocusArea((prev) => (prev === "content" ? "feedback" : "content"));
			return;
		}

		if (focusArea === "content") {
			if (key.name === "up") {
				setSelectedSection((prev) => Math.max(0, prev - 1));
				return;
			}
			if (key.name === "down") {
				setSelectedSection((prev) => Math.min(sections.length - 1, prev + 1));
				return;
			}

			const shortcutIndex = getSectionShortcutIndex(key, sections.length);
			if (shortcutIndex !== null) {
				setSelectedSection(shortcutIndex);
			}
			return;
		}

		if (key.name === "up") {
			setFocusedField((prev) => (prev + 3) % 4);
			return;
		}
		if (key.name === "down") {
			setFocusedField((prev) => (prev + 1) % 4);
		}
	});

	const current = sections[selectedSection] ??
		sections[0] ?? {
			id: "empty",
			headerText: "",
			tocLabel: "",
			lines: [],
		};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Draft"
				title="Stage 2 Pause"
				description="Review the draft, add feedback, then submit for polish"
			/>

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
				<box
					width={22}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={focusArea === "content" ? theme.gold : theme.goldDim}
					title="  Sections  "
					titleAlignment="center"
					padding={1}
					gap={1}
				>
					{sections.map((section, index) => (
						<text key={section.id}>
							<span
								fg={
									index === selectedSection ? theme.gold : theme.textSecondary
								}
							>
								{index === selectedSection ? "▶ " : "  "}
								{index + 1}. {section.tocLabel}
							</span>
						</text>
					))}
				</box>

				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={focusArea === "content" ? theme.gold : theme.goldDim}
					title={`  ${current.headerText}  `}
					titleAlignment="center"
					padding={1}
				>
					<scrollbox
						focused={focusArea === "content"}
						key={current.id}
						style={{
							rootOptions: { flexGrow: 1, backgroundColor: theme.bgDark },
							wrapperOptions: { flexGrow: 1 },
							viewportOptions: { paddingLeft: 1, paddingRight: 1 },
						}}
					>
						{current.lines.map((line, index) => (
							<text key={`${current.id}-${index}`}>
								<span fg={theme.textSecondary}>{line || " "}</span>
							</text>
						))}
					</scrollbox>
				</box>

				<box
					width={54}
					border
					borderStyle="rounded"
					borderColor={focusArea === "feedback" ? theme.cyan : theme.cyanDim}
					title="  Feedback  "
					titleAlignment="center"
					padding={2}
					gap={1}
				>
					<LabelledInput
						label="General Notes"
						value={generalNotes}
						onChange={setGeneralNotes}
						focused={focusArea === "feedback" && focusedField === 0}
						placeholder="e.g. emphasize backend impact"
					/>

					<LabelledInput
						label="Tone"
						value={tone}
						onChange={setTone}
						focused={focusArea === "feedback" && focusedField === 1}
						placeholder="e.g. more technical"
					/>

					<LabelledInput
						label="Additions (comma-separated)"
						value={additionsText}
						onChange={setAdditionsText}
						focused={focusArea === "feedback" && focusedField === 2}
						placeholder="e.g. deployed to production"
					/>

					<LabelledInput
						label="Removals (comma-separated)"
						value={removalsText}
						onChange={setRemovalsText}
						focused={focusArea === "feedback" && focusedField === 3}
						placeholder="e.g. inaccurate ML claim"
					/>

					<text>
						<span fg={theme.textDim}>
							Tab toggles panes · 1-9 jumps sections · ↑/↓ navigates · Enter
							submits · Esc cancels
						</span>
					</text>
				</box>
			</box>

			<box
				paddingLeft={2}
				paddingRight={2}
				paddingBottom={1}
				flexDirection="column"
				gap={1}
			>
				{isSubmitting ? (
					<text>
						<span fg={theme.cyan}>
							Submitting feedback and starting Stage 3...
						</span>
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
