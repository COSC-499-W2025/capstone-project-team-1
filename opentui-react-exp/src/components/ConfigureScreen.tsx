/**
 * Unified Configure screen for both Local LLM and Cloud flows.
 *
 * Left panel (~65%):  scrollable project card grid with select/deselect all
 * Right panel (~35%): email input + model picker (cloud only) + confirm
 *
 * Tab switches focus between the project grid and the config panel.
 */
import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { type Project, theme } from "../types";
import { TopBar } from "./TopBar";
import { useToast } from "./Toast";
import { CLOUD_MODELS, DEFAULT_MODEL_ID } from "./cloud-ai/ModelPicker";
import type { ConsentLevel } from "../api/types";

// ── Types ────────────────────────────────────────────────────────────────────

export interface ConfigureResult {
	selectedProjectIds: string[];
	email: string;
	/** Cloud flow only — chosen model ID. */
	modelId?: string;
}

interface ConfigureScreenProps {
	consentLevel: ConsentLevel;
	projects: Project[];
	initialSelectedIds?: string[];
	/** Pre-fill email (e.g. from GitHub identity in cloud flow). */
	initialEmail?: string;
	/** GitHub login to display in cloud flow. */
	cloudLogin?: string;
	/** GitHub display name to show in cloud flow. */
	cloudName?: string | null;
	onContinue: (result: ConfigureResult) => void;
	onBack: () => void;
}

type FocusPanel = "projects" | "config";

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
	const nameColor = isSelected
		? theme.gold
		: isCursor
			? theme.textPrimary
			: theme.textSecondary;

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
			<text>
				<span fg={checkColor}>
					<strong>{checkIcon}</strong>
				</span>
				<span fg={theme.textDim}>{" "}</span>
				<span fg={nameColor}>
					<strong>{project.name}</strong>
				</span>
			</text>

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
			</box>

			<text>
				<span fg={isSelected ? theme.success : theme.textDim}>
					{isSelected ? "Selected for analysis" : project.lastUpdated}
				</span>
			</text>
		</box>
	);
}

// ── ConfigureScreen ──────────────────────────────────────────────────────────

const COLS = 3; // 3 cards per row in the left panel

export function ConfigureScreen({
	consentLevel,
	projects,
	initialSelectedIds = [],
	initialEmail = "",
	cloudLogin,
	cloudName,
	onContinue,
	onBack,
}: ConfigureScreenProps) {
	const isCloud = consentLevel === "cloud";
	const toast = useToast();

	// ── Project selection state ──
	const [cursorIndex, setCursorIndex] = useState(0);
	const [selectedIds, setSelectedIds] = useState<string[]>(initialSelectedIds);
	const selectedIdSet = useMemo(() => new Set(selectedIds), [selectedIds]);

	// ── Config state ──
	const [email, setEmail] = useState(initialEmail);
	const [editingEmail, setEditingEmail] = useState(!initialEmail);
	const [modelIndex, setModelIndex] = useState(
		Math.max(
			0,
			CLOUD_MODELS.findIndex((m) => m.id === DEFAULT_MODEL_ID),
		),
	);

	// ── Focus management ──
	const [focusPanel, setFocusPanel] = useState<FocusPanel>("projects");

	useEffect(() => {
		setSelectedIds(initialSelectedIds);
	}, [initialSelectedIds]);

	useEffect(() => {
		if (initialEmail) {
			setEmail(initialEmail);
			setEditingEmail(false);
		}
	}, [initialEmail]);

	// ── Project helpers ──
	const toggleProject = (projectId: string) => {
		setSelectedIds((current) => {
			if (current.includes(projectId)) {
				return current.filter((id) => id !== projectId);
			}
			return [...current, projectId];
		});

	};

	const selectAll = () => {
		setSelectedIds(projects.map((p) => p.id));

	};
	const deselectAll = () => setSelectedIds([]);

	const allSelected = selectedIds.length === projects.length;

	// ── Email helpers ──
	const isValidEmail = (e: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);

	// ── Confirm ──
	const handleConfirm = () => {
		if (!selectedIds.length) {
			toast.show({ variant: "warning", message: "Select at least one repository to continue." });
			return;
		}
		const trimmed = email.trim();
		if (!trimmed) {
			toast.show({ variant: "warning", message: "Please enter your email to continue." });
			setFocusPanel("config");
			setEditingEmail(true);
			return;
		}
		if (!isValidEmail(trimmed)) {
			toast.show({ variant: "warning", message: "Please enter a valid email address." });
			setFocusPanel("config");
			setEditingEmail(true);
			return;
		}

		onContinue({
			selectedProjectIds: selectedIds,
			email: trimmed,
			modelId: isCloud ? CLOUD_MODELS[modelIndex]?.id : undefined,
		});
	};

	// ── Grid rows ──
	const rows: Project[][] = [];
	for (let i = 0; i < projects.length; i += COLS) {
		rows.push(projects.slice(i, i + COLS));
	}

	// ── Keyboard ──
	useKeyboard((key) => {
		// Tab switches panels
		if (key.name === "tab") {
			if (editingEmail && focusPanel === "config") {
				// Commit email first, then switch
				const trimmed = email.trim();
				if (trimmed && isValidEmail(trimmed)) {
					setEditingEmail(false);
				}
			}
			setFocusPanel((p) => (p === "projects" ? "config" : "projects"));
			return;
		}

		if (key.name === "escape") {
			if (editingEmail && focusPanel === "config" && initialEmail) {
				setEmail(initialEmail);
				setEditingEmail(false);
				return;
			}
			onBack();
			return;
		}

		if (key.name === "return") {
			if (editingEmail && focusPanel === "config") {
				const trimmed = email.trim();
				if (trimmed && isValidEmail(trimmed)) {
					setEditingEmail(false);
				} else {
					toast.show({ variant: "warning", message: trimmed ? "Please enter a valid email address." : "Please enter your email to continue." });
				}
				return;
			}
			handleConfirm();
			return;
		}

		// ── Project panel keys ──
		if (focusPanel === "projects") {
			if (key.name === "left") {
				setCursorIndex((i) => Math.max(0, i - 1));
			} else if (key.name === "right") {
				setCursorIndex((i) => Math.min(projects.length - 1, i + 1));
			} else if (key.name === "up") {
				setCursorIndex((i) => Math.max(0, i - COLS));
			} else if (key.name === "down") {
				setCursorIndex((i) => Math.min(projects.length - 1, i + COLS));
			} else if (key.name === "space") {
				const project = projects[cursorIndex];
				if (project) toggleProject(project.id);
			} else if (key.name === "a") {
				selectAll();
			} else if (key.name === "d") {
				deselectAll();
			}
			return;
		}

		// ── Config panel keys ──
		if (focusPanel === "config") {
			if (editingEmail) {
				if (key.name === "backspace") {
					setEmail((v) => v.slice(0, -1));
				} else if (
					key.sequence &&
					key.sequence.length === 1 &&
					!key.ctrl &&
					!key.meta
				) {
					setEmail((v) => v + key.sequence);
				}
				return;
			}

			// Not editing email
			if (key.name === "e") {
				setEditingEmail(true);
				return;
			}

			if (isCloud) {
				if (key.name === "up") {
					setModelIndex((i) => Math.max(0, i - 1));
				} else if (key.name === "down") {
					setModelIndex((i) =>
						Math.min(CLOUD_MODELS.length - 1, i + 1),
					);
				}
			}
		}
	});

	// ── Render ──
	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Configure"
				description={
					isCloud
						? "Select your projects, confirm your email, and choose a model for cloud-powered analysis."
						: "Select your projects and enter your email to begin local AI analysis."
				}
			/>

			{/* Main split view */}
			<box flexGrow={1} flexDirection="row" gap={1} paddingLeft={2} paddingRight={2} paddingTop={1}>
				{/* ── Left panel: Project grid ── */}
				<box
					flexGrow={2}
					flexBasis={0}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={focusPanel === "projects" ? theme.gold : theme.textDim}
					padding={1}
					gap={1}
				>
					{/* Panel header */}
					<box flexDirection="row" justifyContent="space-between" alignItems="center">
						<text>
							<span fg={theme.gold}>
								<strong>Projects</strong>
							</span>
							<span fg={theme.textDim}>
								{" "}· {selectedIds.length} of {projects.length} selected
							</span>
						</text>

						<box flexDirection="row" gap={2}>
							<box onMouseDown={selectAll}>
								<text>
									<span fg={!allSelected ? theme.cyan : theme.textDim}>
										<strong>All</strong>
									</span>
									<span fg={theme.textDim}> (a)</span>
								</text>
							</box>
							<box onMouseDown={deselectAll}>
								<text>
									<span fg={selectedIds.length > 0 ? theme.cyan : theme.textDim}>
										<strong>None</strong>
									</span>
									<span fg={theme.textDim}> (d)</span>
								</text>
							</box>
						</box>
					</box>

					{/* Scrollable card grid */}
					<scrollbox
						focused={focusPanel === "projects"}
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
						<box flexDirection="column" gap={1}>
							{rows.map((row, rowIdx) => (
								<box key={rowIdx} flexDirection="row" gap={1}>
									{row.map((project, colIdx) => {
										const globalIdx = rowIdx * COLS + colIdx;
										return (
											<ProjectCard
												key={project.id}
												project={project}
												isSelected={selectedIdSet.has(project.id)}
												isCursor={
													focusPanel === "projects" &&
													cursorIndex === globalIdx
												}
												onToggle={() => toggleProject(project.id)}
												onFocus={() => {
													setFocusPanel("projects");
													setCursorIndex(globalIdx);
												}}
											/>
										);
									})}
									{row.length < COLS
										? Array.from({ length: COLS - row.length }).map(
												(_, i) => (
													<box
														key={`spacer-${i}`}
														flexGrow={1}
														flexBasis={0}
														flexShrink={0}
													/>
												),
											)
										: null}
								</box>
							))}
						</box>
					</scrollbox>
				</box>

				{/* ── Right panel: Configuration ── */}
				<box
					flexGrow={1}
					flexBasis={0}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={focusPanel === "config" ? theme.gold : theme.textDim}
					padding={2}
					gap={1}
					onMouseDown={() => setFocusPanel("config")}
				>
					{/* Panel header */}
					<text>
						<span fg={theme.gold}>
							<strong>{isCloud ? "Cloud Configuration" : "Configuration"}</strong>
						</span>
					</text>

					{/* Cloud: show GitHub identity */}
					{isCloud && cloudLogin ? (
						<box flexDirection="column">
							<text>
								<span fg={theme.textSecondary}>
									{"  "}Signed in as{" "}
								</span>
								<span fg={theme.gold}>
									<strong>{cloudLogin}</strong>
								</span>
								{cloudName ? (
									<span fg={theme.textDim}> ({cloudName})</span>
								) : null}
							</text>
						</box>
					) : null}

					{/* Email section */}
					<box flexDirection="column" gap={0} paddingTop={1}>
						<text>
							<span fg={theme.textSecondary}>
								<strong>Email</strong>
							</span>
						</text>
						{editingEmail && focusPanel === "config" ? (
							<box
								border
								borderStyle="single"
								borderColor={theme.cyan}
								paddingLeft={1}
								paddingRight={1}
							>
								<text>
									<span fg={theme.textPrimary}>
										{email || " "}
									</span>
									<span fg={theme.cyan}>_</span>
								</text>
							</box>
						) : (
							<box flexDirection="column">
								<text>
									<span fg={email ? theme.textPrimary : theme.textDim}>
										{email || "No email set"}
									</span>
								</text>
								<text>
									<span fg={theme.textDim}>Press </span>
									<span fg={theme.cyan}>e</span>
									<span fg={theme.textDim}> to {email ? "change" : "enter"} email</span>
								</text>
							</box>
						)}
					</box>

					{/* Cloud: Model picker */}
					{isCloud ? (
						<box flexDirection="column" gap={1} paddingTop={1}>
							<text>
								<span fg={theme.textSecondary}>
									<strong>Model</strong>
								</span>
							</text>
							<box flexDirection="column" gap={1}>
								{CLOUD_MODELS.map((model, i) => {
									const isSelected = i === modelIndex;
									const bullet = isSelected ? "●" : "○";
									const bulletColor = isSelected
										? theme.gold
										: theme.textDim;
									const nameColor = isSelected
										? theme.gold
										: theme.textSecondary;
									const descColor = isSelected
										? theme.textSecondary
										: theme.textDim;

									return (
										<box
											key={model.id}
											flexDirection="column"
											paddingLeft={1}
											onMouseDown={() => setModelIndex(i)}
										>
											<text>
												<span fg={bulletColor}>{bullet} </span>
												<span fg={nameColor}>
													<strong>{model.name}</strong>
												</span>
												<span fg={theme.textDim}>
													{" "}· {model.provider}
												</span>
											</text>
											<text>
												<span fg={descColor}>
													{"   "}
													{model.description}
												</span>
											</text>
										</box>
									);
								})}
							</box>
						</box>
					) : null}

					{/* Confirm */}
					<box flexDirection="column" gap={1} paddingTop={1}>

						<box flexDirection="row" justifyContent="center" paddingTop={1}>
							<box
								border
								borderStyle="rounded"
								borderColor={
									selectedIds.length > 0 && email.trim()
										? theme.gold
										: theme.textDim
								}
								backgroundColor={
									selectedIds.length > 0 && email.trim()
										? "#1a1a00"
										: theme.bgDark
								}
								paddingLeft={2}
								paddingRight={2}
								onMouseDown={handleConfirm}
							>
								<text>
									<span
										fg={
											selectedIds.length > 0 && email.trim()
												? theme.gold
												: theme.textDim
										}
									>
										<strong>
											{isCloud ? "Start Cloud Analysis" : "Start Analysis"}
										</strong>
									</span>
								</text>
							</box>
						</box>
					</box>
				</box>
			</box>

			{/* Tab hint bar */}
			<box
				flexDirection="row"
				justifyContent="center"
				paddingTop={1}
				paddingBottom={1}
			>
				<text>
					<span fg={theme.textDim}>Press </span>
					<span fg={theme.cyan}>Tab</span>
					<span fg={theme.textDim}>
						{" "}to switch between Projects and Configuration
					</span>
				</text>
			</box>
		</box>
	);
}
