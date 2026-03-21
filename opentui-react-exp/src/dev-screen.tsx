/**
 * Dev harness — renders a single screen in isolation.
 * Usage: bun run src/dev-screen.tsx
 *
 * Change the component below to work on any screen.
 */
import { createCliRenderer } from "@opentui/core";
import { createRoot } from "@opentui/react";
import { ToastProvider } from "./components/Toast";
import { useSelectionCopy } from "./hooks/useSelectionCopy";

// ── swap this import to work on a different screen ──
import { GenerationProgress } from "./components/cloud-ai";

function Harness() {
	useSelectionCopy();
	return (
		<GenerationProgress
			zipPath="/dev/null"
			onComplete={(md) => console.log("DONE:", md.slice(0, 80))}
			onBack={() => process.exit(0)}
		/>
	);
}

const renderer = await createCliRenderer();
createRoot(renderer).render(
	<ToastProvider>
		<Harness />
	</ToastProvider>,
);
