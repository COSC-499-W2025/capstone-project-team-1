import { useKeyboard } from "@opentui/react";
import Fuse from "fuse.js";
import { readdir, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { join, dirname, basename } from "node:path";
import { useEffect, useState, useCallback, useMemo } from "react";
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
	const [searchQuery, setSearchQuery] = useState("");
	const [isSearchFocused, setIsSearchFocused] = useState(false);

	const loadDirectory = useCallback(async (dirPath: string) => {
		setLoading(true);
		setError(null);
		setSelectedStats(null);

		try {
			const dirents = await readdir(dirPath, { withFileTypes: true });

			const fileEntries: FileEntry[] = dirents
				.filter((dirent) => !dirent.name.startsWith(".") || showHidden)
				.filter((dirent) => {
					// Show all directories (for navigation) and only .zip files
					if (dirent.isDirectory()) return true;
					return dirent.name.toLowerCase().endsWith(".zip");
				})
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

	// Reset search when changing directories
	useEffect(() => {
		setSearchQuery("");
		setIsSearchFocused(false);
	}, [currentPath]);

	// Fuse.js fuzzy search
	const fuse = useMemo(() => {
		return new Fuse(entries.filter((e) => !e.isParent), {
			keys: ["name"],
			threshold: 0.4,
			includeScore: true,
		});
	}, [entries]);

	const filteredEntries = useMemo(() => {
		if (!searchQuery.trim()) {
			return entries;
		}
		const results = fuse.search(searchQuery);
		const parentEntry = entries.find((e) => e.isParent);
		const filtered = results.map((r) => r.item);
		// Always keep parent entry at top when searching
		return parentEntry ? [parentEntry, ...filtered] : filtered;
	}, [entries, searchQuery, fuse]);

	// Reset selection when filtered results change
	useEffect(() => {
		setSelectedIndex(0);
	}, [filteredEntries.length]);

	const selectedEntry = filteredEntries[selectedIndex];

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
		if (key.name === "backspace" && currentPath !== "/" && !isSearchFocused) {
			setCurrentPath(dirname(currentPath));
		}
		if (key.name === "h" && key.ctrl) {
			setShowHidden((prev) => !prev);
		}
		// "/" to focus search
		if (key.sequence === "/" && !isSearchFocused) {
			setIsSearchFocused(true);
		}
		// Escape to clear/exit search
		if (key.name === "escape" && isSearchFocused) {
			if (searchQuery) {
				setSearchQuery("");
			} else {
				setIsSearchFocused(false);
			}
		}
		// Enter while in search to exit search and keep focus on list
		if (key.name === "return" && isSearchFocused) {
			setIsSearchFocused(false);
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

					{/* Search Bar */}
					<box marginTop={1} flexDirection="row" gap={1}>
						<text>
							<span fg={theme.cyan}>/</span>
						</text>
						<input
							value={searchQuery}
							onChange={setSearchQuery}
							placeholder="Search files..."
							focused={isSearchFocused}
							onFocus={() => setIsSearchFocused(true)}
							onBlur={() => setIsSearchFocused(false)}
							width={30}
						/>
						{searchQuery && (
							<text>
								<span fg={theme.textDim}>
									({filteredEntries.length - (entries.find((e) => e.isParent) ? 1 : 0)} results)
								</span>
							</text>
						)}
					</box>

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
					) : filteredEntries.length === 0 ? (
						<box marginTop={1}>
							<text>
								<span fg={theme.textDim}>
									{searchQuery ? "No matches found" : "Empty directory"}
								</span>
							</text>
						</box>
					) : (
						<box flexDirection="column" marginTop={1}>
							<select
								options={filteredEntries.map((entry) => ({
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
								focused={!isSearchFocused}
								height={14}
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

				</box>
			</box>
		</box>
	);
}
