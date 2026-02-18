import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/endpoints";
import { useAppState } from "../context/AppContext";
import { theme } from "../types";
import { toErrorMessage } from "../utils";
import { TopBar } from "./TopBar";

interface IdentityScreenProps {
	onContinue: () => void;
	onBack: () => void;
}

type FocusMode = "list" | "manual";

export function IdentityScreen({ onContinue, onBack }: IdentityScreenProps) {
	const {
		state,
		setContributors,
		setSelectedEmail,
		setPipelineNotice,
	} = useAppState();
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [focusMode, setFocusMode] = useState<FocusMode>("list");
	const [manualEmail, setManualEmail] = useState(state.selectedEmail || "");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		if (!state.intakeId || !state.selectedRepoIds.length) {
			setError("Select repositories before choosing identity.");
			return;
		}

		let cancelled = false;
		setIsLoading(true);
		setError(null);

		void api
			.getPipelineContributors(state.intakeId, { repo_ids: state.selectedRepoIds })
			.then((response) => {
				if (cancelled) {
					return;
				}
				setContributors(response.contributors);
				if (!response.contributors.length) {
					setFocusMode("manual");
					setPipelineNotice(
						"No contributors found in selected repos. Enter email manually.",
					);
				}
			})
			.catch((requestError) => {
				if (cancelled) {
					return;
				}
				setError(toErrorMessage(requestError));
			})
			.finally(() => {
				if (!cancelled) {
					setIsLoading(false);
				}
			});

		return () => {
			cancelled = true;
		};
	}, [
		setContributors,
		setPipelineNotice,
		state.intakeId,
		state.selectedRepoIds,
	]);

	const options = useMemo(
		() =>
			state.contributors.map((contributor) => ({
				name: `${contributor.name || contributor.candidate_username} <${contributor.email}>`,
				description: `${contributor.repo_count} repos • ${contributor.commit_count} commits`,
				value: contributor.email,
			})),
		[state.contributors],
	);

	const selectedContributor = state.contributors[selectedIndex];

	const confirmIdentity = () => {
		if (focusMode === "manual") {
			const value = manualEmail.trim().toLowerCase();
			if (!value) {
				setError("Enter an email in manual mode.");
				return;
			}
			setSelectedEmail(value);
			setError(null);
			onContinue();
			return;
		}

		if (!selectedContributor) {
			setError("No contributor selected. Use manual mode with Tab.");
			return;
		}

		setSelectedEmail(selectedContributor.email);
		setManualEmail(selectedContributor.email);
		setError(null);
		onContinue();
	};

	useKeyboard((key) => {
		if (key.name === "escape") {
			onBack();
			return;
		}

		if (key.name === "tab") {
			setFocusMode((prev) => (prev === "list" ? "manual" : "list"));
			setError(null);
			return;
		}

		if (key.name === "up" && focusMode === "list" && options.length) {
			setSelectedIndex((prev) => Math.max(0, prev - 1));
			return;
		}

		if (key.name === "down" && focusMode === "list" && options.length) {
			setSelectedIndex((prev) => Math.min(options.length - 1, prev + 1));
			return;
		}

		if (key.name === "return" || key.name === "enter") {
			confirmIdentity();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Identity"
				title="Select Contributor Email"
				description="Choose one identity for this prototype run"
			/>

			<box flexGrow={1} flexDirection="row" gap={1} padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Contributors from Selected Repos</strong>
						</span>
					</text>
					{isLoading ? (
						<box padding={1}>
							<text>
								<span fg={theme.cyan}>Collecting contributor identities...</span>
							</text>
						</box>
					) : options.length ? (
						<select
							options={options}
							onChange={(index) => setSelectedIndex(index)}
							selectedIndex={selectedIndex}
							focused={focusMode === "list"}
							height={18}
							showScrollIndicator
						/>
					) : (
						<box padding={1}>
							<text>
								<span fg={theme.warning}>
									No contributors were found for selected repositories.
								</span>
							</text>
						</box>
					)}
				</box>

				<box
					width={56}
					border
					borderStyle="rounded"
					borderColor={focusMode === "manual" ? theme.cyan : theme.cyanDim}
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Manual Email Fallback</strong>
						</span>
					</text>
					<text>
						<span fg={theme.textDim}>
							Press Tab to switch focus between contributor list and manual input.
						</span>
					</text>

					<input
						value={manualEmail}
						onChange={setManualEmail}
						focused={focusMode === "manual"}
						placeholder="name@example.com"
						width={50}
					/>

					{selectedContributor ? (
						<box marginTop={1} flexDirection="column" gap={1}>
							<text>
								<span fg={theme.textDim}>Current selection</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>
									{selectedContributor.name || selectedContributor.candidate_username}
								</span>
							</text>
							<text>
								<span fg={theme.cyan}>{selectedContributor.email}</span>
							</text>
						</box>
					) : null}
				</box>
			</box>

			<box paddingLeft={2} paddingRight={2} paddingBottom={1} flexDirection="column" gap={1}>
				{state.pipelineNotice ? (
					<text>
						<span fg={theme.warning}>{state.pipelineNotice}</span>
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
