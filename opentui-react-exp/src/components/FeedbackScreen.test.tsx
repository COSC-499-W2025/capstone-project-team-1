import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type { ResumeV3Output } from "../api/types";
import { api } from "../api/endpoints";
import { AppProvider, useAppState } from "../context/AppContext";

type AppContextHookValue = ReturnType<typeof useAppState>;
type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyboardEventLike = { name: string; shift?: boolean };

const originalPolishPipeline = api.polishPipeline;
const originalCancelPipeline = api.cancelPipeline;

let rendered: RenderedScreen | null = null;
let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { FeedbackScreen } = await import("./FeedbackScreen");

const sampleDraft: ResumeV3Output = {
	professional_summary: "Built reliable platform tooling.",
	skills_section: "TypeScript, React, Bun",
	developer_profile: "Engineer focused on developer workflow UX.",
	projects: [],
	metadata: {
		model_used: "llama3",
		models_used: ["llama3"],
		stage: "draft",
		generation_time_seconds: 11,
		errors: [],
		quality_metrics: {},
	},
};

function createHarness(props?: {
	onNext?: (target: string) => void;
}) {
	let context: AppContextHookValue | null = null;

	function Probe() {
		context = useAppState();
		return <FeedbackScreen onNext={props?.onNext ?? (() => {})} />;
	}

	return {
		getContext() {
			if (!context) {
				throw new Error("FeedbackScreen probe did not mount");
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

async function seedFeedbackState(context: AppContextHookValue) {
	act(() => {
		context.setPipelineJobId("job-431");
		context.setResumeV3Draft(sampleDraft);
		context.setPipelineStatus("draft_ready");
		context.setPipelineNotice(null);
	});
	await rendered?.renderOnce();
}

async function typeIntoFocusedInput(text: string) {
	await act(async () => {
		await rendered?.mockInput.typeText(text);
		await rendered?.renderOnce();
	});
}

async function pressKeyboardShortcut(key: KeyboardEventLike) {
	if (!keyboardHandler) {
		throw new Error("FeedbackScreen keyboard handler was not registered");
	}

	await act(async () => {
		keyboardHandler?.(key);
		await Promise.resolve();
		await rendered?.renderOnce();
	});
}

afterEach(() => {
	api.polishPipeline = originalPolishPipeline;
	api.cancelPipeline = originalCancelPipeline;
	destroyRenderer();
});

test("FeedbackScreen renders draft preview and feedback inputs", async () => {
	const harness = createHarness();
	rendered = await testRender(harness.node, { width: 120, height: 36 });
	await seedFeedbackState(harness.getContext());

	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Draft Preview");
	expect(frame).toContain("Feedback Inputs");
	expect(frame).toContain("Built reliable platform tooling.");
	expect(frame).toContain("General Notes");
	expect(frame).toContain("Additions (comma-separated)");
});

test("FeedbackScreen submits polish feedback from keyboard input", async () => {
	const polishCalls: Array<{
		general_notes: string;
		tone: string;
		additions: string[];
		removals: string[];
	}> = [];
	const nextTargets: string[] = [];

	api.polishPipeline = async (request) => {
		polishCalls.push(request);
		return { ok: true, status: "polishing" };
	};

	const harness = createHarness({
		onNext: (target) => {
			nextTargets.push(target);
		},
	});
	rendered = await testRender(harness.node, { width: 120, height: 36 });
	await seedFeedbackState(harness.getContext());

	await typeIntoFocusedInput("Need stronger metrics");
	await pressKeyboardShortcut({ name: "tab" });
	await typeIntoFocusedInput("more technical");
	await pressKeyboardShortcut({ name: "tab" });
	await typeIntoFocusedInput("led migration,shipped cli");
	await pressKeyboardShortcut({ name: "tab" });
	await typeIntoFocusedInput("old-claim,vague-summary");
	await pressKeyboardShortcut({ name: "return" });

	expect(polishCalls).toEqual([
		{
			general_notes: "Need stronger metrics",
			tone: "more technical",
			additions: ["led migration", "shipped cli"],
			removals: [],
		},
	]);
	expect(nextTargets).toEqual(["analysis"]);
});

test("FeedbackScreen cancels the pipeline and updates app state", async () => {
	let cancelCount = 0;
	const nextTargets: string[] = [];

	api.cancelPipeline = async () => {
		cancelCount += 1;
		return { ok: true, status: "cancelled" };
	};

	const harness = createHarness({
		onNext: (target) => {
			nextTargets.push(target);
		},
	});
	rendered = await testRender(harness.node, { width: 120, height: 36 });
	await seedFeedbackState(harness.getContext());

	await pressKeyboardShortcut({ name: "escape" });

	expect(cancelCount).toBe(1);
	expect(nextTargets).toEqual(["project-list"]);
	expect(harness.getContext().state.pipelineStatus).toBe("cancelled");
	expect(harness.getContext().state.pipelineNotice).toBe(
		"Pipeline cancelled from feedback screen.",
	);
});
