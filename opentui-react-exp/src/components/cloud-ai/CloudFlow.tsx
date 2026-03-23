/**
 * Cloud AI resume generation flow.
 *
 * Auth and model selection are handled earlier (CloudAuth screen),
 * so this component goes straight to generation via SnakeWithProgress.
 */
import { SnakeWithProgress } from "./SnakeWithProgress";

interface GitIdentity {
	login: string;
	name: string | null;
	email: string;
}

interface CloudFlowProps {
	zipPath: string;
	modelId: string;
	gitIdentity: GitIdentity | null;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

export function CloudFlow({ zipPath, modelId, gitIdentity, onComplete, onBack }: CloudFlowProps) {
	return (
		<SnakeWithProgress
			zipPath={zipPath}
			modelId={modelId}
			gitIdentity={gitIdentity}
			onComplete={onComplete}
			onBack={onBack}
		/>
	);
}
