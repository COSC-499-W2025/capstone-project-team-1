/**
 * Auth gate for the cloud flow.
 *
 * Checks for existing credentials on mount:
 * - If already authenticated → auto-completes with default model + user info, skips ahead
 * - If not authenticated → renders CopilotLogin until auth succeeds, then auto-completes
 *
 * Model selection and email entry happen in ConfigureScreen (the unified flow).
 */
import { useCallback, useEffect, useState } from "react";
import {
	checkAvailableModels,
	fetchGitHubUser,
	type GitHubUser,
} from "../../agent";
import { CopilotLogin } from "./CopilotLogin";
import { DEFAULT_MODEL_ID } from "./ModelPicker";
import type { ModelListResult } from "./ModelList";

interface CloudAuthProps {
	onComplete: (result: ModelListResult) => void;
	onBack: () => void;
}

type AuthState = "checking" | "needs-login" | "completing";

export function CloudAuth({ onComplete, onBack }: CloudAuthProps) {
	const [state, setState] = useState<AuthState>("checking");

	const completeWithUser = useCallback(
		(user: GitHubUser | null) => {
			onComplete({
				modelId: DEFAULT_MODEL_ID,
				gitIdentity: {
					login: user?.login ?? "",
					name: user?.name ?? null,
					email: user?.email ?? "",
				},
			});
		},
		[onComplete],
	);

	useEffect(() => {
		(async () => {
			try {
				const result = await checkAvailableModels();
				if (result.hasCopilot) {
					// Already authenticated → fetch user and skip ahead
					setState("completing");
					let user: GitHubUser | null = null;
					try {
						user = await fetchGitHubUser();
					} catch {
						// Non-fatal — proceed without user info
					}
					completeWithUser(user);
				} else {
					setState("needs-login");
				}
			} catch {
				setState("needs-login");
			}
		})();
	}, [completeWithUser]);

	// While checking or completing, render nothing (instant transition)
	if (state === "checking" || state === "completing") return null;

	// Not authenticated — show login flow
	return (
		<CopilotLogin
			onLoginSuccess={(user) => {
				completeWithUser(user);
			}}
			onBack={onBack}
		/>
	);
}
