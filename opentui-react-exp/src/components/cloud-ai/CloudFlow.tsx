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
	const [step, setStep] = useState<Step>("auth");

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
