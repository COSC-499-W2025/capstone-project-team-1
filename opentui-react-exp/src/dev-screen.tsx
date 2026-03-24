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

// ── swap this import to work on a different screen ──
import { CloudAuth } from "./components/cloud-ai";

function Harness() {
	return (
		<box flexGrow={1} flexDirection="column">
			<CloudAuth
				onComplete={(result) => {
					console.log("Auth complete:", result.modelId, result.gitIdentity?.login);
					process.exit(0);
				}}
				onBack={() => process.exit(0)}
			/>
			<BottomBar
				actions={[
					{ key: "Enter", label: "Confirm" },
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
