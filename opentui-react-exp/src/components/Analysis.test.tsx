import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type { PipelineStatusResponse, ResumeV3Output } from "../api/types";
import { api } from "../api/endpoints";
import { AppProvider, useAppState } from "../context/AppContext";

type AppContextHookValue = ReturnType<typeof useAppState>;
type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyboardEventLike = { name: string };

const originalGetPipelineStatus = api.getPipelineStatus;
const originalCancelPipeline = api.cancelPipeline;
const originalSetInterval = globalThis.setInterval;
const originalClearInterval = globalThis.clearInterval;

let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { Analysis } = await import("./Analysis");

const sampleDraft: ResumeV3Output = {
	professional_summary: "Built a migration-safe analysis flow.",
	skills_section: "TypeScript, React, Bun",
	developer_profile: "Engineer focused on stable frontend migrations.",
	projects: [],
	metadata: {
		model_used: "llama3",
		models_used: ["llama3"],
		stage: "draft",
		generation_time_seconds: 12,
		errors: [],
		quality_metrics: {},
	},
};

function createHarness(props?: {
	onNext?: (target: string) => void;
	onComplete?: () => void;
	onBack?: () => void;
}) {
	let context: AppContextHookValue | null = null;

	function Probe() {
		context = useAppState();
		return (
			<Analysis
				onNext={props?.onNext}
				onComplete={props?.onComplete}
				onBack={props?.onBack}
			/>
		);
	}

	return {
		getContext() {
			if (!context) {
				throw new Error("Analysis probe did not mount");
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

async function flushEffects(rendered: RenderedScreen) {
	await act(async () => {
		await Promise.resolve();
		await Promise.resolve();
		await rendered.renderOnce();
	});
}

function destroyRenderer(rendered: RenderedScreen | null) {
	if (!rendered) {
		return;
	}
	act(() => {
		rendered.renderer.destroy();
	});
}

function freezeIntervals() {
	globalThis.setInterval = ((_: TimerHandler, __?: number) => 1) as unknown as typeof setInterval;
	globalThis.clearInterval = ((_: number) => {}) as unknown as typeof clearInterval;
}

afterEach(() => {
	api.getPipelineStatus = originalGetPipelineStatus;
	api.cancelPipeline = originalCancelPipeline;
	globalThis.setInterval = originalSetInterval;
	globalThis.clearInterval = originalClearInterval;
	keyboardHandler = null;
});

test("Analysis polls status, updates app state, and routes draft_ready to draft-pause", async () => {
	freezeIntervals();
	const nextTargets: string[] = [];
	let rendered: RenderedScreen | null = null;

	const draftReadyResponse: PipelineStatusResponse = {
		status: "draft_ready",
		stage: "DRAFT",
		messages: ["Draft assembled from telemetry facts."],
		telemetry: {
			stage: "DRAFT",
			active_model: "llama3",
			repos_total: 2,
			repos_done: 2,
			current_repo: null,
			facts_total: 10,
			draft_projects: 2,
			polished_projects: 0,
			elapsed_seconds: 18,
			model_check_seconds: 1,
			selected_repos: ["repo-1", "repo-2"],
		},
		draft: sampleDraft,
		output: null,
		error: null,
	};

	api.getPipelineStatus = async () => draftReadyResponse;

	const harness = createHarness({
		onNext: (target) => {
			nextTargets.push(target);
		},
	});

	try {
		rendered = await testRender(harness.node, { width: 100, height: 32 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-428");
			context.setPipelineStatus("running");
			context.setPipelineStage("ANALYZE");
		});
		await flushEffects(rendered);

		expect(nextTargets).toEqual(["draft-pause"]);
		expect(harness.getContext().state).toMatchObject({
			pipelineStatus: "draft_ready",
			pipelineStage: "DRAFT",
			pipelineMessages: ["Draft assembled from telemetry facts."],
			resumeV3Draft: sampleDraft,
		});
		expect(rendered.captureCharFrame()).toContain("75%");
	} finally {
		destroyRenderer(rendered);
	}
});

test("Analysis routes complete status to preview", async () => {
	freezeIntervals();
	const nextTargets: string[] = [];
	let rendered: RenderedScreen | null = null;

	api.getPipelineStatus = async () =>
		({
			status: "complete",
			stage: "POLISH",
			messages: ["Pipeline complete."],
			telemetry: {
				stage: "POLISH",
				active_model: "lfm2.5",
				repos_total: 1,
				repos_done: 1,
				current_repo: null,
				facts_total: 10,
				draft_projects: 1,
				polished_projects: 1,
				elapsed_seconds: 24,
				model_check_seconds: 1,
				selected_repos: ["repo-1"],
			},
			draft: sampleDraft,
			output: sampleDraft,
			error: null,
		}) satisfies PipelineStatusResponse;

	const harness = createHarness({
		onNext: (target) => {
			nextTargets.push(target);
		},
	});

	try {
		rendered = await testRender(harness.node, { width: 100, height: 32 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-428");
			context.setPipelineStatus("running");
			context.setPipelineStage("POLISH");
		});
		await flushEffects(rendered);

		expect(nextTargets).toEqual(["preview"]);
		expect(harness.getContext().state.resumeV3Output).toEqual(sampleDraft);
		expect(rendered.captureCharFrame()).toContain("100%");
	} finally {
		destroyRenderer(rendered);
	}
});

test("Analysis cancels the pipeline from Escape while active", async () => {
	freezeIntervals();
	let cancelCount = 0;
	let rendered: RenderedScreen | null = null;

	api.getPipelineStatus = async () =>
		({
			status: "running",
			stage: "FACTS",
			messages: ["Collecting facts."],
			telemetry: {
				stage: "FACTS",
				active_model: "llama3",
				repos_total: 2,
				repos_done: 1,
				current_repo: "artifact-miner",
				facts_total: 6,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 9,
				model_check_seconds: 1,
				selected_repos: ["repo-1", "repo-2"],
			},
			draft: null,
			output: null,
			error: null,
		}) satisfies PipelineStatusResponse;

	api.cancelPipeline = async () => {
		cancelCount += 1;
		return { ok: true, status: "cancelled" };
	};

	const harness = createHarness();

	try {
		rendered = await testRender(harness.node, { width: 100, height: 32 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-428");
			context.setPipelineStatus("running");
			context.setPipelineStage("FACTS");
		});
		await flushEffects(rendered);

			await act(async () => {
				keyboardHandler?.({ name: "escape" });
				await Promise.resolve();
			});
			await rendered.renderOnce();

			expect(cancelCount).toBe(1);
			expect(harness.getContext().state.pipelineStatus).toBe("cancelled");
			expect(harness.getContext().state.pipelineNotice).toBe("Pipeline cancelled.");
		expect(rendered.captureCharFrame()).toContain("Pipeline cancelled.");
	} finally {
		destroyRenderer(rendered);
	}
});
