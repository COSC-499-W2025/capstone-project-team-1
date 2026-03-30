import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type { DeveloperProfile } from "../api/types";

type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyboardEventLike = { name: string };

let rendered: RenderedScreen | null = null;
let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { CloudResumePreview } = await import("./CloudResumePreview");

const sampleProfile: DeveloperProfile = {
	resume_markdown: "# Resume\n\nBuilt resilient frontend workflows.",
	developer_dna: {
		archetype: "Systems Builder",
		description: "Finds the stable seam and builds around it.",
		defining_traits: ["Pragmatic", "Evidence-driven"],
	},
	hidden_strengths: [
		{
			observation: "Keeps migrations incremental.",
			evidence: "Lifted orchestration into shared app state.",
			why_it_matters: "Reduces regression surface during feature work.",
		},
	],
	growth_areas: [],
	talking_points: [],
	impact: {
		commits: {
			total: 24,
			avg_per_week: 2.5,
			most_active_period: "2025-Q1",
			conventional_commits_pct: 40,
		},
		languages: [],
		collaboration: {
			branch_count: 2,
			merge_frequency: "weekly",
			workflow_style: "small iterative PRs",
		},
		complexity: {
			frameworks_used: 2,
			project_types: ["CLI"],
			distinct_tools: ["Bun"],
		},
	},
	projects: [],
};

async function pressKeyboardShortcut(key: KeyboardEventLike) {
	if (!keyboardHandler) {
		throw new Error("CloudResumePreview keyboard handler was not registered");
	}

	await act(async () => {
		keyboardHandler?.(key);
		await Promise.resolve();
	});
	await rendered?.renderOnce();
}

async function pressKeyboardShortcutTwiceWithoutRerender(
	key: KeyboardEventLike,
) {
	if (!keyboardHandler) {
		throw new Error("CloudResumePreview keyboard handler was not registered");
	}

	await act(async () => {
		keyboardHandler?.(key);
		keyboardHandler?.(key);
		await Promise.resolve();
	});
	await rendered?.renderOnce();
}

function destroyRenderer() {
	if (!rendered) {
		return;
	}

	act(() => {
		rendered?.renderer.destroy();
	});
	rendered = null;
	keyboardHandler = null;
}

afterEach(() => {
	destroyRenderer();
});

test("CloudResumePreview renders the portfolio button and shortcut hint", async () => {
	rendered = await testRender(
		<CloudResumePreview
			profile={sampleProfile}
			onOpenPortfolio={() => {}}
			isOpeningPortfolio={false}
			portfolioStatusMessage={null}
		/>,
		{ width: 120, height: 40 },
	);
	await rendered.renderOnce();

	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Press o");
	expect(frame).toContain("Portfolio");
	expect(frame).toContain("HTML");
	expect(frame).toContain("Developer Profile");
});

test("CloudResumePreview calls onOpenPortfolio on o and blocks duplicate triggers while busy", async () => {
	let openCount = 0;

	rendered = await testRender(
		<CloudResumePreview
			profile={sampleProfile}
			onOpenPortfolio={() => {
				openCount += 1;
			}}
			isOpeningPortfolio={false}
			portfolioStatusMessage={null}
		/>,
		{ width: 120, height: 40 },
	);
	await rendered.renderOnce();
	await pressKeyboardShortcut({ name: "o" });

	expect(openCount).toBe(1);

	destroyRenderer();

	rendered = await testRender(
		<CloudResumePreview
			profile={sampleProfile}
			onOpenPortfolio={() => {
				openCount += 1;
			}}
			isOpeningPortfolio={true}
			portfolioStatusMessage="Generating portfolio HTML..."
		/>,
		{ width: 120, height: 40 },
	);
	await rendered.renderOnce();
	await pressKeyboardShortcut({ name: "o" });

	expect(openCount).toBe(1);
	expect(rendered.captureCharFrame()).toContain("Generating portfolio HTML...");
	expect(rendered.captureCharFrame()).toContain("Generating...");
});

test("CloudResumePreview blocks same-tick duplicate open shortcuts before busy props rerender", async () => {
	let openCount = 0;

	rendered = await testRender(
		<CloudResumePreview
			profile={sampleProfile}
			onOpenPortfolio={() => {
				openCount += 1;
			}}
			isOpeningPortfolio={false}
			portfolioStatusMessage={null}
		/>,
		{ width: 120, height: 40 },
	);
	await rendered.renderOnce();
	await pressKeyboardShortcutTwiceWithoutRerender({ name: "o" });

	expect(openCount).toBe(1);
});
