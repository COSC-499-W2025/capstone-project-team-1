import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import { api } from "../api/endpoints";
import type { PipelineStatusResponse, ResumeV3Output } from "../api/types";
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
	analysisMode?: "phase1" | "phase3";
}) {
	let context: AppContextHookValue | null = null;

	function Probe() {
		context = useAppState();
		return (
			<Analysis
				onNext={props?.onNext}
				onComplete={props?.onComplete}
				onBack={props?.onBack}
				analysisMode={props?.analysisMode}
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

function countOccurrences(haystack: string, needle: string) {
	return haystack.split(needle).length - 1;
}

function repoBar(done: number, total: number, width = 14) {
	if (total === 0) {
		return "░".repeat(width);
	}

	const filled = Math.round((done / total) * width);
	return "█".repeat(filled) + "░".repeat(width - filled);
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
	globalThis.setInterval = ((_: TimerHandler, __?: number) =>
		1) as unknown as typeof setInterval;
	globalThis.clearInterval = ((
		_: number,
	) => {}) as unknown as typeof clearInterval;
}

afterEach(() => {
	api.getPipelineStatus = originalGetPipelineStatus;
	api.cancelPipeline = originalCancelPipeline;
	globalThis.setInterval = originalSetInterval;
	globalThis.clearInterval = originalClearInterval;
	keyboardHandler = null;
});

test("Analysis routes draft_ready to draft-pause and renders the draft stage UI", async () => {
	freezeIntervals();
	const nextTargets: string[] = [];
	let rendered: RenderedScreen | null = null;

	const draftReadyResponse: PipelineStatusResponse = {
		status: "draft_ready",
		stage: "DRAFT",
		messages: [
			"Pipeline started",
			"Running project query for selected repositories",
			"Running project query for selected repositories",
			"Assembling resume...",
		],
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
		rendered = await testRender(harness.node, { width: 140, height: 40 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-429");
			context.setPipelineStatus("running");
			context.setPipelineStage("ANALYZE");
			context.setPipelineTelemetry(draftReadyResponse.telemetry);
			context.setPipelineMessages(draftReadyResponse.messages);
		});
		await flushEffects(rendered);

		const frame = rendered.captureCharFrame();

		expect(nextTargets).toEqual(["draft-pause"]);
		expect(harness.getContext().state).toMatchObject({
			pipelineStatus: "draft_ready",
			pipelineStage: "DRAFT",
			resumeV3Draft: sampleDraft,
		});
		expect(frame).toContain("✓ Analyze   -  Read repos");
		expect(frame).toContain("✓ Facts     -  Compile");
		expect(frame).toContain("► Draft     -  Write resume");
		expect(frame).toContain("○ Polish    -  Apply feedback");
		expect(frame).toContain("DRAFT_READY");
		expect(frame).toContain("AI: Writing project bullets");
		expect(frame).toContain("Assembling resume document");
		expect(countOccurrences(frame, "AI: Writing project bullets")).toBe(1);
		expect(countOccurrences(frame, "Assembling resume document")).toBe(1);
		expect(frame).not.toContain("Pipeline started");
	} finally {
		destroyRenderer(rendered);
	}
});

test("Analysis renders pipeline panels with repo progress and current activity", async () => {
	freezeIntervals();
	let rendered: RenderedScreen | null = null;

	api.getPipelineStatus = async () =>
		({
			status: "running",
			stage: "FACTS",
			messages: [
				"Extracting README from repository",
				"Extracting README from repository",
				"Classifying commits for selected author",
				"Pipeline request accepted",
			],
			telemetry: {
				stage: "FACTS",
				active_model: "llama3.2:latest",
				repos_total: 3,
				repos_done: 1,
				current_repo: "artifact-miner",
				facts_total: 6,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 9,
				model_check_seconds: 1,
				selected_repos: ["repo-1", "repo-2", "repo-3"],
			},
			draft: null,
			output: null,
			error: null,
		}) satisfies PipelineStatusResponse;

	const harness = createHarness();

	try {
		rendered = await testRender(harness.node, { width: 140, height: 40 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-429");
			context.setPipelineStatus("running");
			context.setPipelineStage("FACTS");
			context.setPipelineTelemetry({
				stage: "FACTS",
				active_model: "llama3.2:latest",
				repos_total: 3,
				repos_done: 1,
				current_repo: "artifact-miner",
				facts_total: 6,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 9,
				model_check_seconds: 1,
				selected_repos: ["repo-1", "repo-2", "repo-3"],
			});
			context.setPipelineMessages([
				"Extracting README from repository",
				"Extracting README from repository",
				"Classifying commits for selected author",
				"Pipeline request accepted",
			]);
		});
		await flushEffects(rendered);

		const frame = rendered.captureCharFrame();

		expect(frame).toContain("✓ Analyze   -  Read repos");
		expect(frame).toContain("► Facts     -  Compile");
		expect(frame).toContain("Status RUNNING");
		expect(frame).toContain("Elapsed 9.0s");
		expect(frame).toContain("Repos 1 / 3");
		expect(frame).toContain("33%");
		expect(frame).toContain(repoBar(1, 3));
		expect(frame).toContain("Now analyzing");
		expect(frame).toContain("artifact-miner");
		expect(frame).toContain("repo 2 of 3");
		expect(frame).toContain("Reading project documentation");
		expect(frame).toContain("Analyzing commit history");
		expect(frame).toContain("Facts 6");
		expect(countOccurrences(frame, "Reading project documentation")).toBe(1);
		expect(countOccurrences(frame, "Analyzing commit history")).toBe(1);
		expect(frame).not.toContain("Pipeline request accepted");
		expect(frame).not.toContain("Extracting README from repository");
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
		rendered = await testRender(harness.node, { width: 140, height: 40 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-429");
			context.setPipelineStatus("running");
			context.setPipelineStage("POLISH");
			context.setPipelineTelemetry({
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
			});
			context.setPipelineMessages(["Pipeline complete."]);
		});
		await flushEffects(rendered);

		const frame = rendered.captureCharFrame();

		expect(nextTargets).toEqual(["preview"]);
		expect(harness.getContext().state.resumeV3Output).toEqual(sampleDraft);
		expect(frame).toContain("✓ Polish    -  Apply feedback");
		expect(frame).toContain("COMPLETE");
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
		rendered = await testRender(harness.node, { width: 140, height: 40 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-429");
			context.setPipelineStatus("running");
			context.setPipelineStage("FACTS");
			context.setPipelineTelemetry({
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
			});
			context.setPipelineMessages(["Collecting facts."]);
		});
		await flushEffects(rendered);

		await act(async () => {
			keyboardHandler?.({ name: "escape" });
			await Promise.resolve();
		});
		await rendered.renderOnce();

		expect(cancelCount).toBe(1);
		expect(harness.getContext().state.pipelineStatus).toBe("cancelled");
		expect(harness.getContext().state.pipelineNotice).toBe(
			"Pipeline cancelled.",
		);
		expect(rendered.captureCharFrame()).toContain("Pipeline cancelled.");
	} finally {
		destroyRenderer(rendered);
	}
});

test("Analysis surfaces terminal errors and Escape returns to project-list", async () => {
	freezeIntervals();
	const nextTargets: string[] = [];
	let rendered: RenderedScreen | null = null;

	api.getPipelineStatus = async () =>
		({
			status: "error",
			stage: "FACTS",
			messages: ["Model failed to respond."],
			telemetry: {
				stage: "FACTS",
				active_model: "llama3",
				repos_total: 1,
				repos_done: 0,
				current_repo: "artifact-miner",
				facts_total: 1,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 4,
				model_check_seconds: 1,
				selected_repos: ["repo-1"],
			},
			draft: null,
			output: null,
			error: "Pipeline failed because the model was unavailable.",
		}) satisfies PipelineStatusResponse;

	const harness = createHarness({
		onNext: (target) => {
			nextTargets.push(target);
		},
	});

	try {
		rendered = await testRender(harness.node, { width: 140, height: 40 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-429");
			context.setPipelineStatus("running");
			context.setPipelineStage("FACTS");
			context.setPipelineTelemetry({
				stage: "FACTS",
				active_model: "llama3",
				repos_total: 1,
				repos_done: 0,
				current_repo: "artifact-miner",
				facts_total: 1,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 4,
				model_check_seconds: 1,
				selected_repos: ["repo-1"],
			});
			context.setPipelineMessages(["Model failed to respond."]);
		});
		await flushEffects(rendered);

		const frame = rendered.captureCharFrame();

		expect(frame).toContain(
			"Pipeline failed because the model was unavailable.",
		);
		expect(frame).toContain("ERROR");

		await act(async () => {
			keyboardHandler?.({ name: "escape" });
			await Promise.resolve();
		});
		await rendered.renderOnce();

		expect(nextTargets).toEqual(["project-list"]);
		expect(harness.getContext().state.pipelineStatus).toBe("error");
	} finally {
		destroyRenderer(rendered);
	}
});

test("Analysis surfaces failed_resource_guard as a terminal error and Escape returns to project-list", async () => {
	freezeIntervals();
	const nextTargets: string[] = [];
	let rendered: RenderedScreen | null = null;

	api.getPipelineStatus = async () =>
		({
			status: "failed_resource_guard",
			stage: "DRAFT",
			messages: ["Resource guard stopped the run."],
			telemetry: {
				stage: "DRAFT",
				active_model: "llama3",
				repos_total: 1,
				repos_done: 0,
				current_repo: "artifact-miner",
				facts_total: 1,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 4,
				model_check_seconds: 1,
				selected_repos: ["repo-1"],
			},
			draft: null,
			output: null,
			error: "Pipeline stopped because the resource guard was triggered.",
		}) satisfies PipelineStatusResponse;

	const harness = createHarness({
		onNext: (target) => {
			nextTargets.push(target);
		},
	});

	try {
		rendered = await testRender(harness.node, { width: 140, height: 40 });
		act(() => {
			const context = harness.getContext();
			context.setPipelineJobId("job-429");
			context.setPipelineStatus("running");
			context.setPipelineStage("DRAFT");
			context.setPipelineTelemetry({
				stage: "DRAFT",
				active_model: "llama3",
				repos_total: 1,
				repos_done: 0,
				current_repo: "artifact-miner",
				facts_total: 1,
				draft_projects: 0,
				polished_projects: 0,
				elapsed_seconds: 4,
				model_check_seconds: 1,
				selected_repos: ["repo-1"],
			});
			context.setPipelineMessages(["Resource guard stopped the run."]);
		});
		await flushEffects(rendered);

		const frame = rendered.captureCharFrame();

		expect(frame).toContain("Pipeline stopped because the resource guard was triggered.");
		expect(frame).toContain("FAILED_RESOURCE_GUARD");

		await act(async () => {
			keyboardHandler?.({ name: "escape" });
			await Promise.resolve();
		});
		await rendered.renderOnce();

		expect(nextTargets).toEqual(["project-list"]);
		expect(harness.getContext().state.pipelineStatus).toBe(
			"failed_resource_guard",
		);
	} finally {
		destroyRenderer(rendered);
	}
});
