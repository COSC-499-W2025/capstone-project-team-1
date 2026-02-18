import { useKeyboard } from "@opentui/react";
import { useMemo, useState } from "react";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { buildLineDiff, keyedLines, resumeToLines } from "../utils";
import { TopBar } from "./TopBar";

interface ResumePreviewProps {
	onPolishAgain: () => void;
	onRestart: () => void;
	onExit: () => void;
}

type PreviewMode = "draft" | "final" | "diff";

const modeOrder: PreviewMode[] = ["draft", "final", "diff"];

export function ResumePreview({
	onPolishAgain,
	onRestart,
	onExit,
}: ResumePreviewProps) {
	const { state } = useAppState();
	const [mode, setMode] = useState<PreviewMode>(
		state.resumeV3Output ? "final" : "draft",
	);

	const draftLines = useMemo(() => resumeToLines(state.resumeV3Draft), [state.resumeV3Draft]);
	const finalLines = useMemo(() => resumeToLines(state.resumeV3Output), [state.resumeV3Output]);
	const keyedDraft = useMemo(() => keyedLines(draftLines, "preview-draft"), [draftLines]);
	const keyedFinal = useMemo(() => keyedLines(finalLines, "preview-final"), [finalLines]);
	const diffRows = useMemo(
		() => buildLineDiff(state.resumeV3Draft, state.resumeV3Output),
		[state.resumeV3Draft, state.resumeV3Output],
	);

	const cycleMode = () => {
		setMode((prev) => {
			const index = modeOrder.indexOf(prev);
			return modeOrder[(index + 1) % modeOrder.length] || "draft";
		});
	};

	useKeyboard((key) => {
		if (key.name === "tab") {
			cycleMode();
			return;
		}

		if (key.name === "p") {
			onPolishAgain();
			return;
		}

		if (key.name === "r") {
			onRestart();
			return;
		}

		if (key.name === "escape") {
			onExit();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Preview"
				title="Draft / Final / Diff"
				description={`Current mode: ${mode.toUpperCase()}`}
			/>

			<box flexGrow={1} padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={1}
				>
					{mode === "draft" ? (
						<SinglePane title="Draft" lines={keyedDraft} color={theme.cyan} />
					) : null}

					{mode === "final" ? (
						<SinglePane title="Final" lines={keyedFinal} color={theme.success} />
					) : null}

					{mode === "diff" ? <DiffPane rows={diffRows} /> : null}
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column" gap={1}>
				<text>
					<span fg={theme.textDim}>
						Tab switches mode. P polish again. R restart flow. Esc exit.
					</span>
				</text>
			</box>
		</box>
	);
}

interface SinglePaneProps {
	title: string;
	lines: { key: string; text: string }[];
	color: string;
}

function SinglePane({ title, lines, color }: SinglePaneProps) {
	return (
		<box flexGrow={1} flexDirection="column">
			<text>
				<span fg={color}>
					<strong>{title}</strong>
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
				{lines.map((line) => (
					<text key={line.key}>
						<span fg={theme.textSecondary}>{line.text || " "}</span>
					</text>
				))}
			</scrollbox>
		</box>
	);
}

interface DiffPaneProps {
	rows: ReturnType<typeof buildLineDiff>;
}

function DiffPane({ rows }: DiffPaneProps) {
	return (
		<box flexGrow={1} flexDirection="column" gap={1}>
			<box flexDirection="row" justifyContent="space-between">
				<text>
					<span fg={theme.cyan}>
						<strong>Draft</strong>
					</span>
				</text>
				<text>
					<span fg={theme.success}>
						<strong>Final</strong>
					</span>
				</text>
			</box>

			<scrollbox
				focused
				style={{
					rootOptions: { flexGrow: 1, backgroundColor: theme.bgDark },
					wrapperOptions: { flexGrow: 1 },
					viewportOptions: { paddingLeft: 1, paddingRight: 1 },
				}}
			>
				{rows.map((row) => (
					<box key={row.lineNumber} flexDirection="row" gap={1}>
						<box width={4}>
							<text>
								<span fg={theme.textDim}>{String(row.lineNumber).padStart(3, " ")}</span>
							</text>
						</box>

						<box width={50}>
							<text>
								<span fg={row.changed ? theme.warning : theme.textSecondary}>
									{clipLine(row.left)}
								</span>
							</text>
						</box>

						<box width={50}>
							<text>
								<span fg={row.changed ? theme.success : theme.textSecondary}>
									{clipLine(row.right)}
								</span>
							</text>
						</box>
					</box>
				))}
			</scrollbox>
		</box>
	);
}

function clipLine(line: string): string {
	if (line.length <= 48) {
		return line || " ";
	}
	return `${line.slice(0, 45)}...`;
}
