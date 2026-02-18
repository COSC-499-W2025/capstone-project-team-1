import { useKeyboard } from "@opentui/react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface ConsentPolicyScreenProps {
	onContinue: () => void;
	onBack: () => void;
}

export function ConsentScreen({
	onContinue,
	onBack,
}: ConsentPolicyScreenProps) {
	useKeyboard((key) => {
		if (key.name === "return" || key.name === "enter") {
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
				description="This prototype runs only on your machine."
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
					<text>
						<span fg={theme.gold}>
							<strong>Local-Only Processing</strong>
						</span>
					</text>

					<text>
						<span fg={theme.textSecondary}>
							Your ZIP, repositories, logs, and generated resume stay on this machine
							during this run.
						</span>
					</text>

					<text>
						<span fg={theme.success}>+ No cloud routing in this flow</span>
					</text>
					<text>
						<span fg={theme.success}>
							+ One intake ZIP and one ephemeral job state per run
						</span>
					</text>
					<text>
						<span fg={theme.success}>
							+ Escape can hard-cancel backend processing
						</span>
					</text>

					<box marginTop={1}>
						<text>
							<span fg={theme.textDim}>
								By continuing, you confirm local processing for this prototype run.
							</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
