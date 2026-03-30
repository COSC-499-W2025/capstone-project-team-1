import { useKeyboard } from "@opentui/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import type { ResumeSection, StatLine } from "../utils";
import {
	createUnifiedDiff,
	resumeStats,
	resumeToSections,
	resumeToText,
} from "../utils";
import { TopBar } from "./TopBar";

interface ResumePreviewProps {
	onPolishAgain?: () => void;
	onRestart: () => void;
	onExit?: () => void;
	onBack?: () => void;
	data?: unknown;
}

type PreviewMode = "draft" | "final" | "diff";

const modeOrder: PreviewMode[] = ["draft", "final", "diff"];

export function ResumePreview({
	onPolishAgain,
	onRestart,
	onExit,
	onBack,
}: ResumePreviewProps) {
	const { state } = useAppState();
	const [mode, setMode] = useState<PreviewMode>(
		state.resumeV3Output ? "final" : "draft",
	);
	const [selectedSection, setSelectedSection] = useState(0);
	const [saveMessage, setSaveMessage] = useState<string | null>(null);

	const activeData =
		mode === "draft" ? state.resumeV3Draft : state.resumeV3Output;
	const sections = useMemo(() => resumeToSections(activeData), [activeData]);
	const stats = useMemo(() => resumeStats(activeData), [activeData]);

	const draftText = useMemo(
		() => resumeToText(state.resumeV3Draft),
		[state.resumeV3Draft],
	);
	const finalText = useMemo(
		() => resumeToText(state.resumeV3Output),
		[state.resumeV3Output],
	);

	const handlePolishAgain = onPolishAgain ?? onBack;
	const handleExit = onExit ?? onBack;

	const cycleMode = useCallback(() => {
		setMode((prev) => {
			const index = modeOrder.indexOf(prev);
			return modeOrder[(index + 1) % modeOrder.length] || "draft";
		});
	}, []);

	const saveResume = useCallback(async () => {
		const data = state.resumeV3Output ?? state.resumeV3Draft;
		const text = resumeToText(data);
		try {
			await Bun.write("./artifact-miner-resume.md", text);
			setSaveMessage("Saved to ./artifact-miner-resume.md");
		} catch {
			setSaveMessage("Failed to save file");
		}
	}, [state.resumeV3Output, state.resumeV3Draft]);

	useEffect(() => {
		if (!saveMessage) {
			return;
		}

		const timer = setTimeout(() => setSaveMessage(null), 3000);
		return () => clearTimeout(timer);
	}, [saveMessage]);

	useKeyboard((key) => {
		if (key.name === "tab") {
			cycleMode();
			return;
		}

		if (mode !== "diff") {
			if (key.name === "up") {
				setSelectedSection((sectionIndex) => Math.max(0, sectionIndex - 1));
				return;
			}

			if (key.name === "down") {
				setSelectedSection((sectionIndex) =>
					Math.min(sections.length - 1, sectionIndex + 1),
				);
				return;
			}

			const sectionNumber = Number(key.name);
			if (
				Number.isInteger(sectionNumber) &&
				sectionNumber >= 1 &&
				sectionNumber <= 5 &&
				sectionNumber <= sections.length
			) {
				setSelectedSection(sectionNumber - 1);
				return;
			}
		}

		if (key.name === "s") {
			void saveResume();
			return;
		}

		if (key.name === "p") {
			handlePolishAgain?.();
			return;
		}

		if (key.name === "r") {
			onRestart();
			return;
		}

		if (key.name === "escape") {
			handleExit?.();
		}
	});

	const current =
		sections[selectedSection] ??
		sections[0] ?? {
			id: "empty",
			headerText: "",
			tocLabel: "",
			lines: [],
		};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar step="Preview" title="Resume" />

			<ModeTabBar mode={mode} />

			<box flexGrow={1} padding={1} paddingTop={0}>
				{mode === "diff" ? (
					<DiffView draftText={draftText} finalText={finalText} />
				) : (
					<box flexGrow={1} flexDirection="row" gap={1}>
						<SectionNav
							sections={sections}
							selectedIndex={selectedSection}
							stats={stats}
						/>
						<SectionContent section={current} />
					</box>
				)}
			</box>

			{saveMessage ? (
				<box paddingLeft={2} paddingBottom={1}>
					<text>
						<span fg={theme.success}>{saveMessage}</span>
					</text>
				</box>
			) : null}
		</box>
	);
}

function ModeTabBar({ mode }: { mode: PreviewMode }) {
	return (
		<box
			flexDirection="row"
			justifyContent="center"
			gap={2}
			paddingTop={1}
			paddingBottom={1}
		>
			{modeOrder.map((entryMode) => (
				<box
					key={entryMode}
					paddingLeft={1}
					paddingRight={1}
					backgroundColor={entryMode === mode ? theme.goldDim : undefined}
				>
					<text>
						<span fg={entryMode === mode ? theme.gold : theme.textDim}>
							{entryMode === mode ? (
								<strong>
									{entryMode.charAt(0).toUpperCase() + entryMode.slice(1)}
								</strong>
							) : (
								entryMode.charAt(0).toUpperCase() + entryMode.slice(1)
							)}
						</span>
					</text>
				</box>
			))}
		</box>
	);
}

interface SectionNavProps {
	sections: ResumeSection[];
	selectedIndex: number;
	stats: StatLine[];
}

function SectionNav({ sections, selectedIndex, stats }: SectionNavProps) {
	return (
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
			{sections.map((section, index) => (
				<text key={section.id}>
					<span fg={index === selectedIndex ? theme.gold : theme.textSecondary}>
						{index === selectedIndex
							? `▶ ${section.tocLabel}`
							: `  ${section.tocLabel}`}
					</span>
				</text>
			))}

			{stats.length > 0 ? (
				<>
					<text>
						<span fg={theme.goldDim}>{"─".repeat(18)}</span>
					</text>
					{stats.map((stat) => (
						<text key={stat.label}>
							<span fg={theme.textDim}>{stat.label}: </span>
							<span fg={theme.textSecondary}>{stat.value}</span>
						</text>
					))}
				</>
			) : null}
		</box>
	);
}

function SectionContent({ section }: { section: ResumeSection }) {
	return (
		<box
			flexGrow={1}
			border
			borderStyle="rounded"
			borderColor={theme.goldDim}
			title={`  ${section.headerText}  `}
			titleAlignment="center"
			padding={1}
		>
			<scrollbox
				key={section.id}
				style={{
					rootOptions: { flexGrow: 1, backgroundColor: theme.bgDark },
					wrapperOptions: { flexGrow: 1 },
					viewportOptions: { paddingLeft: 1, paddingRight: 1 },
				}}
			>
				{section.lines.map((line, index) => (
					<FormatLine key={`${section.id}-${index}`} line={line} />
				))}
			</scrollbox>
		</box>
	);
}

const KEY_VALUE_RE = /^([A-Za-z][A-Za-z ]+):\s+(.+)$/;
const BULLET_RE = /^- (.+)$/;
const PROJECT_NAME_RE = /^(.+) \(([^)]+)\)$/;
const DASH_UNDERLINE_RE = /^-{3,}$/;

function FormatLine({ line }: { line: string }) {
	if (!line || line.trim() === "") {
		return (
			<text>
				<span> </span>
			</text>
		);
	}

	if (DASH_UNDERLINE_RE.test(line)) {
		return (
			<text>
				<span fg={theme.goldDim}>{"─".repeat(line.length)}</span>
			</text>
		);
	}

	const projectMatch = PROJECT_NAME_RE.exec(line);
	if (projectMatch && !KEY_VALUE_RE.test(line)) {
		return (
			<text>
				<span fg={theme.textPrimary}>
					<strong>{projectMatch[1]}</strong>
				</span>
				<span fg={theme.textDim}>{` (${projectMatch[2]})`}</span>
			</text>
		);
	}

	const bulletMatch = BULLET_RE.exec(line);
	if (bulletMatch) {
		return (
			<text>
				<span fg={theme.cyan}>{"  • "}</span>
				<span fg={theme.textPrimary}>{bulletMatch[1]}</span>
			</text>
		);
	}

	const keyValueMatch = KEY_VALUE_RE.exec(line);
	if (keyValueMatch) {
		return (
			<text>
				<span fg={theme.textDim}>{keyValueMatch[1]}: </span>
				<span fg={theme.textPrimary}>{keyValueMatch[2]}</span>
			</text>
		);
	}

	return (
		<text>
			<span fg={theme.textSecondary}>{line}</span>
		</text>
	);
}

interface DiffViewProps {
	draftText: string;
	finalText: string;
}

function DiffView({ draftText, finalText }: DiffViewProps) {
	const diffString = useMemo(
		() => createUnifiedDiff(draftText, finalText),
		[draftText, finalText],
	);

	return (
		<box
			flexGrow={1}
			border
			borderStyle="rounded"
			borderColor={theme.goldDim}
			title="  Draft → Final  "
			titleAlignment="center"
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
				<diff diff={diffString} view="split" showLineNumbers />
			</scrollbox>
		</box>
	);
}
