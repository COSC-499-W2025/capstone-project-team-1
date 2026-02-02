import { useKeyboard } from "@opentui/react";
import { readdir, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { join, dirname, basename } from "node:path";
import { useEffect, useState, useCallback } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface FileUploadProps {
	onSubmit: (path: string) => void;
	onBack: () => void;
}

type FileEntry = {
	name: string;
	type: "dir" | "file";
	size?: number;
	modifiedAt?: Date;
	isParent?: boolean;
};

const formatSize = (bytes: number): string => {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	if (bytes < 1024 * 1024 * 1024)
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

const formatDate = (date: Date): string => {
	return date.toLocaleDateString("en-US", {
		year: "numeric",
		month: "short",
		day: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
};

const sortEntries = (a: FileEntry, b: FileEntry): number => {
	if (a.isParent) return -1;
	if (b.isParent) return 1;
	if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
	return a.name.localeCompare(b.name);
};

export function FileUpload({ onSubmit, onBack }: FileUploadProps) {
	const [currentPath, setCurrentPath] = useState(homedir());
	const [entries, setEntries] = useState<FileEntry[]>([]);
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [showHidden, setShowHidden] = useState(false);
	const [selectedStats, setSelectedStats] = useState<{
		size?: number;
		modifiedAt?: Date;
		itemCount?: number;
	} | null>(null);

	const loadDirectory = useCallback(async (dirPath: string) => {
		setLoading(true);
		setError(null);
		setSelectedStats(null);

		try {
			const dirents = await readdir(dirPath, { withFileTypes: true });

			const fileEntries: FileEntry[] = dirents
				.filter((dirent) => !dirent.name.startsWith(".") || showHidden)
				.map((dirent) => ({
					name: dirent.name,
					type: dirent.isDirectory() ? "dir" : "file",
				}));

			const isRoot = dirPath === "/";
			const withParent: FileEntry[] = isRoot
				? []
				: [{ name: "..", type: "dir", isParent: true }];

			setEntries([...withParent, ...fileEntries].sort(sortEntries));
			setSelectedIndex(0);
		} catch (err) {
			setError(
				err instanceof Error ? err.message : "Failed to read directory",
			);
			setEntries([]);
		} finally {
			setLoading(false);
		}
	}, [showHidden]);

	useEffect(() => {
		loadDirectory(currentPath);
	}, [currentPath, loadDirectory]);

	const selectedEntry = entries[selectedIndex];

	// Load stats for selected entry
	useEffect(() => {
		if (!selectedEntry || selectedEntry.isParent) {
			setSelectedStats(null);
			return;
		}

		const entryPath = join(currentPath, selectedEntry.name);

		(async () => {
			try {
				const stats = await stat(entryPath);
				if (selectedEntry.type === "dir") {
					const contents = await readdir(entryPath);
					setSelectedStats({
						modifiedAt: stats.mtime,
						itemCount: contents.length,
					});
				} else {
					setSelectedStats({
						size: stats.size,
						modifiedAt: stats.mtime,
					});
				}
			} catch {
				setSelectedStats(null);
			}
		})();
	}, [selectedEntry, currentPath]);

	const selectedPath = selectedEntry
		? selectedEntry.isParent
			? dirname(currentPath)
			: join(currentPath, selectedEntry.name)
		: currentPath;

	const handleSelect = () => {
		if (!selectedEntry) return;

		if (selectedEntry.isParent) {
			setCurrentPath(dirname(currentPath));
			return;
		}

		if (selectedEntry.type === "dir") {
			setCurrentPath(join(currentPath, selectedEntry.name));
			return;
		}

		// File selected - submit it
		onSubmit(selectedPath);
	};

	useKeyboard((key) => {
		if (key.name === "backspace" && currentPath !== "/") {
			setCurrentPath(dirname(currentPath));
		}
		if (key.name === "h" && key.ctrl) {
			setShowHidden((prev) => !prev);
		}
	});

	const displayPath = currentPath === "/" ? "/" : `${currentPath}/`;

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
						{showHidden && (
							<span fg={theme.textDim}> (showing hidden)</span>
						)}
					</text>
					<text>
						<span fg={theme.textDim}>{displayPath}</span>
					</text>

					{loading ? (
						<box marginTop={1}>
							<text>
								<span fg={theme.cyan}>Loading...</span>
							</text>
						</box>
					) : error ? (
						<box marginTop={1}>
							<text>
								<span fg={theme.error}>Error: {error}</span>
							</text>
						</box>
					) : entries.length === 0 ? (
						<box marginTop={1}>
							<text>
								<span fg={theme.textDim}>Empty directory</span>
							</text>
						</box>
					) : (
						<box flexDirection="column" marginTop={1}>
							<select
								options={entries.map((entry) => ({
									name: entry.isParent
										? ".."
										: `${entry.type === "dir" ? "📁" : "📄"} ${entry.name}`,
									description: entry.isParent
										? "Parent directory"
										: entry.type === "dir"
											? "Directory"
											: "File",
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
					)}
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
								{selectedStats?.size !== undefined
									? formatSize(selectedStats.size)
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
							Modified:{" "}
							<span fg={theme.textPrimary}>
								{selectedStats?.modifiedAt
									? formatDate(selectedStats.modifiedAt)
									: "-"}
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
										• {selectedStats?.itemCount ?? "?"} items
									</text>
								</>
							) : selectedEntry?.name.endsWith(".zip") ? (
								<>
									<text>
										<span fg={theme.success}>ZIP Archive</span>
									</text>
									<text>• Ready for analysis</text>
									<text>• Press Enter to select</text>
								</>
							) : (
								<text>
									<span fg={theme.textDim}>
										Select a .zip file for analysis
									</span>
								</text>
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
						marginTop={2}
						border
						borderStyle="single"
						borderColor={theme.cyanDim}
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
					>
						<text>
							<span fg={theme.cyan}>Shortcuts:</span>
						</text>
						<text>
							<span fg={theme.textDim}>Backspace</span>
							<span fg={theme.textPrimary}> - Go up</span>
						</text>
						<text>
							<span fg={theme.textDim}>Ctrl+H</span>
							<span fg={theme.textPrimary}> - Toggle hidden files</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
