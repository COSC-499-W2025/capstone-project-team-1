/**
 * Cloud AI resume generation flow.
 *
 * Auth is handled earlier (CloudAuth screen), so this component
 * goes straight to generation via SnakeWithProgress.
 */
import { SnakeWithProgress } from "./SnakeWithProgress";

interface CloudFlowProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

export function CloudFlow({ zipPath, onComplete, onBack }: CloudFlowProps) {
	return (
		<SnakeWithProgress
			zipPath={zipPath}
			onComplete={onComplete}
			onBack={onBack}
		/>
	);
}
