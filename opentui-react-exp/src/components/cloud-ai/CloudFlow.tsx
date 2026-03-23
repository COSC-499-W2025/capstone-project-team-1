/**
 * Cloud AI resume generation flow.
 *
 * Auth and model selection are handled earlier (CloudAuth screen),
 * so this component goes straight to generation via SnakeWithProgress.
 */
import { SnakeWithProgress } from "./SnakeWithProgress";

interface CloudFlowProps {
	zipPath: string;
	modelId: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

export function CloudFlow({ zipPath, modelId, onComplete, onBack }: CloudFlowProps) {
	return (
		<SnakeWithProgress
			zipPath={zipPath}
			modelId={modelId}
			onComplete={onComplete}
			onBack={onBack}
		/>
	);
}
