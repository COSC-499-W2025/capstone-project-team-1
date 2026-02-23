import { useEffect, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface ConsentPolicyScreenProps {
	onContinue: () => void;
	onBack: () => void;
	onHintChange: (hint: string) => void;
}

export function ConsentScreen({
	onContinue,
	onBack,
	onHintChange,
}: ConsentPolicyScreenProps) {
	const [checked, setChecked] = useState(false);

	useEffect(() => {
		onHintChange(
			checked
				? "You're all set — press Enter to continue"
				: "Check the box to confirm you're happy to proceed",
		);
	}, [checked, onHintChange]);

	useKeyboard((key) => {
		if (key.name === "space") {
			setChecked((prev) => !prev);
		}
		if ((key.name === "return" || key.name === "enter") && checked) {
			onContinue();
		}
		if (key.name === "escape") {
			onBack();
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Policy"
				title="Local Processing Consent"
				description="Everything stays on your machine — here's exactly what happens."
			/>

			<box flexGrow={1} justifyContent="center" alignItems="center" padding={2}>
				<box
					width={88}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					gap={1}
				>
					{/* Intro */}
					<text>
						<span fg={theme.textSecondary}>
							We read your repos locally, run a small AI model on your machine,
							and hand you a resume. Nothing leaves your device.
						</span>
					</text>

					{/* Two mini-cards */}
					<box flexDirection="row" gap={2} marginTop={1}>
						{/* Left card: What we read */}
						<box
							flexGrow={1}
							flexDirection="column"
							border
							borderStyle="rounded"
							borderColor={theme.cyanDim}
							padding={1}
							gap={1}
						>
							<text>
								<span fg={theme.cyan}>
									<strong>What we read</strong>
								</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>
									· README files (up to 2,000 chars)
								</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>· Your commit messages</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>
									· Folder structure & file names
								</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>
									· Code metrics & skill timeline
								</span>
							</text>
						</box>

						{/* Right card: What AI sees + Where it runs */}
						<box
							flexGrow={1}
							flexDirection="column"
							border
							borderStyle="rounded"
							borderColor={theme.goldDim}
							padding={1}
							gap={1}
						>
							<text>
								<span fg={theme.gold}>
									<strong>What the AI sees</strong>
								</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>
									Summaries & metrics only — never
								</span>
							</text>
							<text>
								<span fg={theme.textSecondary}>your raw source code.</span>
							</text>
							<text>
								<span fg={theme.textDim}>
									Commit messages only reach the AI
								</span>
							</text>
							<text>
								<span fg={theme.textDim}>
									if our classifier can't label them.
								</span>
							</text>

							<box marginTop={1} flexDirection="column" gap={1}>
								<text>
									<span fg={theme.gold}>
										<strong>Where it runs</strong>
									</span>
								</text>
								<text>
									<span fg={theme.textSecondary}>
										A local model on your machine.
									</span>
								</text>
								<text>
									<span fg={theme.textSecondary}>
										No cloud. Nothing leaves here.
									</span>
								</text>
								<text>
									<span fg={theme.textDim}>~/.artifactminer/models/</span>
								</text>
							</box>
						</box>
					</box>

					{/* Checkbox */}
					<box marginTop={1} flexDirection="row" gap={1}>
						<text>
							<span fg={checked ? theme.success : theme.textDim}>
								{checked ? "[✓]" : "[ ]"}
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>
								{"  "}I'm happy for this run to process my repos locally.
							</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
