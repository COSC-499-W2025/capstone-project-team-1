import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import { api } from "../api/endpoints";
import type { ResumeV3Output } from "../api/types";
import { AppProvider, useAppState } from "../context/AppContext";

type AppContextHookValue = ReturnType<typeof useAppState>;
type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyboardEventLike = { name: string; sequence?: string; shift?: boolean };

const originalPolishPipeline = api.polishPipeline;
const originalCancelPipeline = api.cancelPipeline;

let rendered: RenderedScreen | null = null;
let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { DraftPauseScreen } = await import("./DraftPauseScreen");

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

function createHarness(props?: { onNext?: (target: string) => void }) {
	let context: AppContextHookValue | null = null;

	function Probe() {
		context = useAppState();
		return <DraftPauseScreen onNext={props?.onNext ?? (() => {})} />;
	}

	return {
		getContext() {
			if (!context) {
				throw new Error("DraftPauseScreen probe did not mount");
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

async function seedDraftState(context: AppContextHookValue) {
	act(() => {
		context.setPipelineJobId("job-430");
		context.setResumeV3Draft(sampleDraft);
		context.setPipelineStatus("draft_ready");
		context.setPipelineNotice(null);
	});
	await rendered?.renderOnce();
}

async function pressKeyboardShortcut(key: KeyboardEventLike) {
	if (!keyboardHandler) {
		throw new Error("DraftPauseScreen keyboard handler was not registered");
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

test("DraftPauseScreen renders the paused draft review layout", async () => {
	const harness = createHarness();
	rendered = await testRender(harness.node, { width: 140, height: 40 });
	await seedDraftState(harness.getContext());

	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Stage 2 Pause");
	expect(frame).toContain("Sections");
	expect(frame).toContain("Feedback");
	expect(frame).toContain("Built reliable platform tooling.");
	expect(frame).toContain("General Notes");
});

test("DraftPauseScreen moves between draft sections with arrow keys", async () => {
	const harness = createHarness();
	rendered = await testRender(harness.node, { width: 140, height: 40 });
	await seedDraftState(harness.getContext());

	expect(rendered.captureCharFrame()).toContain(
		"Built reliable platform tooling.",
	);

	await pressKeyboardShortcut({ name: "down" });

	const frame = rendered.captureCharFrame();
	expect(frame).toContain("TypeScript, React, Bun");
	expect(frame).toContain("TECHNICAL SKILLS");
});

test("DraftPauseScreen cancels the pipeline and updates app state", async () => {
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
	rendered = await testRender(harness.node, { width: 140, height: 40 });
	await seedDraftState(harness.getContext());

	await pressKeyboardShortcut({ name: "escape" });

	expect(cancelCount).toBe(1);
	expect(nextTargets).toEqual(["project-list"]);
	expect(harness.getContext().state.pipelineStatus).toBe("cancelled");
	expect(harness.getContext().state.pipelineNotice).toBe(
		"Pipeline cancelled at draft pause.",
	);
});
