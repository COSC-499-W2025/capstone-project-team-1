import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type { PipelineRepoCandidate } from "../api/types";
import { AppProvider, useAppState } from "../context/AppContext";

type AppContextHookValue = ReturnType<typeof useAppState>;
type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyEvent = {
	name: string;
	sequence: string;
	ctrl: boolean;
	shift: boolean;
	meta: boolean;
	option: boolean;
	eventType: "press";
	repeated: boolean;
};

let keyboardHandler: ((key: KeyEvent) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyEvent) => void) => {
		keyboardHandler = handler;
	},
}));

const { PipelineLaunchScreen } = await import("./PipelineLaunchScreen");

const originalFetch = globalThis.fetch;

const repoCandidates: PipelineRepoCandidate[] = [
	{
		id: "repo-1",
		name: "artifact-miner",
		rel_path: "apps/artifact-miner",
	},
	{
		id: "repo-2",
		name: "resume-lab",
		rel_path: "apps/resume-lab",
	},
];

function createScreenHarness(props?: {
	onStarted?: () => void;
	onBack?: () => void;
}) {
	let context: AppContextHookValue | null = null;

	function Probe() {
		context = useAppState();
		return <box />;
	}

	return {
		getContext() {
			if (!context) {
				throw new Error("AppContext probe did not mount");
			}
			return context;
		},
		node: (
			<AppProvider>
				<Probe />
				<PipelineLaunchScreen
					onStarted={props?.onStarted ?? (() => {})}
					onBack={props?.onBack ?? (() => {})}
				/>
			</AppProvider>
		),
	};
}

function destroyRenderer(rendered: RenderedScreen) {
	act(() => {
		rendered.renderer.destroy();
	});
}

function pressKey(name: string, sequence = "") {
	if (!keyboardHandler) {
		throw new Error("Keyboard handler was not registered");
	}

	keyboardHandler({
		name,
		sequence,
		ctrl: false,
		shift: false,
		meta: false,
		option: false,
		eventType: "press",
		repeated: false,
	});
}

async function flushEffects() {
	await Promise.resolve();
	await Promise.resolve();
}

afterEach(() => {
	globalThis.fetch = originalFetch;
	keyboardHandler = null;
});

function setupResponse(overrides?: Partial<Record<string, unknown>>) {
	return {
		models_dir: "/Users/stavan/.artifactminer/models",
		preferred_default_model: "qwen2.5-coder-3b-q4",
		selected_default_model: "qwen2.5-coder-3b-q4",
		supported_models: [
			{
				name: "qwen2.5-coder-3b-q4",
				filename: "qwen2.5-coder-3b-instruct-q4_k_m.gguf",
				repo_url:
					"https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF?show_file_info=qwen2.5-coder-3b-instruct-q4_k_m.gguf",
				context_window: 16384,
				path: null,
			},
		],
		available_models: [
			{
				name: "qwen2.5-coder-3b-q4",
				filename: "qwen2.5-coder-3b-instruct-q4_k_m.gguf",
				repo_url:
					"https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF?show_file_info=qwen2.5-coder-3b-instruct-q4_k_m.gguf",
				context_window: 16384,
				path: "/Users/stavan/.artifactminer/models/qwen2.5-coder-3b-instruct-q4_k_m.gguf",
			},
		],
		llama_server_found: true,
		runtime: {
			loaded_model: null,
			server_pid: null,
			server_port: null,
			is_running: false,
			is_healthy: false,
			models_dir: "/Users/stavan/.artifactminer/models",
		},
		...overrides,
	};
}

test("PipelineLaunchScreen renders the selected email and repo summary", async () => {
	const harness = createScreenHarness();
	globalThis.fetch = (async () =>
		new Response(JSON.stringify(setupResponse()), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		})) as typeof fetch;
	const rendered = await testRender(harness.node, { width: 100, height: 32 });
	const context = harness.getContext();

	act(() => {
		context.setIntakeId("intake-123");
		context.setDetectedRepos(repoCandidates);
		context.setSelectedRepoIds(["repo-1", "repo-2"]);
		context.setSelectedEmail("dev@example.com");
	});

	await rendered.renderOnce();
	await act(async () => {
		await flushEffects();
	});
	await rendered.renderOnce();
	const frame = rendered.captureCharFrame();

	expect(frame).toContain("Pipeline Configuration");
	expect(frame).toContain("Email: dev@example.com");
	expect(frame).toContain("Selected repos: 2");
	expect(frame).toContain("- artifact-miner");
	expect(frame).toContain("- resume-lab");
	expect(frame).toContain("Detected model: qwen2.5-coder-3b-q4");
	expect(frame).toContain("llama-server found on PATH");

	destroyRenderer(rendered);
});

test("PipelineLaunchScreen starts the pipeline on Enter and updates context", async () => {
	let startedCount = 0;
	const harness = createScreenHarness({
		onStarted: () => {
			startedCount += 1;
		},
	});
	const fetchCalls: Array<{ url: string; body?: string }> = [];
	globalThis.fetch = (async (input, init) => {
		if (!init?.method || init.method === "GET") {
			fetchCalls.push({ url: String(input) });
			return new Response(JSON.stringify(setupResponse()), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			});
		}
		fetchCalls.push({
			url: String(input),
			body: typeof init?.body === "string" ? init.body : undefined,
		});
		return new Response(JSON.stringify({ job_id: "job-427", status: "queued" }), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		});
	}) as typeof fetch;

	const rendered = await testRender(harness.node, { width: 100, height: 32 });
	const context = harness.getContext();

	act(() => {
		context.setIntakeId("intake-123");
		context.setDetectedRepos(repoCandidates);
		context.setSelectedRepoIds(["repo-1"]);
		context.setSelectedEmail("dev@example.com");
		context.setPipelineJobId("stale-job");
		context.setPipelineStatus("complete");
		context.setPipelineStage("POLISH");
		context.setPipelineMessages(["old message"]);
		context.setPipelineNotice("Old notice");
	});

	await rendered.renderOnce();
	await act(async () => {
		await flushEffects();
	});
	await rendered.renderOnce();
	await act(async () => {
		pressKey("return", "\r");
		await flushEffects();
	});
	await rendered.renderOnce();

	expect(fetchCalls).toEqual([
		{
			url: "http://127.0.0.1:8000/local-llm/setup",
		},
		{
			url: "http://127.0.0.1:8000/local-llm/generation/start",
			body: JSON.stringify({
				intake_id: "intake-123",
				repo_ids: ["repo-1"],
				user_email: "dev@example.com",
			}),
		},
	]);
	expect(startedCount).toBe(1);
	expect(harness.getContext().state).toMatchObject({
		pipelineJobId: "job-427",
		pipelineStatus: "queued",
		pipelineStage: "ANALYZE",
		pipelineMessages: ["Pipeline start requested."],
		pipelineNotice: null,
	});

	destroyRenderer(rendered);
});

test("PipelineLaunchScreen shows a validation error instead of launching with missing state", async () => {
	const harness = createScreenHarness();
	const rendered = await testRender(harness.node, { width: 100, height: 32 });
	let fetchCalled = false;

	globalThis.fetch = (async (_input, init) => {
		if (!init?.method || init.method === "GET") {
			return new Response(JSON.stringify(setupResponse()), {
				status: 200,
				headers: { "Content-Type": "application/json" },
			});
		}
		fetchCalled = true;
		return new Response(JSON.stringify({ job_id: "job-should-not-run", status: "queued" }), {
			status: 200,
			headers: { "Content-Type": "application/json" },
		});
	}) as unknown as typeof fetch;

	await rendered.renderOnce();
	await act(async () => {
		await flushEffects();
	});
	await rendered.renderOnce();
	await act(async () => {
		pressKey("return", "\r");
		await flushEffects();
	});
	await rendered.renderOnce();

	expect(fetchCalled).toBe(false);
	expect(rendered.captureCharFrame()).toContain(
		"Missing intake, repo selection, or identity.",
	);

	destroyRenderer(rendered);
});

test("PipelineLaunchScreen blocks launch when no supported local model is installed", async () => {
	const harness = createScreenHarness();
	globalThis.fetch = (async () =>
		new Response(
			JSON.stringify(
				setupResponse({
					selected_default_model: null,
					available_models: [],
				}),
			),
			{
				status: 200,
				headers: { "Content-Type": "application/json" },
			},
		)) as typeof fetch;

	const rendered = await testRender(harness.node, { width: 100, height: 32 });
	const context = harness.getContext();

	act(() => {
		context.setIntakeId("intake-123");
		context.setDetectedRepos(repoCandidates);
		context.setSelectedRepoIds(["repo-1"]);
		context.setSelectedEmail("dev@example.com");
	});

	await rendered.renderOnce();
	await act(async () => {
		await flushEffects();
	});
	await rendered.renderOnce();
	await act(async () => {
		pressKey("return", "\r");
		await flushEffects();
	});
	await rendered.renderOnce();

	expect(rendered.captureCharFrame()).toContain(
		"No supported local model found in ~/.artifactminer/models.",
	);

	destroyRenderer(rendered);
});
