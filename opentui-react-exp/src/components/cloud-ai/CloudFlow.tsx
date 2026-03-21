/**
 * Orchestrator for the cloud AI resume generation flow.
 *
 * Manages sub-screens: CopilotLogin → GenerationProgress → (parent handles resume preview)
 */
import { useState } from "react";
import { checkAvailableModels } from "../../agent";
import { CopilotLogin } from "./CopilotLogin";
import { GenerationProgress } from "./GenerationProgress";

interface CloudFlowProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Step = "auth" | "generate";

export function CloudFlow({ zipPath, onComplete, onBack }: CloudFlowProps) {
	// HACK: skip straight to generation screen for TUI dev
	// TODO: change back to "auth"
	const [step, setStep] = useState<Step>("generate");

	if (step === "auth") {
		return (
			<CopilotLogin
				onComplete={() => setStep("generate")}
				onBack={onBack}
			/>
		);
	}

	return (
		<GenerationProgress
			zipPath={zipPath}
			onComplete={onComplete}
			onBack={() => setStep("auth")}
		/>
	);
}
