import { useKeyboard } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface FileUploadProps {
	onSubmit: (path: string) => void;
	onBack: () => void;
}

type FileNode = {
	name: string;
	type: "dir" | "file";
	size?: string;
	children?: FileNode[];
};

type FileEntry = FileNode & { isParent?: boolean };

// Mock file system data
const mockFileSystem: FileNode = {
	name: "root",
	type: "dir",
	children: [
		{
			name: "Users",
			type: "dir",
			children: [
				{
					name: "shlok",
					type: "dir",
					children: [
						{
							name: "projects",
							type: "dir",
							children: [
								{ name: "opentui-react", type: "dir" },
								{ name: "capstone-project.zip", type: "file", size: "12 MB" },
								{ name: "personal-site.zip", type: "file", size: "4.5 MB" },
							],
						},
						{ name: "Documents", type: "dir" },
						{
							name: "Downloads",
							type: "dir",
							children: [
								{ name: "resume-data.zip", type: "file", size: "2 MB" },
								{ name: "images.zip", type: "file", size: "150 MB" },
							],
						},
					],
				},
			],
		},
		{ name: "var", type: "dir" },
		{ name: "tmp", type: "dir" },
	],
};

const getNodeAtPath = (root: FileNode, segments: string[]) => {
	let node: FileNode | undefined = root;
	for (const segment of segments) {
		const next = node.children?.find(
			(child) => child.type === "dir" && child.name === segment,
		);
		if (!next) {
			return undefined;
		}
		node = next;
	}
	return node;
};

const buildPath = (segments: string[], name?: string) => {
	const base = `/${segments.join("/")}`;
	if (!name) {
		return base === "" ? "/" : base;
	}
	return base === "" || base === "/" ? `/${name}` : `${base}/${name}`;
};

const sortEntries = (a: FileEntry, b: FileEntry) => {
	if (a.isParent) return -1;
	if (b.isParent) return 1;
	if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
	return a.name.localeCompare(b.name);
};

export function FileUpload({ onSubmit, onBack }: FileUploadProps) {
	const [currentPathSegments, setCurrentPathSegments] = useState([
		"Users",
		"shlok",
		"projects",
	]);
	const [selectedIndex, setSelectedIndex] = useState(0);

	const currentNode = useMemo(
		() => getNodeAtPath(mockFileSystem, currentPathSegments),
		[currentPathSegments],
	);
	const entries = useMemo(() => {
		const baseEntries = currentNode?.children ?? [];
		const withParent: FileEntry[] = currentPathSegments.length
			? [{ name: "..", type: "dir", isParent: true }]
			: [];
		return [...withParent, ...baseEntries].sort(sortEntries);
	}, [currentNode, currentPathSegments]);

	useEffect(() => {
		if (selectedIndex >= entries.length) {
			setSelectedIndex(0);
		}
	}, [entries.length, selectedIndex]);

	const selectedEntry = entries[selectedIndex];
	const currentPath = buildPath(currentPathSegments);
	const displayPath = currentPath === "/" ? "/" : `${currentPath}/`;
	const selectedPath = selectedEntry
		? selectedEntry.isParent
			? buildPath(currentPathSegments.slice(0, -1))
			: buildPath(currentPathSegments, selectedEntry.name)
		: currentPath;

	const handleSelect = () => {
		if (!selectedEntry) return;
		if (selectedEntry.isParent) {
			setCurrentPathSegments((segments) => segments.slice(0, -1));
			return;
		}
		if (selectedEntry.type === "dir") {
			setCurrentPathSegments((segments) => [...segments, selectedEntry.name]);
			return;
		}
		onSubmit(selectedPath);
	};

	useKeyboard((key) => {
		if (key.name === "backspace" && currentPathSegments.length > 0) {
			setCurrentPathSegments((segments) => segments.slice(0, -1));
		}
	});

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 1"
				title="Select Projects"
				description="Browse for your project zip file"
			/>

			<box flexGrow={1} flexDirection="row" padding={1} gap={1}>
				{/* Left Panel: Directory Tree */}
				<box
					width="60%"
					border
					borderStyle="rounded"
					borderColor={theme.gold}
					flexDirection="column"
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>File Browser</strong>
						</span>
					</text>
					<text>
						<span fg={theme.textDim}>{displayPath}</span>
					</text>
					<box flexDirection="column" marginTop={1}>
						<select
							options={entries.map((entry) => ({
								name: entry.isParent
									? ".."
									: `${entry.type === "dir" ? "📁" : "📄"} ${entry.name}`,
								description: entry.isParent
									? "Parent directory"
									: entry.type === "dir"
										? `${entry.children?.length ?? 0} items`
										: entry.size ?? "File",
								value: entry.name,
							}))}
							onChange={(index) => setSelectedIndex(index)}
							onSelect={handleSelect}
							selectedIndex={selectedIndex}
							focused
							height={16}
							showScrollIndicator
						/>
					</box>
				</box>

				{/* Right Panel: Details */}
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.textDim}
					flexDirection="column"
					padding={1}
				>
					<text>
						<span fg={theme.gold}>
							<strong>Details</strong>
						</span>
					</text>
					<box flexDirection="column" marginTop={1} gap={1}>
						<text>
							Name:{" "}
							<span fg={theme.textPrimary}>
								{selectedEntry?.isParent
									? ".."
									: selectedEntry?.name ?? "-"}
							</span>
						</text>
						<text>
							Size:{" "}
							<span fg={theme.textPrimary}>
								{selectedEntry?.type === "file"
									? selectedEntry.size ?? "Unknown"
									: "-"}
							</span>
						</text>
						<text>
							Type:{" "}
							<span fg={theme.textPrimary}>
								{selectedEntry?.isParent
									? "Parent Directory"
									: selectedEntry?.type === "dir"
										? "Folder"
										: "File"}
							</span>
						</text>
						<text>
							Path:{" "}
							<span fg={theme.textPrimary}>{selectedPath}</span>
						</text>

						<box
							marginTop={2}
							border
							borderStyle="single"
							borderColor={theme.textDim}
							padding={1}
						>
							{selectedEntry?.isParent ? (
								<text>Move up to the parent directory.</text>
							) : selectedEntry?.type === "dir" ? (
								<>
									<text>Contains:</text>
									<text>
										• {selectedEntry.children?.length ?? 0} items
									</text>
									<text>• Folders and files</text>
								</>
							) : (
								<>
									<text>Details:</text>
									<text>• ZIP Archive</text>
									<text>• Ready for analysis</text>
								</>
							)}
						</box>
					</box>

					<box marginTop={3}>
						<text>
							<span fg={theme.textDim}>Press </span>
							<span fg={theme.cyan}>Enter</span>
							<span fg={theme.textDim}> to open/select</span>
						</text>
					</box>

					<box
						marginTop={5}
						border
						borderStyle="single"
						borderColor={theme.error}
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
					>
						<text>
							<span fg={theme.goldDark}>Demo Mode:</span>
							<span fg={theme.textDim}> Press </span>
							<span fg={theme.cyan}>Enter</span>
							<span fg={theme.textDim}> to select, </span>
							<span fg={theme.cyan}>Backspace</span>
							<span fg={theme.textDim}> to go up</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
