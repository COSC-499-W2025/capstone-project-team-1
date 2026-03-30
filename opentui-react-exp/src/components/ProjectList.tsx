import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { type Project, theme } from "../types";
import { TopBar } from "./TopBar";

interface ProjectListProps {
	projects: Project[];
	initialSelectedIds?: string[];
	onContinue: (selectedProjectIds: string[]) => void;
	onBack: () => void;
}

// ── ProjectCard ──────────────────────────────────────────────────────────────

interface ProjectCardProps {
	project: Project;
	isSelected: boolean;
	isCursor: boolean;
	onToggle: () => void;
	onFocus: () => void;
}

function ProjectCard({
	project,
	isSelected,
	isCursor,
	onToggle,
	onFocus,
}: ProjectCardProps) {
	const borderColor = isSelected
		? theme.gold
		: isCursor
			? theme.goldDim
			: theme.textDim;
	const bgColor = isSelected
		? theme.bgMedium
		: isCursor
			? "#1a1a1a"
			: theme.bgDark;

	const checkColor = isSelected ? theme.success : theme.textDim;
	const checkIcon = isSelected ? "✓" : "○";
	const nameColor = isSelected ? theme.gold : isCursor ? theme.textPrimary : theme.textSecondary;

	return (
		<box
			flexGrow={1}
			flexBasis={0}
			flexShrink={0}
			flexDirection="column"
			padding={1}
			border
			borderStyle="rounded"
			borderColor={borderColor}
			backgroundColor={bgColor}
			gap={1}
			onMouseDown={() => {
				onFocus();
				onToggle();
			}}
		>
			{/* Header: checkbox + name */}
			<text>
				<span fg={checkColor}>
					<strong>{checkIcon}</strong>
				</span>
				<span fg={theme.textDim}>{" "}</span>
				<span fg={nameColor}>
					<strong>{project.name}</strong>
				</span>
			</text>

			{/* Stats row */}
			<box flexDirection="row" gap={2}>
				{project.language ? (
					<text>
						<span fg={theme.cyan}>{project.language}</span>
					</text>
				) : null}
				{project.commits > 0 ? (
					<text>
						<span fg={theme.textDim}>
							{project.commits} commit{project.commits !== 1 ? "s" : ""}
						</span>
					</text>
				) : null}
				{project.files > 0 ? (
					<text>
						<span fg={theme.textDim}>
							{project.files} file{project.files !== 1 ? "s" : ""}
						</span>
					</text>
				) : null}
			</box>

			{/* Status */}
			<text>
				<span fg={isSelected ? theme.success : theme.textDim}>
					{isSelected ? "Selected for analysis" : project.lastUpdated}
				</span>
			</text>
		</box>
	);
}

// ── ProjectList ──────────────────────────────────────────────────────────────

const COLS = 4;

export function ProjectList({
	projects,
	initialSelectedIds = [],
	onContinue,
	onBack,
}: ProjectListProps) {
	const [cursorIndex, setCursorIndex] = useState(0);
	const [selectedIds, setSelectedIds] = useState<string[]>(initialSelectedIds);
	const [error, setError] = useState<string | null>(null);
	const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);

	useEffect(() => {
		setSelectedIds(initialSelectedIds);
	}, [initialSelectedIds]);

	const toggleProjectSelection = (projectId: string) => {
		setSelectedIds((current) => {
			if (current.includes(projectId)) {
				return current.filter((id) => id !== projectId);
			}
			return [...current, projectId];
		});
		setError(null);
	};

	const selectAll = () => {
		setSelectedIds(projects.map((p) => p.id));
		setError(null);
	};

	const deselectAll = () => {
		setSelectedIds([]);
	};

	const continueWithSelection = () => {
		if (!selectedIds.length) {
			setError("Select at least one repository to continue.");
			return;
		}
		onContinue(selectedIds);
	};

	// Build rows for grid layout
	const rows: Project[][] = [];
	for (let i = 0; i < projects.length; i += COLS) {
		rows.push(projects.slice(i, i + COLS));
	}

	useKeyboard((key) => {
		if (key.name === "left") {
			setCursorIndex((i) => Math.max(0, i - 1));
		}
		if (key.name === "right") {
			setCursorIndex((i) => Math.min(projects.length - 1, i + 1));
		}
		if (key.name === "up") {
			setCursorIndex((i) => Math.max(0, i - COLS));
		}
		if (key.name === "down") {
			setCursorIndex((i) => Math.min(projects.length - 1, i + COLS));
		}
		if (key.name === "space") {
			const project = projects[cursorIndex];
			if (project) {
				toggleProjectSelection(project.id);
			}
		}
		if (key.name === "return") {
			continueWithSelection();
		}
		if (key.name === "escape") {
			onBack();
		}
		// 'a' to select all, 'd' to deselect all
		if (key.name === "a") {
			selectAll();
		}
		if (key.name === "d") {
			deselectAll();
		}
	});

	const allSelected = selectedIds.length === projects.length;

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Projects"
				description="Select the repositories from your upload that you'd like to include in your portfolio analysis."
			/>

			{/* Scrollable card grid */}
			<scrollbox
				focused
				style={{
					rootOptions: { backgroundColor: theme.bgDark },
					wrapperOptions: { backgroundColor: theme.bgDark },
					viewportOptions: { backgroundColor: theme.bgDark },
					contentOptions: { backgroundColor: theme.bgDark },
					scrollbarOptions: {
						showArrows: true,
						trackOptions: {
							foregroundColor: theme.goldDim,
							backgroundColor: theme.bgMedium,
						},
					},
				}}
			>
				<box
					flexDirection="column"
					gap={1}
					paddingLeft={2}
					paddingRight={2}
					paddingBottom={1}
				>
					{rows.map((row, rowIdx) => (
						<box key={rowIdx} flexDirection="row" gap={1}>
							{row.map((project, colIdx) => {
								const globalIdx = rowIdx * COLS + colIdx;
								return (
									<ProjectCard
										key={project.id}
										project={project}
										isSelected={selectedIdSet.has(project.id)}
										isCursor={cursorIndex === globalIdx}
										onToggle={() => toggleProjectSelection(project.id)}
										onFocus={() => setCursorIndex(globalIdx)}
									/>
								);
							})}
							{/* Spacers for incomplete rows to maintain grid alignment */}
							{row.length < COLS
								? Array.from({ length: COLS - row.length }).map((_, i) => (
										<box key={`spacer-${i}`} flexGrow={1} flexBasis={0} flexShrink={0} />
									))
								: null}
						</box>
					))}
				</box>
			</scrollbox>

			{/* Footer: Toolbar + Confirm button + error */}
			<box flexDirection="column" gap={1} paddingTop={1} paddingBottom={1}>
				{error ? (
					<box flexDirection="row" justifyContent="center">
						<text>
							<span fg={theme.error}>{error}</span>
						</text>
					</box>
				) : null}

				<box flexDirection="row" justifyContent="center" alignItems="center" gap={4}>
					<box flexDirection="row" gap={2}>
						<box
							border
							borderStyle="rounded"
							borderColor={!allSelected ? theme.goldDim : theme.textDim}
							backgroundColor={!allSelected ? "#1a1a00" : theme.bgDark}
							paddingLeft={1}
							paddingRight={1}
							onMouseDown={selectAll}
						>
							<text>
								<span fg={!allSelected ? theme.gold : theme.textDim}>
									<strong>Select All</strong>
								</span>
								<span fg={theme.textDim}> (a)</span>
							</text>
						</box>

						<box
							border
							borderStyle="rounded"
							borderColor={selectedIds.length > 0 ? theme.goldDim : theme.textDim}
							backgroundColor={selectedIds.length > 0 ? "#1a1a00" : theme.bgDark}
							paddingLeft={1}
							paddingRight={1}
							onMouseDown={deselectAll}
						>
							<text>
								<span fg={selectedIds.length > 0 ? theme.gold : theme.textDim}>
									<strong>Deselect All</strong>
								</span>
								<span fg={theme.textDim}> (d)</span>
							</text>
						</box>

						<box paddingLeft={1} paddingTop={1}>
							<text>
								<span fg={theme.gold}>
									<strong>{selectedIds.length}</strong>
								</span>
								<span fg={theme.textDim}>
									{" "}of {projects.length} selected
								</span>
							</text>
						</box>
					</box>

					<box
						border
						borderStyle="rounded"
						borderColor={selectedIds.length > 0 ? theme.gold : theme.textDim}
						backgroundColor={selectedIds.length > 0 ? "#1a1a00" : theme.bgDark}
						paddingLeft={2}
						paddingRight={2}
						onMouseDown={continueWithSelection}
					>
						<text>
							<span fg={selectedIds.length > 0 ? theme.gold : theme.textDim}>
								<strong>
									Continue with {selectedIds.length} repo{selectedIds.length !== 1 ? "s" : ""}
								</strong>
							</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
