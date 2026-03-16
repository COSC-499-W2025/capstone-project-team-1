import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import type { PipelineContributorIdentity } from "../api/types";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface IdentityScreenProps {
	onNext: () => void;
}

export type FocusMode = "list" | "manual";

export const formatContributorName = (
	contributor: PipelineContributorIdentity,
): string =>
	contributor.name || contributor.candidate_username || contributor.email;

export const getToggledFocusMode = (
	currentMode: FocusMode,
	contributorCount: number,
): FocusMode => {
	if (!contributorCount) {
		return "manual";
	}
	return currentMode === "list" ? "manual" : "list";
};

export const resolveIdentitySelection = ({
	focusMode,
	manualEmail,
	selectedContributor,
}: {
	focusMode: FocusMode;
	manualEmail: string;
	selectedContributor?: PipelineContributorIdentity;
}): { selectedEmail?: string; error?: string } => {
	if (focusMode === "manual") {
		const value = manualEmail.trim().toLowerCase();
		if (!value) {
			return { error: "Enter an email to continue." };
		}

		return { selectedEmail: value };
	}

	if (!selectedContributor) {
		return {
			error: "No contributor available. Press Tab to enter an email manually.",
		};
	}

	return { selectedEmail: selectedContributor.email };
};

export function IdentityScreen({ onNext }: IdentityScreenProps) {
	const { state, setSelectedEmail } = useAppState();
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [focusMode, setFocusMode] = useState<FocusMode>("list");
	const [manualEmail, setManualEmail] = useState(state.selectedEmail ?? "");
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!state.contributors.length) {
			setFocusMode("manual");
			setSelectedIndex(0);
			return;
		}

		setSelectedIndex((prev) =>
			Math.min(prev, Math.max(0, state.contributors.length - 1)),
		);
	}, [state.contributors.length]);

	const options = useMemo(
		() =>
			state.contributors.map((contributor) => ({
				name: `${formatContributorName(contributor)} <${contributor.email}>`,
				description: `${contributor.repo_count} repos • ${contributor.commit_count} commits`,
				value: contributor.email,
			})),
		[state.contributors],
	);

	const selectedContributor = state.contributors[selectedIndex];

	const confirmIdentity = () => {
		const result = resolveIdentitySelection({
			focusMode,
			manualEmail,
			selectedContributor,
		});
		if (result.error) {
			setError(result.error);
			return;
		}

		setSelectedEmail(result.selectedEmail ?? null);
		setError(null);
		onNext();
	};

	const handleContributorSelect = () => {
		setError(null);
		confirmIdentity();
	};

	useKeyboard((key) => {
		if (key.name === "tab") {
			setFocusMode((prev) =>
				getToggledFocusMode(prev, state.contributors.length),
			);
			setError(null);
			return;
		}

		if ((key.name === "return" || key.name === "enter") && focusMode === "manual") {
			confirmIdentity();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Identity"
				title="Select Contributor"
				description="Choose your detected git identity or enter an email manually."
			/>

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={focusMode === "list" ? theme.gold : theme.goldDim}
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Detected Contributors</strong>
						</span>
					</text>

					{options.length ? (
						<select
							options={options}
							onChange={(index) => {
								setSelectedIndex(index);
								setError(null);
							}}
							onSelect={handleContributorSelect}
							selectedIndex={selectedIndex}
							focused={focusMode === "list"}
							height={18}
							showScrollIndicator
						/>
					) : (
						<box paddingTop={2}>
							<text>
								<span fg={theme.warning}>
									No contributors were detected for the selected repositories.
								</span>
							</text>
						</box>
					)}
				</box>

				<box
					width={58}
					border
					borderStyle="rounded"
					borderColor={focusMode === "manual" ? theme.cyan : theme.cyanDim}
					padding={2}
					flexDirection="column"
					gap={1}
				>
					<text>
						<span fg={theme.cyan}>
							<strong>Manual Email Entry</strong>
						</span>
					</text>
					<text>
						<span fg={theme.textDim}>
							Press Tab to switch between the contributor list and email input.
						</span>
					</text>

					<input
						value={manualEmail}
						onChange={(value) => {
							setManualEmail(value);
							setError(null);
						}}
						focused={focusMode === "manual"}
						placeholder="name@example.com"
						width={50}
					/>

					<box marginTop={1} flexDirection="column" gap={1}>
						<text>
							<span fg={theme.gold}>
								<strong>Selected Identity</strong>
							</span>
						</text>
						{selectedContributor ? (
							<>
								<text>
									<span fg={theme.textSecondary}>
										{formatContributorName(selectedContributor)}
									</span>
								</text>
								<text>
									<span fg={theme.cyan}>{selectedContributor.email}</span>
								</text>
								<text>
									<span fg={theme.textDim}>
										{selectedContributor.repo_count} repos •{" "}
										{selectedContributor.commit_count} commits
									</span>
								</text>
							</>
						) : (
							<text>
								<span fg={theme.textDim}>
									Manual mode is available when no contributor match is shown.
								</span>
							</text>
						)}
					</box>
				</box>
			</box>

			<box
				paddingLeft={2}
				paddingRight={2}
				paddingBottom={1}
				flexDirection="column"
				gap={1}
			>
				<text>
					<span fg={theme.textDim}>Use ↑/↓ to navigate and Enter to confirm.</span>
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
