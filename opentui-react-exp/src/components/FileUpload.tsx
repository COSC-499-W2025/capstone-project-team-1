import { useKeyboard } from "@opentui/react";
import { fdir } from "fdir";
import Fuse from "fuse.js";
import { stat } from "node:fs/promises";
import { homedir } from "node:os";
import { join, dirname, basename } from "node:path";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface FileUploadProps {
	onSubmit: (path: string) => void;
	onBack: () => void;
}

type ZipFile = {
	name: string;
	fullPath: string;
	size?: number;
	parentDir: string;
};

type DirEntry = {
	name: string;
	fullPath: string;
	zipCount: number; // Number of ZIPs in this dir (recursively)
	isParent?: boolean;
};

type ScanStatus = "idle" | "scanning" | "complete" | "error";

const formatSize = (bytes: number): string => {
	if (bytes < 1024) return `${bytes} B`;
	if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	if (bytes < 1024 * 1024 * 1024)
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
};

// Convert path to breadcrumb segments
const pathToBreadcrumbs = (path: string): string[] => {
	if (path === "/") return ["/"];
	const parts = path.split("/").filter(Boolean);
	return ["/", ...parts];
};

export function FileUpload({ onSubmit, onBack }: FileUploadProps) {
	const [currentPath, setCurrentPath] = useState(homedir());
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [searchQuery, setSearchQuery] = useState("");
	const [isSearchFocused, setIsSearchFocused] = useState(false);

	// Global ZIP scan state
	const [allZips, setAllZips] = useState<ZipFile[]>([]);
	const [scanStatus, setScanStatus] = useState<ScanStatus>("idle");
	const [filesScanned, setFilesScanned] = useState(0);
	const scanAbortRef = useRef<boolean>(false);

	// Scan filesystem for all ZIP files using fdir
	const scanForZips = useCallback(async () => {
		setScanStatus("scanning");
		setFilesScanned(0);
		scanAbortRef.current = false;

		try {
			const crawler = new fdir()
				.withFullPaths()
				.filter((path) => path.toLowerCase().endsWith(".zip"))
				.exclude((dirName) => {
					// Skip system directories that are slow or inaccessible
					const skipDirs = [
						"node_modules",
						".git",
						".Trash",
						"Library",
						"System",
						"Applications",
						".cache",
						".npm",
						".bun",
						".vscode",
						".idea",
					];
					return skipDirs.includes(dirName);
				})
				.crawl(homedir());

			const files = await crawler.withPromise();

			if (scanAbortRef.current) return;

			// Convert to ZipFile format and get file sizes
			const zipFiles: ZipFile[] = await Promise.all(
				files.map(async (filePath) => {
					let size: number | undefined;
					try {
						const stats = await stat(filePath);
						size = stats.size;
					} catch {
						// Ignore stat errors
					}
					return {
						name: basename(filePath),
						fullPath: filePath,
						parentDir: dirname(filePath),
						size,
					};
				})
			);

			setAllZips(zipFiles);
			setFilesScanned(zipFiles.length);
			setScanStatus("complete");
		} catch (err) {
			if (!scanAbortRef.current) {
				setScanStatus("error");
			}
		}
	}, []);

	// Start scan on mount
	useEffect(() => {
		scanForZips();
		return () => {
			scanAbortRef.current = true;
		};
	}, [scanForZips]);

	// Build set of all directories that contain ZIPs (at any depth)
	const dirsWithZips = useMemo(() => {
		const dirs = new Set<string>();
		for (const zip of allZips) {
			// Add all parent directories up to home
			let dir = zip.parentDir;
			const home = homedir();
			while (dir.startsWith(home) && dir !== home) {
				dirs.add(dir);
				dir = dirname(dir);
			}
			dirs.add(home); // Include home if it has zips
		}
		return dirs;
	}, [allZips]);

	// Get ZIPs in current directory
	const zipsInCurrentDir = useMemo(() => {
		return allZips.filter((zip) => zip.parentDir === currentPath);
	}, [allZips, currentPath]);

	// Get subdirectories that have ZIPs (direct children only)
	const dirsInCurrentPath = useMemo(() => {
		const childDirs = new Map<string, number>();
		
		for (const zip of allZips) {
			// Check if this ZIP is under the current path
			if (!zip.parentDir.startsWith(currentPath)) continue;
			if (zip.parentDir === currentPath) continue; // Skip ZIPs directly in current dir
			
			// Get the immediate child directory
			const relativePath = zip.parentDir.slice(currentPath.length);
			const parts = relativePath.split("/").filter(Boolean);
			if (parts.length === 0) continue;
			
			const childDir = parts[0];
			const fullChildPath = join(currentPath, childDir);
			
			childDirs.set(fullChildPath, (childDirs.get(fullChildPath) || 0) + 1);
		}

		const entries: DirEntry[] = Array.from(childDirs.entries()).map(
			([fullPath, zipCount]) => ({
				name: basename(fullPath),
				fullPath,
				zipCount,
			})
		);

		return entries.sort((a, b) => a.name.localeCompare(b.name));
	}, [allZips, currentPath]);

	// Combined entries: parent + directories with ZIPs + ZIPs in current dir
	const entries = useMemo(() => {
		const result: Array<DirEntry | (ZipFile & { type: "zip" })> = [];

		// Add parent directory if not at home
		if (currentPath !== homedir()) {
			result.push({
				name: "..",
				fullPath: dirname(currentPath),
				zipCount: 0,
				isParent: true,
			});
		}

		// Add directories that contain ZIPs
		for (const dir of dirsInCurrentPath) {
			result.push(dir);
		}

		// Add ZIPs in current directory
		for (const zip of zipsInCurrentDir) {
			result.push({ ...zip, type: "zip" });
		}

		return result;
	}, [currentPath, dirsInCurrentPath, zipsInCurrentDir]);

	// Fuse.js fuzzy search
	const fuse = useMemo(() => {
		return new Fuse(entries.filter((e) => !("isParent" in e && e.isParent)), {
			keys: ["name", "fullPath"],
			threshold: 0.4,
			includeScore: true,
		});
	}, [entries]);

	const filteredEntries = useMemo(() => {
		if (!searchQuery.trim()) {
			return entries;
		}
		const results = fuse.search(searchQuery);
		const parentEntry = entries.find((e) => "isParent" in e && e.isParent);
		const filtered = results.map((r) => r.item);
		return parentEntry ? [parentEntry, ...filtered] : filtered;
	}, [entries, searchQuery, fuse]);

	// Reset selection when entries change
	useEffect(() => {
		setSelectedIndex(0);
	}, [filteredEntries.length, currentPath]);

	// Reset search when changing directories
	useEffect(() => {
		setSearchQuery("");
		setIsSearchFocused(false);
	}, [currentPath]);

	const selectedEntry = filteredEntries[selectedIndex];

	const handleSelect = () => {
		if (!selectedEntry) return;

		if ("isParent" in selectedEntry && selectedEntry.isParent) {
			setCurrentPath(dirname(currentPath));
			return;
		}

		if ("type" in selectedEntry && selectedEntry.type === "zip") {
			// ZIP selected - submit it
			onSubmit(selectedEntry.fullPath);
			return;
		}

		// Directory selected - navigate into it
		if ("zipCount" in selectedEntry) {
			setCurrentPath(selectedEntry.fullPath);
		}
	};

	useKeyboard((key) => {
		if (key.name === "backspace" && currentPath !== homedir() && !isSearchFocused) {
			setCurrentPath(dirname(currentPath));
		}
		if (key.sequence === "/" && !isSearchFocused) {
			setIsSearchFocused(true);
		}
		if (key.name === "escape" && isSearchFocused) {
			if (searchQuery) {
				setSearchQuery("");
			} else {
				setIsSearchFocused(false);
			}
		}
		if (key.name === "return" && isSearchFocused) {
			setIsSearchFocused(false);
		}
		// Rescan with Ctrl+R
		if (key.name === "r" && key.ctrl) {
			scanForZips();
		}
	});

	const breadcrumbs = pathToBreadcrumbs(currentPath);

	// Get display info for each entry
	const getEntryDisplay = (
		entry: DirEntry | (ZipFile & { type: "zip" })
	): { icon: string; name: string; description: string } => {
		if ("isParent" in entry && entry.isParent) {
			return { icon: "", name: "..", description: "Parent directory" };
		}

		if ("type" in entry && entry.type === "zip") {
			const sizeStr = entry.size !== undefined ? formatSize(entry.size) : "";
			return { icon: "📦", name: entry.name, description: sizeStr };
		}

		// Directory with ZIPs
		const zipLabel = entry.zipCount === 1 ? "1 ZIP" : `${entry.zipCount} ZIPs`;
		return { icon: "📁", name: entry.name, description: zipLabel };
	};

	// Scan status display
	const getScanStatusText = (): string => {
		switch (scanStatus) {
			case "scanning":
				return `Scanning... ${filesScanned} ZIPs`;
			case "complete":
				return `${allZips.length} ZIPs found`;
			case "error":
				return "Scan failed";
			default:
				return "";
		}
	};

	const getSelectedInfo = (): string => {
		if (!selectedEntry) return "No selection";

		if ("isParent" in selectedEntry && selectedEntry.isParent) {
			return "Go to parent directory";
		}

		if ("type" in selectedEntry && selectedEntry.type === "zip") {
			return `${selectedEntry.name} • ZIP Archive • Ready for analysis`;
		}

		if ("zipCount" in selectedEntry) {
			return `${selectedEntry.name} • Folder • Contains ${selectedEntry.zipCount} ZIP${selectedEntry.zipCount > 1 ? "s" : ""}`;
		}

		return "";
	};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 1"
				title="Select Projects"
				description="Browse for your project zip file"
			/>

			<box flexGrow={1} flexDirection="column" padding={1}>
				{/* Main Panel */}
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.gold}
					flexDirection="column"
				>
					{/* Breadcrumb Navigation */}
					<box
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
						flexDirection="row"
						justifyContent="space-between"
						alignItems="center"
					>
						<text>
							<span fg={theme.textDim}>Location: </span>
							{breadcrumbs.map((crumb, i) => (
								<>
									<span
										key={i}
										fg={i === breadcrumbs.length - 1 ? theme.cyan : theme.textSecondary}
									>
										{crumb === "/" ? "~" : crumb}
									</span>
									{i < breadcrumbs.length - 1 && (
										<span fg={theme.textDim}> → </span>
									)}
								</>
							))}
						</text>
						{/* Scan status on the right */}
						<text>
							<span fg={scanStatus === "scanning" ? theme.gold : theme.success}>
								{getScanStatusText()}
							</span>
						</text>
					</box>

					{/* Divider */}
					<box paddingLeft={2} paddingRight={2}>
						<text>
							<span fg={theme.goldDim}>{"─".repeat(68)}</span>
						</text>
					</box>

					{/* Search Bar - Boxed */}
					<box
						marginLeft={2}
						marginRight={2}
						marginTop={1}
						marginBottom={1}
						border
						borderStyle="rounded"
						borderColor={isSearchFocused ? theme.cyan : theme.textDim}
						paddingLeft={1}
						paddingRight={1}
						flexDirection="row"
						alignItems="center"
						gap={1}
					>
						<text>
							<span fg={isSearchFocused ? theme.cyan : theme.textDim}>Search:</span>
						</text>
						<input
							value={searchQuery}
							onChange={setSearchQuery}
							placeholder="Type to filter..."
							focused={isSearchFocused}
							onFocus={() => setIsSearchFocused(true)}
							onBlur={() => setIsSearchFocused(false)}
							width={35}
						/>
						{searchQuery ? (
							<text>
								<span fg={theme.cyan}>
									{filteredEntries.length - (entries.find((e) => "isParent" in e && e.isParent) ? 1 : 0)} found
								</span>
							</text>
						) : (
							<text>
								<span fg={theme.textDim}>Press / to search</span>
							</text>
						)}
					</box>

					{/* File List */}
					<box flexGrow={1} paddingLeft={1} paddingRight={1}>
						{scanStatus === "scanning" ? (
							<box padding={1}>
								<text>
									<span fg={theme.gold}>Scanning for ZIP files...</span>
								</text>
							</box>
						) : filteredEntries.length === 0 ? (
							<box padding={1}>
								<text>
									<span fg={theme.textDim}>
										{searchQuery ? "No matches found" : "No ZIP files in this location"}
									</span>
								</text>
							</box>
						) : (
							<select
								options={filteredEntries.map((entry) => {
									const display = getEntryDisplay(entry);
									return {
										name: display.icon ? `${display.icon} ${display.name}` : display.name,
										description: display.description,
										value: "fullPath" in entry ? entry.fullPath : entry.name,
									};
								})}
								onChange={(index) => setSelectedIndex(index)}
								onSelect={handleSelect}
								selectedIndex={selectedIndex}
								focused={!isSearchFocused}
								height={14}
								showScrollIndicator
							/>
						)}
					</box>

					{/* Divider */}
					<box paddingLeft={2} paddingRight={2}>
						<text>
							<span fg={theme.goldDim}>{"─".repeat(68)}</span>
						</text>
					</box>

					{/* Selected Item Info Bar */}
					<box
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
						flexDirection="row"
						gap={1}
					>
						<text>
							<span fg={theme.textDim}>Selected: </span>
							<span fg={selectedEntry && "type" in selectedEntry && selectedEntry.type === "zip" ? theme.success : theme.textPrimary}>
								{getSelectedInfo()}
							</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);
}
