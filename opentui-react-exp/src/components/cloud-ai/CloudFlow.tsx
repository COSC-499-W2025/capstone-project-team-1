/**
 * Cloud AI resume generation flow.
 *
 * Auth and model selection are handled earlier (CloudAuth / ConfigureScreen),
 * so this component goes straight to generation via SnakeWithProgress.
 */
import type { DeveloperProfile } from "../../api/types";
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
	selectedRepoPaths: string[];
	onComplete: (profile: DeveloperProfile) => void;
	onBack: () => void;
}

export function CloudFlow({ zipPath, modelId, gitIdentity, selectedRepoPaths, onComplete, onBack }: CloudFlowProps) {
	return (
		<SnakeWithProgress
			mode="cloud"
			zipPath={zipPath}
			modelId={modelId}
			gitIdentity={gitIdentity}
			selectedRepoPaths={selectedRepoPaths}
			onComplete={onComplete}
			onBack={onBack}
		/>
	);
}
