import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import type { PipelineRepoCandidate } from "../api/types";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface ProjectListProps {
	repos: PipelineRepoCandidate[];
	selectedRepoIds: string[];
	onChangeSelection: (repoIds: string[]) => void;
	onContinue: () => void;
	onBack: () => void;
	notice?: string | null;
}

export function ProjectList({
	repos,
	selectedRepoIds,
	onChangeSelection,
	onContinue,
	onBack,
	notice,
}: ProjectListProps) {
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [message, setMessage] = useState<string | null>(null);

	useEffect(() => {
		if (selectedIndex >= repos.length) {
			setSelectedIndex(Math.max(0, repos.length - 1));
		}
	}, [repos.length, selectedIndex]);

	const selectedSet = useMemo(() => new Set(selectedRepoIds), [selectedRepoIds]);

	const selectedRepos = useMemo(
		() => repos.filter((repo) => selectedSet.has(repo.id)),
		[repos, selectedSet],
	);

	const currentRepo = repos[selectedIndex];

	const setAndClearMessage = (value: string | null) => {
		setMessage(value);
	};

	const toggleCurrent = () => {
		if (!currentRepo) {
			return;
		}
		const next = new Set(selectedRepoIds);
		if (next.has(currentRepo.id)) {
			next.delete(currentRepo.id);
		} else {
			next.add(currentRepo.id);
		}
		onChangeSelection(Array.from(next));
		setAndClearMessage(null);
	};

	const selectAll = () => {
		onChangeSelection(repos.map((repo) => repo.id));
		setAndClearMessage(null);
	};

	const clearAll = () => {
		onChangeSelection([]);
		setAndClearMessage(null);
	};

	const continueIfValid = () => {
		if (!selectedRepoIds.length) {
			setAndClearMessage("Select at least one repository before continuing.");
			return;
		}
		onContinue();
	};

	useKeyboard((key) => {
		if (key.name === "space") {
			toggleCurrent();
			return;
		}

		if (key.name === "a") {
			selectAll();
			return;
		}

		if (key.name === "n") {
			clearAll();
			return;
		}

		if (key.name === "return" || key.name === "enter") {
			continueIfValid();
			return;
		}

		if (key.name === "escape") {
			onBack();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 2"
				title="Select Repositories"
				description="Multi-select the repos you want to include"
			/>

			<box flexGrow={1} flexDirection="row" padding={1} gap={1}>
				<box
					width={56}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					flexDirection="column"
				>
					<box padding={1} backgroundColor={theme.bgMedium}>
						<text>
							<span fg={theme.cyan}>
								<strong>Detected Repositories ({repos.length})</strong>
							</span>
						</text>
					</box>

					{repos.length ? (
						<select
							options={repos.map((repo) => ({
								name: `${selectedSet.has(repo.id) ? "[x]" : "[ ]"} ${repo.name}`,
								value: repo.id,
							}))}
							onChange={(index) => setSelectedIndex(index)}
							selectedIndex={selectedIndex}
							focused
							height={18}
							showScrollIndicator
							itemSpacing={0}
							showDescription={false}
						/>
					) : (
						<box padding={1}>
							<text>
								<span fg={theme.warning}>No repositories detected in this intake.</span>
							</text>
						</box>
					)}
				</box>

				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.cyanDim}
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Selection Summary</strong>
						</span>
					</text>

					<text>
						<span fg={theme.textSecondary}>
							Selected {selectedRepoIds.length} of {repos.length} repositories.
						</span>
					</text>

					{currentRepo ? (
						<box marginTop={1} flexDirection="column" gap={1}>
							<text>
								<span fg={theme.textDim}>Current Repo</span>
							</text>
							<text>
								<span fg={theme.cyan}>{currentRepo.name}</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>{currentRepo.rel_path}</span>
							</text>
						</box>
					) : null}

					<box marginTop={1} flexDirection="column" gap={1}>
						<text>
							<span fg={theme.textDim}>Selected Repos</span>
						</text>
						{selectedRepos.length ? (
							selectedRepos.slice(0, 8).map((repo) => (
								<text key={repo.id}>
									<span fg={theme.textSecondary}>- {repo.name}</span>
								</text>
							))
						) : (
							<text>
								<span fg={theme.warning}>No repositories selected yet.</span>
							</text>
						)}
					</box>
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column">
				{notice ? (
					<text>
						<span fg={theme.warning}>{notice}</span>
					</text>
				) : null}
				{message ? (
					<text>
						<span fg={theme.error}>{message}</span>
					</text>
				) : null}
			</box>
		</box>
	);
}
