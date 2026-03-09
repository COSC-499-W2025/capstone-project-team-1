import { describe, expect, test } from "bun:test";
import { testRender } from "@opentui/react/test-utils";
import { act, useEffect } from "react";
import type { PipelineContributorIdentity } from "../api/types";
import { AppProvider, useAppState } from "../context/AppContext";
import {
	formatContributorName,
	getNextSelectedIndex,
	getToggledFocusMode,
	IdentityScreen,
	resolveIdentitySelection,
} from "./IdentityScreen";

const contributorsFixture: PipelineContributorIdentity[] = [
	{
		email: "first@example.com",
		name: "First Dev",
		repo_count: 2,
		commit_count: 15,
		candidate_username: "firstdev",
	},
	{
		email: "second@example.com",
		name: "Second Dev",
		repo_count: 4,
		commit_count: 28,
		candidate_username: "seconddev",
	},
];

function SeedIdentityState({ contributors }: { contributors: PipelineContributorIdentity[] }) {
	const { setContributors } = useAppState();

	useEffect(() => {
		setContributors(contributors);
	}, [contributors, setContributors]);

	return null;
}

describe("IdentityScreen helpers", () => {
	test("formats contributor metadata for rendering", () => {
		const contributor = contributorsFixture[0]!;
		expect(formatContributorName(contributor)).toBe("First Dev");
		expect(formatContributorName({
			...contributor,
			name: null,
		})).toBe("firstdev");
	});

	test("toggles focus mode and keeps manual mode when no contributors exist", () => {
		expect(getToggledFocusMode("list", 2)).toBe("manual");
		expect(getToggledFocusMode("manual", 2)).toBe("list");
		expect(getToggledFocusMode("list", 0)).toBe("manual");
	});

	test("moves selected index within list bounds", () => {
		expect(getNextSelectedIndex(0, "up", 2)).toBe(0);
		expect(getNextSelectedIndex(0, "down", 2)).toBe(1);
		expect(getNextSelectedIndex(1, "down", 2)).toBe(1);
		expect(getNextSelectedIndex(5, "down", 0)).toBe(0);
	});

	test("resolves contributor and manual identity selections", () => {
		expect(
			resolveIdentitySelection({
				focusMode: "list",
				manualEmail: "",
				selectedContributor: contributorsFixture[1],
			}),
		).toEqual({ selectedEmail: "second@example.com" });

		expect(
			resolveIdentitySelection({
				focusMode: "manual",
				manualEmail: " Manual@Example.com ",
			}),
		).toEqual({ selectedEmail: "manual@example.com" });

		expect(
			resolveIdentitySelection({
				focusMode: "manual",
				manualEmail: "   ",
			}),
		).toEqual({ error: "Enter an email to continue." });
	});
});

describe("IdentityScreen rendering", () => {
	test("renders detected contributors from app state", async () => {
		const view = await testRender(
			<AppProvider>
				<SeedIdentityState contributors={contributorsFixture} />
				<IdentityScreen onNext={() => {}} />
			</AppProvider>,
			{ width: 120, height: 40 },
		);

		await act(async () => {
			await view.renderOnce();
		});

		const frame = view.captureCharFrame();
		expect(frame).toContain("Detected Contributors");
		expect(frame).toContain("First Dev <first@example.com>");
		expect(frame).toContain("Manual Email Entry");

		await act(async () => {
			view.renderer.destroy();
		});
	});
});
