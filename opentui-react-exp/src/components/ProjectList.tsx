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

export function ProjectList({
	projects,
	initialSelectedIds = [],
	onContinue,
	onBack,
}: ProjectListProps) {
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [selectedIds, setSelectedIds] = useState<string[]>(initialSelectedIds);
	const [error, setError] = useState<string | null>(null);
	const selectedProject = projects[selectedIndex];
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

	const continueWithSelection = () => {
		if (!selectedIds.length) {
			setError("Select at least one repository to continue.");
			return;
		}
		onContinue(selectedIds);
	};

	useKeyboard((key) => {
		if (key.name === "up" || key.name === "k") {
			setSelectedIndex((i) => Math.max(0, i - 1));
		}
		if (key.name === "down" || key.name === "j") {
			setSelectedIndex((i) => Math.min(projects.length - 1, i + 1));
		}
		if (key.name === "space") {
			if (selectedProject) {
				toggleProjectSelection(selectedProject.id);
			}
		}
		if (key.name === "return") {
			continueWithSelection();
		}
		if (key.name === "escape") {
			onBack();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar title="Projects" />

			{/* Split view */}
			<box flexGrow={1} flexDirection="row">
				{/* Left panel: Project list */}
				<box
					width={45}
					flexDirection="column"
					border
					borderStyle="single"
					borderColor={theme.goldDim}
				>
					<box
						paddingLeft={1}
						paddingTop={1}
						paddingBottom={1}
						backgroundColor={theme.bgMedium}
					>
						<text>
							<span fg={theme.cyan}>
								<strong>Projects</strong>
							</span>
						</text>
					</box>
					<scrollbox height={16} focused>
						{projects.map((project, index) => {
							const isCursor = project.id === selectedProject?.id;
							const isSelected = selectedIdSet.has(project.id);
							return (
								<box
									key={project.id}
									backgroundColor={
										isCursor
											? theme.bgMedium
											: index % 2 === 0
												? theme.bgDark
												: "#111111"
									}
									paddingLeft={1}
									paddingRight={1}
									onMouseDown={() => {
										setSelectedIndex(index);
										toggleProjectSelection(project.id);
									}}
								>
									<text>
										<span fg={isCursor ? theme.gold : theme.textSecondary}>
											{isCursor ? ">" : " "}{" "}
											{isSelected ? "[x]" : "[ ]"} {project.name}
										</span>
										<span fg={theme.textDim}>
											{" "}
											{project.language} · {project.commits} commits
										</span>
									</text>
								</box>
							);
						})}
					</scrollbox>
				</box>

				{/* Right panel: Project details */}
				<box flexGrow={1} flexDirection="column" padding={2} gap={2}>
					{selectedProject && (
						<>
							{/* Project name */}
							<box flexDirection="column" gap={1}>
								<text>
									<span fg={theme.gold}>
										<strong>{selectedProject.name}</strong>
									</span>
								</text>
								<text>
									<span
										fg={
											selectedIdSet.has(selectedProject.id)
												? theme.success
												: theme.warning
										}
									>
										{selectedIdSet.has(selectedProject.id)
											? "Selected for analysis"
											: "Not selected yet"}
									</span>
								</text>
								<text>
									<span fg={theme.textSecondary}>
										{selectedProject.description}
									</span>
								</text>
							</box>

							{/* Stats */}
							<box flexDirection="row" gap={4}>
								<box flexDirection="column">
									<text>
										<span fg={theme.textDim}>Language</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											<strong>{selectedProject.language}</strong>
										</span>
									</text>
								</box>
								<box flexDirection="column">
									<text>
										<span fg={theme.textDim}>Commits</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											<strong>{selectedProject.commits}</strong>
										</span>
									</text>
								</box>
								<box flexDirection="column">
									<text>
										<span fg={theme.textDim}>Files</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											<strong>{selectedProject.files}</strong>
										</span>
									</text>
								</box>
								<box flexDirection="column">
									<text>
										<span fg={theme.textDim}>Updated</span>
									</text>
									<text>
										<span fg={theme.cyan}>
											<strong>{selectedProject.lastUpdated}</strong>
										</span>
									</text>
								</box>
							</box>

							{/* Technologies */}
							<box flexDirection="column" gap={1}>
								<text>
									<span fg={theme.textDim}>Technologies</span>
								</text>
								<box flexDirection="row" gap={1} flexWrap="wrap">
									{selectedProject.technologies.map((tech, i) => (
										<box
											key={i}
											backgroundColor={theme.cyanDim}
											paddingLeft={1}
											paddingRight={1}
										>
											<text>
												<span fg={theme.textPrimary}>{tech}</span>
											</text>
										</box>
									))}
								</box>
							</box>
						</>
					)}
				</box>
			</box>

			{/* Footer guidance */}
			<box
				height={4}
				border
				borderStyle="single"
				borderColor={error ? theme.error : theme.goldDim}
				paddingLeft={2}
				paddingRight={2}
				paddingTop={1}
				paddingBottom={1}
				flexDirection="column"
			>
				<text>
					<span fg={theme.goldDark}>Selected:</span>
					<span fg={theme.textDim}> Press </span>
					<span fg={theme.cyan}>Space</span>
					<span fg={theme.textDim}> to toggle repos, </span>
					<span fg={theme.cyan}>Enter</span>
					<span fg={theme.textDim}> to continue with </span>
					<span fg={theme.gold}>{selectedIds.length}</span>
					<span fg={theme.textDim}> selected repo(s)</span>
				</text>
				{error ? (
					<text>
						<span fg={theme.error}>{error}</span>
					</text>
				) : null}
			</box>
		</box>
	);
}
