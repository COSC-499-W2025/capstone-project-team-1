import { afterEach, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act } from "react";
import type { PipelineRepoCandidate } from "../api/types";

type KeyboardEventLike = { name: string };

let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { ProjectList } = await import("./ProjectList");

const repoFixture: PipelineRepoCandidate[] = [
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

function pressKey(key: KeyboardEventLike) {
	if (!keyboardHandler) {
		throw new Error("ProjectList keyboard handler was not registered");
	}

	keyboardHandler(key);
}

afterEach(() => {
	keyboardHandler = null;
});

test("ProjectList renders repo summary and external notice", async () => {
	const rendered = await testRender(
		<ProjectList
			repos={repoFixture}
			selectedRepoIds={["repo-1"]}
			onChangeSelection={() => {}}
			onContinue={() => {}}
			onBack={() => {}}
			notice="No contributors found. Manual email entry is still available."
		/>,
		{ width: 120, height: 40 },
	);

	await act(async () => {
		await rendered.renderOnce();
	});

	const frame = rendered.captureCharFrame();
	expect(frame).toContain("Select Repositories");
	expect(frame).toContain("Selected 1 of 2 repositories.");
	expect(frame).toContain("No contributors found.");

	await act(async () => {
		rendered.renderer.destroy();
	});
});

test("ProjectList validates before continue when no repositories are selected", async () => {
	let continueCount = 0;
	const rendered = await testRender(
		<ProjectList
			repos={repoFixture}
			selectedRepoIds={[]}
			onChangeSelection={() => {}}
			onContinue={() => {
				continueCount += 1;
			}}
			onBack={() => {}}
		/>,
		{ width: 120, height: 44 },
	);

	await act(async () => {
		await rendered.renderOnce();
	});

	await act(async () => {
		pressKey({ name: "return" });
		await rendered.renderOnce();
	});

	expect(continueCount).toBe(0);

	await act(async () => {
		rendered.renderer.destroy();
	});
});

test("ProjectList toggles the current repository on Space", async () => {
	let selection: string[] | null = null;
	const rendered = await testRender(
		<ProjectList
			repos={repoFixture}
			selectedRepoIds={[]}
			onChangeSelection={(repoIds) => {
				selection = repoIds;
			}}
			onContinue={() => {}}
			onBack={() => {}}
		/>,
		{ width: 120, height: 40 },
	);

	await act(async () => {
		await rendered.renderOnce();
	});

	act(() => {
		pressKey({ name: "space" });
	});

	expect(selection).toEqual(["repo-1"]);

	await act(async () => {
		rendered.renderer.destroy();
	});
});

test("ProjectList calls onBack when Escape is pressed", async () => {
	let backCount = 0;
	const rendered = await testRender(
		<ProjectList
			repos={repoFixture}
			selectedRepoIds={["repo-1"]}
			onChangeSelection={() => {}}
			onContinue={() => {}}
			onBack={() => {
				backCount += 1;
			}}
		/>,
		{ width: 120, height: 40 },
	);

	await act(async () => {
		await rendered.renderOnce();
	});

	await act(async () => {
		pressKey({ name: "escape" });
		await rendered.renderOnce();
	});

	expect(backCount).toBe(1);

	await act(async () => {
		rendered.renderer.destroy();
	});
});
