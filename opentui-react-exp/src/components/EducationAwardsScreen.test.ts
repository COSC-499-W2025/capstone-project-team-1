import { afterEach, describe, expect, mock, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act, createElement, useEffect } from "react";

import { api } from "../api/endpoints";
import type { Award, Education, EducationCreateRequest } from "../api/types";
import { AppProvider, useAppState } from "../context/AppContext";

type RenderedScreen = Awaited<ReturnType<typeof testRender>>;
type KeyboardEventLike = {
	name: string;
	sequence?: string;
	ctrl?: boolean;
	meta?: boolean;
	shift?: boolean;
	option?: boolean;
	eventType?: "press";
	repeated?: boolean;
};

let keyboardHandler: ((key: KeyboardEventLike) => void) | null = null;

mock.module("@opentui/react", () => ({
	useKeyboard: (handler: (key: KeyboardEventLike) => void) => {
		keyboardHandler = handler;
	},
}));

const { EducationAwardsScreen } = await import("./EducationAwardsScreen");

const originalListEducation = api.listEducation;
const originalListAwards = api.listAwards;
const originalCreateEducation = api.createEducation;
const originalDeleteEducation = api.deleteEducation;

const timestamps = {
	created_at: "2026-03-30T00:00:00",
	updated_at: "2026-03-30T00:00:00",
};

const educationFixture: Education = {
	id: 1,
	portfolio_id: "student@example.com",
	institution: "University of Victoria",
	degree: "BSc",
	field_of_study: "Computer Science",
	start_date: "2022-09-01",
	end_date: "2026-05-01",
	gpa: "3.9",
	honors: "Dean's List",
	...timestamps,
};

const awardFixture: Award = {
	id: 10,
	portfolio_id: "student@example.com",
	title: "Scholarship Award",
	issuer: "UVic",
	date: "2025-01-15",
	description: "Awarded for strong academic performance",
	...timestamps,
};

function SeedSelectedEmail({ email }: { email: string }) {
	const { setSelectedEmail } = useAppState();

	useEffect(() => {
		setSelectedEmail(email);
	}, [email, setSelectedEmail]);

	return createElement("box");
}

function createNode(onNext: (target: string) => void) {
	return createElement(
		AppProvider,
		null,
		createElement(SeedSelectedEmail, { email: "student@example.com" }),
		createElement(EducationAwardsScreen, { onNext }),
	);
}

async function flushEffects(view: RenderedScreen) {
	await act(async () => {
		await Promise.resolve();
		await Promise.resolve();
		await view.renderOnce();
	});
}

async function pressKey(view: RenderedScreen, key: KeyboardEventLike) {
	if (!keyboardHandler) {
		throw new Error("EducationAwardsScreen keyboard handler was not registered");
	}

	await act(async () => {
		keyboardHandler?.({
			option: false,
			eventType: "press",
			repeated: false,
			ctrl: false,
			meta: false,
			shift: false,
			...key,
		});
		await Promise.resolve();
		await view.renderOnce();
	});
}

async function typeText(view: RenderedScreen, text: string) {
	for (const character of text) {
		await pressKey(view, {
			name: character,
			sequence: character,
		});
	}
}

function destroyRenderer(view: RenderedScreen | null) {
	if (!view) {
		return;
	}

	act(() => {
		view.renderer.destroy();
	});
}

afterEach(() => {
	api.listEducation = originalListEducation;
	api.listAwards = originalListAwards;
	api.createEducation = originalCreateEducation;
	api.deleteEducation = originalDeleteEducation;
	keyboardHandler = null;
});

describe("EducationAwardsScreen", () => {
	test("fetches and renders education and awards on mount", async () => {
		const portfolioIds: string[] = [];
		let view: RenderedScreen | null = null;

		api.listEducation = async (portfolioId: string) => {
			portfolioIds.push(`education:${portfolioId}`);
			return [educationFixture];
		};
		api.listAwards = async (portfolioId: string) => {
			portfolioIds.push(`awards:${portfolioId}`);
			return [awardFixture];
		};

		try {
			view = await testRender(createNode(() => {}), { width: 140, height: 45 });
			await flushEffects(view);

			const frame = view.captureCharFrame();
			expect(portfolioIds).toEqual([
				"education:default",
				"awards:default",
				"education:student@example.com",
				"awards:student@example.com",
			]);
			expect(frame).toContain("Education & Awards");
			expect(frame).toContain("University of Victoria");
			expect(frame).toContain("Scholarship Award");
		} finally {
			destroyRenderer(view);
		}
	});

	test("creates a new education entry from keyboard input", async () => {
		let view: RenderedScreen | null = null;
		let createArgs:
			| { portfolioId: string; data: EducationCreateRequest }
			| undefined;

		api.listEducation = async () => [];
		api.listAwards = async () => [];
		api.createEducation = async (
			portfolioId: string,
			data: EducationCreateRequest,
		) => {
			createArgs = { portfolioId, data };
			return {
				id: 22,
				portfolio_id: portfolioId,
				...data,
				...timestamps,
			};
		};

		try {
			view = await testRender(createNode(() => {}), { width: 140, height: 45 });
			await flushEffects(view);

			await pressKey(view, { name: "n" });
			expect(view.captureCharFrame()).toContain("Add Education");

			await typeText(view, "UVic");
			await pressKey(view, { name: "tab" });
			await typeText(view, "BSc");
			await pressKey(view, { name: "tab" });
			await pressKey(view, { name: "tab" });
			await typeText(view, "2022-09-01");
			await pressKey(view, { name: "return" });
			await flushEffects(view);

			expect(createArgs).toEqual({
				portfolioId: "student@example.com",
				data: {
					institution: "UVic",
					degree: "BSc",
					field_of_study: null,
					start_date: "2022-09-01",
					end_date: null,
					gpa: null,
					honors: null,
				},
			});
			expect(view.captureCharFrame()).toContain("UVic - BSc");
		} finally {
			destroyRenderer(view);
		}
	});

	test("opens add mode and cancels back to view with Escape", async () => {
		let view: RenderedScreen | null = null;

		api.listEducation = async () => [educationFixture];
		api.listAwards = async () => [];

		try {
			view = await testRender(createNode(() => {}), { width: 140, height: 45 });
			await flushEffects(view);

			await pressKey(view, { name: "n" });
			expect(view.captureCharFrame()).toContain("Add Education");

			await pressKey(view, { name: "escape" });
			expect(view.captureCharFrame()).toContain("University of Victoria");
			expect(view.captureCharFrame()).not.toContain("Add Education");
		} finally {
			destroyRenderer(view);
		}
	});

	test("uses Enter and Escape to navigate forward and back", async () => {
		let view: RenderedScreen | null = null;
		const targets: string[] = [];

		api.listEducation = async () => [];
		api.listAwards = async () => [];

		try {
			view = await testRender(
				createNode((target) => {
					targets.push(target);
				}),
				{ width: 140, height: 45 },
			);
			await flushEffects(view);

			await pressKey(view, { name: "return" });
			await pressKey(view, { name: "escape" });

			expect(targets).toEqual(["analysis", "identity"]);
		} finally {
			destroyRenderer(view);
		}
	});
});
