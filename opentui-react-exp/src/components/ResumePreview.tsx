import { useKeyboard } from "@opentui/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { createUnifiedDiff, resumeStats, resumeToSections, resumeToText } from "../utils";
import type { ResumeSection, StatLine } from "../utils";
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
	const [selectedSection, setSelectedSection] = useState(0);
	const [saveMessage, setSaveMessage] = useState<string | null>(null);

	const activeData = mode === "draft" ? state.resumeV3Draft : state.resumeV3Output;
	const sections = useMemo(() => resumeToSections(activeData), [activeData]);
	const stats = useMemo(() => resumeStats(activeData), [activeData]);

	const draftText = useMemo(() => resumeToText(state.resumeV3Draft), [state.resumeV3Draft]);
	const finalText = useMemo(() => resumeToText(state.resumeV3Output), [state.resumeV3Output]);

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
		if (!saveMessage) return;
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
				setSelectedSection((s) => Math.max(0, s - 1));
				return;
			}
			if (key.name === "down") {
				setSelectedSection((s) => Math.min(sections.length - 1, s + 1));
				return;
			}
			// Number keys 1-5 jump to section
			const num = Number(key.name);
			if (num >= 1 && num <= 5 && num <= sections.length) {
				setSelectedSection(num - 1);
				return;
			}
		}

		if (key.name === "s") {
			void saveResume();
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

	const current = sections[selectedSection] ?? sections[0]!;

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

/* ── Visual Tab Bar ─────────────────────────────────────────────── */

function ModeTabBar({ mode }: { mode: PreviewMode }) {
	return (
		<box
			flexDirection="row"
			justifyContent="center"
			gap={2}
			paddingTop={1}
			paddingBottom={1}
		>
			{modeOrder.map((m) => (
				<box
					key={m}
					paddingLeft={1}
					paddingRight={1}
					backgroundColor={m === mode ? theme.goldDim : undefined}
				>
					<text>
						<span fg={m === mode ? theme.gold : theme.textDim}>
							{m === mode ? (
								<strong>{m.charAt(0).toUpperCase() + m.slice(1)}</strong>
							) : (
								m.charAt(0).toUpperCase() + m.slice(1)
							)}
						</span>
					</text>
				</box>
			))}
		</box>
	);
}

/* ── Section Navigation Sidebar ─────────────────────────────────── */

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
			{sections.map((section, i) => (
				<text key={section.id}>
					<span fg={i === selectedIndex ? theme.gold : theme.textSecondary}>
						{i === selectedIndex ? `▶ ${section.tocLabel}` : `  ${section.tocLabel}`}
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

/* ── Section Content with Rich Formatting ───────────────────────── */

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
				{section.lines.map((line, i) => (
					<FormatLine key={`${section.id}-${i}`} line={line} />
				))}
			</scrollbox>
		</box>
	);
}

/* ── Rich Line Formatting ───────────────────────────────────────── */

const KEY_VALUE_RE = /^([A-Za-z][A-Za-z ]+):\s+(.+)$/;
const BULLET_RE = /^- (.+)$/;
const PROJECT_NAME_RE = /^(.+) \(([^)]+)\)$/;
const DASH_UNDERLINE_RE = /^-{3,}$/;

function FormatLine({ line }: { line: string }) {
	if (!line || line.trim() === "") {
		return (
			<text>
				<span>{" "}</span>
			</text>
		);
	}

	// Dash underline → goldDim separator
	if (DASH_UNDERLINE_RE.test(line)) {
		return (
			<text>
				<span fg={theme.goldDim}>{"─".repeat(line.length)}</span>
			</text>
		);
	}

	// Project name line e.g. "my-app (CLI Tool)"
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

	// Bullet line → cyan marker + white text
	const bulletMatch = BULLET_RE.exec(line);
	if (bulletMatch) {
		return (
			<text>
				<span fg={theme.cyan}>{"  • "}</span>
				<span fg={theme.textPrimary}>{bulletMatch[1]}</span>
			</text>
		);
	}

	// Key: value → dim label, bright value
	const kvMatch = KEY_VALUE_RE.exec(line);
	if (kvMatch) {
		return (
			<text>
				<span fg={theme.textDim}>{kvMatch[1]}: </span>
				<span fg={theme.textPrimary}>{kvMatch[2]}</span>
			</text>
		);
	}

	// Default: secondary text
	return (
		<text>
			<span fg={theme.textSecondary}>{line}</span>
		</text>
	);
}

/* ── Diff View ──────────────────────────────────────────────────── */

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
				<diff
					diff={diffString}
					view="split"
					showLineNumbers
				/>
			</scrollbox>
		</box>
	);
}
