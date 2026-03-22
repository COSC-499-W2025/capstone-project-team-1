import { useKeyboard } from "@opentui/react";
import { useState } from "react";
import { mockProjects } from "../data/mockProjects";
import { type Project, theme } from "../types";
import { ClickableList } from "../utils/mouse";
import { TopBar } from "./TopBar";

interface ProjectListProps {
	projects: Project[];
	onContinue: () => void;
	onBack: () => void;
}

export function ProjectList({
	projects,
	onContinue,
	onBack,
}: ProjectListProps) {
	const [selectedIndex, setSelectedIndex] = useState(0);
	const selectedProject = projects[selectedIndex];

	useKeyboard((key) => {
		if (key.name === "up" || key.name === "k") {
			setSelectedIndex((i) => Math.max(0, i - 1));
		}
		if (key.name === "down" || key.name === "j") {
			setSelectedIndex((i) => Math.min(projects.length - 1, i + 1));
		}
		if (key.name === "return") {
			onContinue();
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

					<ClickableList
						items={projects.map((p) => ({
							id: p.id,
							label: p.name,
							description: `${p.language} · ${p.commits} commits`,
						}))}
						selectedId={selectedProject?.id ?? null}
						onSelect={(_id, index) => setSelectedIndex(index)}
						height={16}
						selectedTextColor={theme.gold}
						selectedRowBg={theme.bgMedium}
						evenRowBg={theme.bgDark}
						oddRowBg="#111111"
					/>
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

			{/* Demo Mode Banner */}
			<box
				height={3}
				border
				borderStyle="single"
				borderColor={theme.error}
				paddingLeft={2}
				paddingRight={2}
				paddingTop={1}
				paddingBottom={1}
			>
				<text>
					<span fg={theme.goldDark}>Demo Mode:</span>
					<span fg={theme.textDim}> Press </span>
					<span fg={theme.cyan}>Enter</span>
					<span fg={theme.textDim}> to continue</span>
				</text>
			</box>
		</box>
	);
}
