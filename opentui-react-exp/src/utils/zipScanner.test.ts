import { expect, test } from "bun:test";
import {
	buildEntries,
	getChildDirsWithZips,
	type ZipFile,
} from "./zipScanner";

const rootPath = "/workspace";

const zips: ZipFile[] = [
	{
		name: "visible.zip",
		fullPath: "/workspace/projects/visible.zip",
		parentDir: "/workspace/projects",
	},
	{
		name: "hidden.zip",
		fullPath: "/workspace/.git/hidden.zip",
		parentDir: "/workspace/.git",
	},
	{
		name: "nested.zip",
		fullPath: "/workspace/projects/app/nested.zip",
		parentDir: "/workspace/projects/app",
	},
];

test("getChildDirsWithZips excludes hidden child directories", () => {
	const entries = getChildDirsWithZips(zips, rootPath);

	expect(entries).toEqual([
		{
			name: "projects",
			fullPath: "/workspace/projects",
			zipCount: 2,
		},
	]);
});

test("buildEntries does not expose hidden directories in the browser list", () => {
	const entries = buildEntries(zips, rootPath, rootPath);

	expect(entries).toEqual([
		{
			name: "projects",
			fullPath: "/workspace/projects",
			zipCount: 2,
		},
	]);
});
