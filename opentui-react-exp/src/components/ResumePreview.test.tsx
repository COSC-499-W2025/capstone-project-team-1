import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act, useEffect, useState } from "react";
import type { ResumeV3Output } from "../api/types";
import { AppProvider, useAppState } from "../context/AppContext";

type AppContextHookValue = ReturnType<typeof useAppState>;
type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyboardEventLike = { name: string; shift?: boolean };

let rendered: RenderedScreen | null = null;
let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;
const originalBunWrite = Bun.write;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { ResumePreview } = await import("./ResumePreview");

const draftResume: ResumeV3Output = {
	professional_summary: "Draft summary focused on early pipeline output.",
	skills_section: "TypeScript, Bun, OpenTUI",
	developer_profile: "Draft developer profile.",
	projects: [
		{
			name: "artifact-miner",
			type: "CLI Tool",
			primary_language: "TypeScript",
			frameworks: ["Bun"],
			contribution_pct: 80,
			commit_breakdown: { author: 50 },
			period: {
				first_commit: "2025-01-01",
				last_commit: "2025-02-01",
			},
			description: "Draft project description.",
			bullets: ["Built pipeline scaffolding"],
			narrative: "Draft narrative",
		},
	],
	metadata: {
		model_used: "qwen",
		models_used: ["qwen", "lfm"],
		stage: "draft",
		generation_time_seconds: 9.5,
		errors: [],
		quality_metrics: {},
	},
	portfolio: {
		total_projects: 1,
		total_commits: 50,
		languages_used: ["TypeScript"],
		frameworks_used: ["Bun"],
		project_types: { "CLI Tool": 1 },
		top_skills: ["TypeScript"],
	},
};

const finalResume: ResumeV3Output = {
	professional_summary: "Final summary with polished impact statements.",
	skills_section: "TypeScript, React, Bun",
	developer_profile: "Final developer profile.",
	projects: [
		{
			name: "artifact-miner",
			type: "CLI Tool",
			primary_language: "TypeScript",
			frameworks: ["Bun", "React"],
			contribution_pct: 92,
			commit_breakdown: { author: 70 },
			period: {
				first_commit: "2025-01-01",
				last_commit: "2025-03-01",
			},
			description: "Final project description.",
			bullets: ["Shipped resume preview rewrite"],
			narrative: "Final narrative",
		},
	],
	metadata: {
		model_used: "lfm",
		models_used: ["qwen", "lfm"],
		stage: "final",
		generation_time_seconds: 12.3,
		errors: [],
		quality_metrics: {},
	},
	portfolio: {
		total_projects: 1,
		total_commits: 70,
		languages_used: ["TypeScript", "TSX"],
		frameworks_used: ["Bun", "React"],
		project_types: { "CLI Tool": 1 },
		top_skills: ["TypeScript", "React"],
	},
};

function createHarness(props?: {
	onPolishAgain?: () => void;
	onRestart?: () => void;
	onExit?: () => void;
}) {
	let context: AppContextHookValue | null = null;

	function Probe() {
		context = useAppState();
		const [ready, setReady] = useState(false);

		useEffect(() => {
			context?.setResumeV3Draft(draftResume);
			context?.setResumeV3Output(finalResume);
			setReady(true);
		}, []);

		if (!ready) {
			return <box />;
		}

		return (
			<ResumePreview
				onPolishAgain={props?.onPolishAgain ?? (() => {})}
				onRestart={props?.onRestart ?? (() => {})}
				onExit={props?.onExit ?? (() => {})}
			/>
		);
	}

	return {
		getContext() {
			if (!context) {
				throw new Error("ResumePreview probe did not mount");
			}
			return context;
		},
		node: (
			<AppProvider>
				<Probe />
			</AppProvider>
		),
	};
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

async function seedPreviewState(_context: AppContextHookValue) {
	await rendered?.renderOnce();
	await Promise.resolve();
	await rendered?.renderOnce();
}

async function pressKeyboardShortcut(key: KeyboardEventLike) {
	if (!keyboardHandler) {
		throw new Error("ResumePreview keyboard handler was not registered");
	}

	await act(async () => {
		keyboardHandler?.(key);
		await Promise.resolve();
		await rendered?.renderOnce();
	});
}

afterEach(() => {
	Bun.write = originalBunWrite;
	destroyRenderer();
});

test("ResumePreview renders final output by default with section stats", async () => {
	const harness = createHarness();
	rendered = await testRender(harness.node, { width: 120, height: 40 });
	await seedPreviewState(harness.getContext());

	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Preview");
	expect(frame).toContain("Final");
	expect(frame).toContain("Final summary with polished impact statements.");
	expect(frame).toContain("Projects: 1");
	expect(frame).toContain("Stage: final");
});

test("ResumePreview cycles modes and supports section keyboard navigation", async () => {
	const harness = createHarness();
	rendered = await testRender(harness.node, { width: 120, height: 40 });
	await seedPreviewState(harness.getContext());

	await pressKeyboardShortcut({ name: "tab" });
	let frame = rendered.captureCharFrame();
	expect(frame).toContain("Draft");
	expect(frame).toContain("Draft → Final");

	await pressKeyboardShortcut({ name: "tab" });
	frame = rendered.captureCharFrame();
	expect(frame).toContain("Draft summary focused on early pipeline output.");

	await pressKeyboardShortcut({ name: "3" });
	frame = rendered.captureCharFrame();
	expect(frame).toContain("PROJECTS");
	expect(frame).toContain("artifact-miner");
	expect(frame).toContain("Built pipeline scaffolding");

	await pressKeyboardShortcut({ name: "down" });
	frame = rendered.captureCharFrame();
	expect(frame).toContain("DEVELOPER PROFILE");

	await pressKeyboardShortcut({ name: "up" });
	frame = rendered.captureCharFrame();
	expect(frame).toContain("PROJECTS");
});

test("ResumePreview keybindings save and invoke action callbacks", async () => {
	let polishCount = 0;
	let restartCount = 0;
	let exitCount = 0;
	const writeCalls: Array<{ path: string; text: string }> = [];

	Bun.write = (async (path, data) => {
		writeCalls.push({
			path: String(path),
			text: String(data),
		});
		return 1;
	}) as typeof Bun.write;

	const harness = createHarness({
		onPolishAgain: () => {
			polishCount += 1;
		},
		onRestart: () => {
			restartCount += 1;
		},
		onExit: () => {
			exitCount += 1;
		},
	});
	rendered = await testRender(harness.node, { width: 120, height: 40 });
	await seedPreviewState(harness.getContext());

	await pressKeyboardShortcut({ name: "s" });
	await pressKeyboardShortcut({ name: "p" });
	await pressKeyboardShortcut({ name: "r" });
	await pressKeyboardShortcut({ name: "escape" });

	expect(writeCalls).toHaveLength(1);
	expect(writeCalls[0]).toEqual({
		path: "./artifact-miner-resume.md",
		text: expect.stringContaining("Final summary with polished impact statements."),
	});
	expect(rendered.captureCharFrame()).toContain(
		"Saved to ./artifact-miner-resume.md",
	);
	expect(polishCount).toBe(1);
	expect(restartCount).toBe(1);
	expect(exitCount).toBe(1);
});
