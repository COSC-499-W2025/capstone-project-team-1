/**
 * Auth gate + model picker for the cloud flow.
 *
 * Checks for existing credentials on mount:
 * - If already authenticated → shows success card + model picker
 * - If not authenticated → renders CopilotLogin (which shows model picker after login)
 */
import { useEffect, useState } from "react";
import { checkAvailableModels } from "../../agent";
import { theme } from "../../types";
import { TopBar } from "../TopBar";
import { CopilotLogin } from "./CopilotLogin";
import { ModelList } from "./ModelList";

interface CloudAuthProps {
	onComplete: (modelId: string) => void;
	onBack: () => void;
}

type AuthState = "checking" | "needs-login" | "pick-model";

export function CloudAuth({ onComplete, onBack }: CloudAuthProps) {
	const [state, setState] = useState<AuthState>("checking");

	useEffect(() => {
		(async () => {
			try {
				const result = await checkAvailableModels();
				setState(result.available ? "pick-model" : "needs-login");
			} catch {
				setState("needs-login");
			}
		})();
	}, []);

	if (state === "checking") return null;

	if (state === "needs-login") {
		return <CopilotLogin onComplete={onComplete} onBack={onBack} />;
	}

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="GitHub Copilot Login"
				description="Sign in with your GitHub account to use AI-powered resume generation."
			/>
			<ModelList
				successMessage="✓ Already logged in to GitHub Copilot"
				onSelect={onComplete}
				onBack={onBack}
			/>
		</box>
	);
}
