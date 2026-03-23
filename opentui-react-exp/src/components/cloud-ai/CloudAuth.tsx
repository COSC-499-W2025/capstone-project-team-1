/**
 * Auth gate + model picker for the cloud flow.
 *
 * Checks for existing credentials on mount:
 * - If already authenticated → fetches GitHub profile, shows success card + model picker
 * - If not authenticated → renders CopilotLogin (which handles login + model picker)
 */
import { useEffect, useState } from "react";
import { checkAvailableModels, fetchGitHubUser, type GitHubUser } from "../../agent";
import { theme } from "../../types";
import { TopBar } from "../TopBar";
import { CopilotLogin } from "./CopilotLogin";
import { ModelList, type ModelListResult } from "./ModelList";

interface CloudAuthProps {
	onComplete: (result: ModelListResult) => void;
	onBack: () => void;
}

type AuthState = "checking" | "needs-login" | "pick-model";

export function CloudAuth({ onComplete, onBack }: CloudAuthProps) {
	const [state, setState] = useState<AuthState>("checking");
	const [ghUser, setGhUser] = useState<GitHubUser | null>(null);

	useEffect(() => {
		(async () => {
			try {
				const result = await checkAvailableModels();
				if (result.available) {
					try {
						const user = await fetchGitHubUser();
						setGhUser(user);
					} catch {
						// Non-fatal
					}
					setState("pick-model");
				} else {
					setState("needs-login");
				}
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
				user={ghUser}
				onSelect={onComplete}
				onBack={onBack}
			/>
		</box>
	);
}
