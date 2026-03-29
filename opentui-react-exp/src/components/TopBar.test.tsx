import { expect, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act, type ReactNode } from "react";
import { TopBar } from "./TopBar";

async function renderTopBar(node: ReactNode) {
	const rendered = await testRender(node, { width: 100, height: 5 });

	await act(async () => {
		await rendered.renderOnce();
	});

	return rendered;
}

test("TopBar renders the combined step and title header", async () => {
	const rendered = await renderTopBar(
		<TopBar
			step="Draft"
			title="Stage 2 Pause"
			description="Review the draft, add feedback, then submit for polish"
		/>,
	);

	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Draft | Stage 2 Pause");
	expect(frame).toContain(
		"Review the draft, add feedback, then submit for polish",
	);

	await act(async () => {
		rendered.renderer.destroy();
	});
});

test("TopBar omits the separator when no step is provided", async () => {
	const rendered = await renderTopBar(
		<TopBar
			title="Consent"
			description="Choose how you'd like your data to be processed."
		/>,
	);

	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Consent");
	expect(frame).not.toContain(" | Consent");
	expect(frame).toContain("Choose how you'd like your data to be processed.");

	await act(async () => {
		rendered.renderer.destroy();
	});
});
