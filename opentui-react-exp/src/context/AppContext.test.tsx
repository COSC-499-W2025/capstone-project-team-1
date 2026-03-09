import { expect, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type {
	PipelineContributorIdentity,
	PipelineRepoCandidate,
	PipelineTelemetry,
	ResumeV3Output,
} from "../api/types";
import { AppProvider, useAppState } from "./AppContext";

type AppContextHookValue = ReturnType<typeof useAppState>;

function createHarness() {
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
			</AppProvider>
		),
	};
}

function destroyRenderer(rendered: { renderer: { destroy: () => void } }) {
	act(() => {
		rendered.renderer.destroy();
	});
}

const repoCandidate: PipelineRepoCandidate = {
	id: "repo-1",
	name: "artifact-miner",
	rel_path: "artifact-miner",
};

const contributor: PipelineContributorIdentity = {
	email: "dev@example.com",
	name: "Dev Example",
	repo_count: 1,
	commit_count: 42,
	candidate_username: "devexample",
};

const telemetry: PipelineTelemetry = {
	stage: "FACTS",
	active_model: "llama3",
	repos_total: 3,
	repos_done: 1,
	current_repo: "artifact-miner",
	facts_total: 12,
	draft_projects: 1,
	polished_projects: 0,
	elapsed_seconds: 10,
	model_check_seconds: 2,
	selected_repos: ["repo-1"],
};

const resumeOutput: ResumeV3Output = {
	professional_summary: "Built reliable developer tooling.",
	skills_section: "TypeScript, React, Python",
	developer_profile: "Backend and frontend engineer.",
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

test("AppContext exposes the pipeline initial state", async () => {
	const harness = createHarness();
	const rendered = await testRender(harness.node, { width: 80, height: 24 });

	expect(harness.getContext().state).toEqual({
		zipPath: "",
		intakeId: null,
		detectedRepos: [],
		selectedRepoIds: [],
		contributors: [],
		selectedEmail: null,
		pipelineJobId: null,
		pipelineStatus: "idle",
		pipelineStage: null,
		pipelineTelemetry: null,
		pipelineMessages: [],
		resumeV3Draft: null,
		resumeV3Output: null,
		pipelineNotice: null,
	});

	destroyRenderer(rendered);
});

test("AppContext setters update pipeline state", async () => {
	const harness = createHarness();
	const rendered = await testRender(harness.node, { width: 80, height: 24 });
	const context = harness.getContext();

	act(() => {
		context.setZipPath("/tmp/export.zip");
		context.setIntakeId("intake-123");
		context.setDetectedRepos([repoCandidate]);
		context.setSelectedRepoIds(["repo-1"]);
		context.setContributors([contributor]);
		context.setSelectedEmail("dev@example.com");
		context.setPipelineJobId("job-123");
		context.setPipelineStatus("running");
		context.setPipelineStage("FACTS");
		context.setPipelineTelemetry(telemetry);
		context.setPipelineMessages(["starting", "processing"]);
		context.setResumeV3Draft(resumeOutput);
		context.setResumeV3Output(resumeOutput);
		context.setPipelineNotice("Ready to continue");
	});

	expect(harness.getContext().state).toMatchObject({
		zipPath: "/tmp/export.zip",
		intakeId: "intake-123",
		detectedRepos: [repoCandidate],
		selectedRepoIds: ["repo-1"],
		contributors: [contributor],
		selectedEmail: "dev@example.com",
		pipelineJobId: "job-123",
		pipelineStatus: "running",
		pipelineStage: "FACTS",
		pipelineTelemetry: telemetry,
		pipelineMessages: ["starting", "processing"],
		resumeV3Draft: resumeOutput,
		resumeV3Output: resumeOutput,
		pipelineNotice: "Ready to continue",
	});

	destroyRenderer(rendered);
});

test("resetRunState clears only run-specific pipeline fields", async () => {
	const harness = createHarness();
	const rendered = await testRender(harness.node, { width: 80, height: 24 });
	const context = harness.getContext();

	act(() => {
		context.setZipPath("/tmp/export.zip");
		context.setIntakeId("intake-123");
		context.setDetectedRepos([repoCandidate]);
		context.setSelectedRepoIds(["repo-1"]);
		context.setContributors([contributor]);
		context.setSelectedEmail("dev@example.com");
		context.setPipelineJobId("job-123");
		context.setPipelineStatus("draft_ready");
		context.setPipelineStage("DRAFT");
		context.setPipelineTelemetry(telemetry);
		context.setPipelineMessages(["draft ready"]);
		context.setResumeV3Draft(resumeOutput);
		context.setResumeV3Output(resumeOutput);
		context.setPipelineNotice("Use feedback to continue");
	});

	act(() => {
		context.resetRunState();
	});

	expect(harness.getContext().state).toEqual({
		zipPath: "/tmp/export.zip",
		intakeId: "intake-123",
		detectedRepos: [repoCandidate],
		selectedRepoIds: ["repo-1"],
		contributors: [contributor],
		selectedEmail: "dev@example.com",
		pipelineJobId: null,
		pipelineStatus: "idle",
		pipelineStage: null,
		pipelineTelemetry: null,
		pipelineMessages: [],
		resumeV3Draft: null,
		resumeV3Output: null,
		pipelineNotice: "Use feedback to continue",
	});

	destroyRenderer(rendered);
});

test("reset restores the full initial state", async () => {
	const harness = createHarness();
	const rendered = await testRender(harness.node, { width: 80, height: 24 });
	const context = harness.getContext();

	act(() => {
		context.setZipPath("/tmp/export.zip");
		context.setIntakeId("intake-123");
		context.setDetectedRepos([repoCandidate]);
		context.setSelectedRepoIds(["repo-1"]);
		context.setContributors([contributor]);
		context.setSelectedEmail("dev@example.com");
		context.setPipelineJobId("job-123");
		context.setPipelineStatus("complete");
		context.setPipelineStage("POLISH");
		context.setPipelineTelemetry(telemetry);
		context.setPipelineMessages(["done"]);
		context.setResumeV3Draft(resumeOutput);
		context.setResumeV3Output(resumeOutput);
		context.setPipelineNotice("Complete");
	});

	act(() => {
		context.reset();
	});

	expect(harness.getContext().state).toEqual({
		zipPath: "",
		intakeId: null,
		detectedRepos: [],
		selectedRepoIds: [],
		contributors: [],
		selectedEmail: null,
		pipelineJobId: null,
		pipelineStatus: "idle",
		pipelineStage: null,
		pipelineTelemetry: null,
		pipelineMessages: [],
		resumeV3Draft: null,
		resumeV3Output: null,
		pipelineNotice: null,
	});

	destroyRenderer(rendered);
});
