import { afterEach, expect, test } from "bun:test";
import { api } from "./endpoints";

const originalFetch = globalThis.fetch;

type FetchCall = {
	url: string;
	options?: RequestInit;
};

const fetchCalls: FetchCall[] = [];

const jsonResponse = (body: unknown): Response =>
	new Response(JSON.stringify(body), {
		status: 200,
		headers: { "Content-Type": "application/json" },
	});

const installMockFetch = (body: unknown): void => {
	globalThis.fetch = (async (input, init) => {
		fetchCalls.push({ url: String(input), options: init });
		return jsonResponse(body);
	}) as typeof fetch;
};

afterEach(() => {
	globalThis.fetch = originalFetch;
	fetchCalls.length = 0;
});

test("createPipelineIntake sends POST /local-llm/context with zip_path", async () => {
	installMockFetch({ intake_id: "intake-1", zip_path: "/tmp/repo.zip", repos: [] });

	await api.createPipelineIntake("/tmp/repo.zip");

	expect(fetchCalls).toHaveLength(1);
	expect(fetchCalls[0]?.url).toBe("http://127.0.0.1:8000/local-llm/context");
	expect(fetchCalls[0]?.options?.method).toBe("POST");
	expect(fetchCalls[0]?.options?.body).toBe(JSON.stringify({ zip_path: "/tmp/repo.zip" }));
});

test("getPipelineContributors posts the request payload unchanged", async () => {
	installMockFetch({ contributors: [] });
	const request = { repo_ids: ["repo-1", "repo-2"] };

	await api.getPipelineContributors(request);

	expect(fetchCalls).toHaveLength(1);
	expect(fetchCalls[0]?.url).toBe(
		"http://127.0.0.1:8000/local-llm/context/contributors",
	);
	expect(fetchCalls[0]?.options?.method).toBe("POST");
	expect(fetchCalls[0]?.options?.body).toBe(JSON.stringify(request));
});

test("startPipeline posts the request payload unchanged", async () => {
	installMockFetch({ job_id: "job-1", status: "queued" });
	const request = {
		intake_id: "intake-1",
		repo_ids: ["repo-1"],
		user_email: "user@example.com",
		stage1_model: "model-a",
		stage2_model: "model-b",
		stage3_model: "model-c",
	};

	await api.startPipeline(request);

	expect(fetchCalls).toHaveLength(1);
	expect(fetchCalls[0]?.url).toBe(
		"http://127.0.0.1:8000/local-llm/generation/start",
	);
	expect(fetchCalls[0]?.options?.method).toBe("POST");
	expect(fetchCalls[0]?.options?.body).toBe(JSON.stringify(request));
});

test("getPipelineStatus performs GET with no JSON body", async () => {
	installMockFetch({
		status: "running",
		stage: "ANALYZE",
		messages: [],
		telemetry: {
			stage: "ANALYZE",
			active_model: null,
			repos_total: 0,
			repos_done: 0,
			current_repo: null,
			facts_total: 0,
			draft_projects: 0,
			polished_projects: 0,
			elapsed_seconds: 0,
			model_check_seconds: 0,
			selected_repos: [],
		},
		draft: null,
		output: null,
		error: null,
	});

	await api.getPipelineStatus();

	expect(fetchCalls).toHaveLength(1);
	expect(fetchCalls[0]?.url).toBe(
		"http://127.0.0.1:8000/local-llm/generation/status",
	);
	expect(fetchCalls[0]?.options?.method).toBe("GET");
	expect(fetchCalls[0]?.options?.body).toBeUndefined();
});

test("polishPipeline posts the request payload unchanged", async () => {
	installMockFetch({ ok: true, status: "polishing" });
	const request = {
		general_notes: "Keep metrics concrete",
		tone: "concise",
		additions: ["Highlight platform work"],
		removals: ["Drop vague bullet"],
	};

	await api.polishPipeline(request);

	expect(fetchCalls).toHaveLength(1);
	expect(fetchCalls[0]?.url).toBe(
		"http://127.0.0.1:8000/local-llm/generation/polish",
	);
	expect(fetchCalls[0]?.options?.method).toBe("POST");
	expect(fetchCalls[0]?.options?.body).toBe(JSON.stringify(request));
});

test("cancelPipeline posts to /local-llm/generation/cancel with no JSON body", async () => {
	installMockFetch({ ok: true, status: "cancelled" });

	await api.cancelPipeline();

	expect(fetchCalls).toHaveLength(1);
	expect(fetchCalls[0]?.url).toBe(
		"http://127.0.0.1:8000/local-llm/generation/cancel",
	);
	expect(fetchCalls[0]?.options?.method).toBe("POST");
	expect(fetchCalls[0]?.options?.body).toBeUndefined();
});

test("runAnalysis still posts to /analyze/{zipId} and preserves optional directories behavior", async () => {
	installMockFetch({
		zip_id: 12,
		extraction_path: "/tmp/extracted",
		repos_found: 0,
		repos_analyzed: [],
		rankings: [],
		summaries: [],
		consent_level: "local",
		user_email: "user@example.com",
	});

	await api.runAnalysis(12, ["apps/web", "packages/core"]);
	await api.runAnalysis(12);

	expect(fetchCalls).toHaveLength(2);
	expect(fetchCalls[0]?.url).toBe("http://127.0.0.1:8000/analyze/12");
	expect(fetchCalls[0]?.options?.method).toBe("POST");
	expect(fetchCalls[0]?.options?.body).toBe(
		JSON.stringify({ directories: ["apps/web", "packages/core"] }),
	);
	expect(fetchCalls[1]?.url).toBe("http://127.0.0.1:8000/analyze/12");
	expect(fetchCalls[1]?.options?.method).toBe("POST");
	expect(fetchCalls[1]?.options?.body).toBeUndefined();
});
