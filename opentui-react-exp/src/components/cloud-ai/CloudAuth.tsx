/**
 * Standalone auth gate for the cloud flow.
 *
 * Checks for existing credentials on mount — if already authenticated,
 * fires onComplete immediately.  Otherwise renders CopilotLogin.
 */
import { useEffect, useState } from "react";
import { checkAvailableModels } from "../../agent";
import { CopilotLogin } from "./CopilotLogin";

interface CloudAuthProps {
	onComplete: () => void;
	onBack: () => void;
}

type AuthState = "checking" | "needs-login" | "done";

export function CloudAuth({ onComplete, onBack }: CloudAuthProps) {
	const [state, setState] = useState<AuthState>("checking");

	useEffect(() => {
		(async () => {
			try {
				const result = await checkAvailableModels();
				if (result.available) {
					onComplete();
				} else {
					setState("needs-login");
				}
			} catch {
				setState("needs-login");
			}
		})();
	}, []);

	if (state === "checking") return null;

	return <CopilotLogin onComplete={onComplete} onBack={onBack} />;
}
