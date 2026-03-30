/**
 * Dev harness — renders a single screen in isolation.
 * Usage: bun run src/dev-screen.tsx
 *
 * Change the component below to work on a different screen.
 */
import { createCliRenderer } from "@opentui/core";
import { createRoot } from "@opentui/react";
import { ToastProvider } from "./components/Toast";
import { BottomBar } from "./components/BottomBar";
import { useSelectionCopy } from "./hooks/useSelectionCopy";

// ── swap this import to work on a different screen ──
import { SnakeWithProgress } from "./components/cloud-ai";

function Harness() {
	useSelectionCopy();
	return (
		<box flexGrow={1} flexDirection="column">
			<SnakeWithProgress
				mode="cloud"
				zipPath="/dev/null"
				modelId="claude-haiku-4-5"
				gitIdentity={null}
				onComplete={(profile) => {
					console.log("Profile ready:", profile.developer_dna.archetype);
					process.exit(0);
				}}
				onBack={() => process.exit(0)}
			/>
			<BottomBar
				actions={[
					{ key: "S", label: "Play Snake" },
					{ key: "Enter", label: "View resume" },
					{ key: "Esc", label: "Back" },
				]}
			/>
		</box>
	);
}

const renderer = await createCliRenderer();
createRoot(renderer).render(
	<ToastProvider>
		<Harness />
	</ToastProvider>,
);
