/**
 * Orchestrator for the cloud AI resume generation flow.
 *
 * CopilotLogin → SnakeWithProgress → (parent handles resume preview)
 *
 * Checks for existing auth on mount — skips login if already authenticated.
 */
import { useEffect, useState } from "react";
import { checkAvailableModels } from "../../agent";
import { CopilotLogin } from "./CopilotLogin";
import { SnakeWithProgress } from "./SnakeWithProgress";

interface CloudFlowProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Step = "checking" | "auth" | "generate";

export function CloudFlow({ zipPath, onComplete, onBack }: CloudFlowProps) {
	const [step, setStep] = useState<Step>("checking");

	// Check if already authenticated on mount
	useEffect(() => {
		(async () => {
			try {
				const result = await checkAvailableModels();
				setStep(result.available ? "generate" : "auth");
			} catch {
				setStep("auth");
			}
		})();
	}, []);

	if (step === "checking") return null;

	if (step === "auth") {
		return (
			<CopilotLogin
				onComplete={() => setStep("generate")}
				onBack={onBack}
			/>
		);
	}

	return (
		<SnakeWithProgress
			zipPath={zipPath}
			onComplete={onComplete}
			onBack={() => setStep("auth")}
		/>
	);
}
