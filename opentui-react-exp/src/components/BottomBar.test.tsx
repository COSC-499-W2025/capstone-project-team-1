import { expect, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act, type ReactNode } from "react";
import { BottomBar } from "./BottomBar";

async function renderBottomBar(node: ReactNode) {
	const rendered = await testRender(node, { width: 100, height: 3 });

	await act(async () => {
		await rendered.renderOnce();
	});

	return rendered;
}

test("BottomBar hides shortcut hints when no actions are provided", async () => {
	const rendered = await renderBottomBar(<BottomBar actions={[]} />);
	const frame = rendered.captureCharFrame();

	expect(frame).not.toContain("Enter");
	expect(frame).not.toContain("Get Started");
	expect(frame).not.toContain("Esc");

	await act(async () => {
		rendered.renderer.destroy();
	});
});

test("BottomBar only shows the forward CTA when a screen opts into it", async () => {
	const withoutForward = await renderBottomBar(
		<BottomBar actions={[{ key: "Enter", label: "Continue" }]} />,
	);

	expect(withoutForward.captureCharFrame()).not.toContain("Analyze");

	await act(async () => {
		withoutForward.renderer.destroy();
	});

	const withForward = await renderBottomBar(
		<BottomBar
			actions={[{ key: "Enter", label: "Continue" }]}
			onForward={() => {}}
			forwardLabel="Analyze"
		/>,
	);

	expect(withForward.captureCharFrame()).toContain("Analyze");

	await act(async () => {
		withForward.renderer.destroy();
	});
});

test("BottomBar renders an optional hint alongside breadcrumbs", async () => {
	const rendered = await renderBottomBar(
		<BottomBar
			actions={[{ key: "Enter", label: "Continue" }]}
			hint="Select at least one repository before continuing."
			breadcrumbs={[
				{ screen: "consent", label: "Consent", visited: true },
				{ screen: "project-list", label: "Repos", visited: true },
			]}
			currentScreen="project-list"
		/>,
	);

	const frame = rendered.captureCharFrame();
	expect(frame).toContain("Consent");
	expect(frame).toContain("Repos");
	expect(frame).toContain("Select at least one repository");

	await act(async () => {
		rendered.renderer.destroy();
	});
});
