import { useEffect, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { api } from "../api/endpoints";
import type { ConsentLevel } from "../api/types";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface ConsentScreenProps {
	onContinue: () => void;
	onBack: () => void;
}

const OPTIONS: ConsentLevel[] = ["local", "local-llm", "cloud"];

export function ConsentScreen({ onContinue, onBack }: ConsentScreenProps) {
	const [selected, setSelected] = useState<ConsentLevel>("local-llm");
	const [saving, setSaving] = useState(false);

	useEffect(() => {
		let ignore = false;
		api.getConsent().then((resp) => {
			if (!ignore && resp.consent_level !== "none") {
				setSelected(resp.consent_level);
			}
		}).catch((err) => { console.error("Failed to load consent:", err); });
		return () => { ignore = true; };
	}, []);

	useKeyboard((key) => {
		if (saving) return;

		if (key.name === "left") {
			setSelected((prev) => {
				const idx = OPTIONS.indexOf(prev);
				return OPTIONS[Math.max(0, idx - 1)];
			});
		}
		if (key.name === "right") {
			setSelected((prev) => {
				const idx = OPTIONS.indexOf(prev);
				return OPTIONS[Math.min(OPTIONS.length - 1, idx + 1)];
			});
		}
		if (key.name === "return") {
			setSaving(true);
			api.updateConsent(selected).then(() => {
				onContinue();
			}).catch(() => {
				setSaving(false);
			});
		}
		if (key.name === "escape") {
			onBack();
		}
	});

	const borderColor = (level: ConsentLevel) =>
		selected === level ? theme.gold : theme.textDim;
	const bgColor = (level: ConsentLevel) =>
		selected === level ? theme.bgMedium : theme.bgDark;
	const titleColor = (level: ConsentLevel) =>
		selected === level ? theme.gold : theme.textSecondary;

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Privacy"
				title="Analysis Mode"
				description="Choose how your project data is processed. All options keep your source code on-device."
			/>

			<box
				flexGrow={1}
				flexDirection="row"
				gap={1}
				paddingTop={1}
				paddingLeft={2}
				paddingRight={2}
				paddingBottom={1}
			>
				{/* ── Panel 1: Local Only ───────────────────────────────────────── */}
				<box
					flexGrow={1}
					flexDirection="column"
					padding={2}
					border
					borderStyle="rounded"
					borderColor={borderColor("local")}
					backgroundColor={bgColor("local")}
					gap={1}
				>
					<text>
						<span fg={titleColor("local")}>
							<strong>Local Only</strong>
						</span>
						<span fg={theme.textDim}>  · pattern-based</span>
					</text>

					<text>
						<span fg={theme.textDim}>
							Reads your repos using static rules.
							No AI model needed or involved.
						</span>
					</text>

					{/* What we read */}
					<box flexDirection="column">
						<text>
							<span fg={theme.cyan}>
								<strong>What we read</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· File &amp; folder names</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Language detection</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Commit count &amp; dates</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Framework fingerprints</span>
						</text>
					</box>

					{/* Privacy */}
					<box flexDirection="column">
						<text>
							<span fg={theme.gold}>
								<strong>Privacy</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>No model required.</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>Zero network calls.</span>
						</text>
						<text>
							<span fg={theme.textDim}>Nothing ever leaves your machine.</span>
						</text>
					</box>

					<box flexDirection="column">
						<text>
							<span fg={theme.success}> + Complete privacy</span>
						</text>
						<text>
							<span fg={theme.success}> + No setup required</span>
						</text>
						<text>
							<span fg={theme.success}> + Works instantly</span>
						</text>
						<text>
							<span fg={theme.warning}> - No AI narratives</span>
						</text>
						<text>
							<span fg={theme.warning}> - Basic skill detection</span>
						</text>
					</box>
				</box>

				{/* ── Panel 2: Local AI ─────────────────────────────────────────── */}
				<box
					flexGrow={1}
					flexDirection="column"
					padding={2}
					border
					borderStyle="rounded"
					borderColor={borderColor("local-llm")}
					backgroundColor={bgColor("local-llm")}
					gap={1}
				>
					<text>
						<span fg={titleColor("local-llm")}>
							<strong>Local AI</strong>
						</span>
						<span fg={theme.textDim}>  · recommended</span>
					</text>

					<text>
						<span fg={theme.textDim}>
							Static analysis plus a small model
							that runs entirely on your device.
						</span>
					</text>

					{/* What we read */}
					<box flexDirection="column">
						<text>
							<span fg={theme.cyan}>
								<strong>What we read</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· README files (up to 2,000 chars)</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Your commit messages</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Folder structure &amp; file names</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Code metrics &amp; skill timeline</span>
						</text>
					</box>

					{/* What AI sees */}
					<box flexDirection="column">
						<text>
							<span fg={theme.gold}>
								<strong>What the AI sees</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>Summaries &amp; metrics only —</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>never your raw source code.</span>
						</text>
						<text>
							<span fg={theme.textDim}>Commit messages only reach the AI</span>
						</text>
						<text>
							<span fg={theme.textDim}>if our classifier can't label them.</span>
						</text>
					</box>

					{/* Where it runs */}
					<box flexDirection="column">
						<text>
							<span fg={theme.gold}>
								<strong>Where it runs</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>A local model on your machine.</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>No cloud. Nothing leaves here.</span>
						</text>
						<text>
							<span fg={theme.textDim}>~/.artifactminer/models/</span>
						</text>
					</box>

					<box flexDirection="column">
						<text>
							<span fg={theme.success}> + Rich AI-generated narratives</span>
						</text>
						<text>
							<span fg={theme.success}> + Smart skill inference</span>
						</text>
						<text>
							<span fg={theme.success}> + Stays fully on-device</span>
						</text>
						<text>
							<span fg={theme.warning}> - ~2 GB model download</span>
						</text>
						<text>
							<span fg={theme.warning}> - Needs available RAM</span>
						</text>
					</box>
				</box>

				{/* ── Panel 3: Cloud ────────────────────────────────────────────── */}
				<box
					flexGrow={1}
					flexDirection="column"
					padding={2}
					border
					borderStyle="rounded"
					borderColor={borderColor("cloud")}
					backgroundColor={bgColor("cloud")}
					gap={1}
				>
					<text>
						<span fg={titleColor("cloud")}>
							<strong>Cloud AI</strong>
						</span>
						<span fg={theme.textDim}>  · coming soon</span>
					</text>

					<text>
						<span fg={theme.textDim}>
							Static analysis plus a cloud model.
							Best quality, no local storage needed.
						</span>
					</text>

					{/* What gets sent */}
					<box flexDirection="column">
						<text>
							<span fg={theme.cyan}>
								<strong>What gets sent</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· File &amp; technology names</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Commit messages</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>· Summaries &amp; metrics</span>
						</text>
						<text>
							<span fg={theme.textDim}>Sent to an external AI service.</span>
						</text>
					</box>

					{/* Privacy note */}
					<box flexDirection="column">
						<text>
							<span fg={theme.gold}>
								<strong>Privacy</strong>
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>Metadata leaves your device.</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>Subject to provider's data policy.</span>
						</text>
						<text>
							<span fg={theme.textDim}>Raw source code is never sent.</span>
						</text>
					</box>

					<box flexDirection="column">
						<text>
							<span fg={theme.success}> + Best quality results</span>
						</text>
						<text>
							<span fg={theme.success}> + No local setup or storage</span>
						</text>
						<text>
							<span fg={theme.warning}> ~ Not yet available</span>
						</text>
						<text>
							<span fg={theme.warning}> - Requires network</span>
						</text>
						<text>
							<span fg={theme.warning}> - Data leaves device</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
