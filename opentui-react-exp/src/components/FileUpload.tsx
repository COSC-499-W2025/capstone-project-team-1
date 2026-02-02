import { useKeyboard } from "@opentui/react";
import { homedir } from "node:os";
import { dirname } from "node:path";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";
import {
	scanForZips,
	buildEntries,
	filterEntries,
	getMatchCount,
	pathToBreadcrumbs,
	formatSize,
	type ZipFile,
	type DirEntry,
	type SearchableEntry,
} from "../utils";

interface FileUploadProps {
	onSubmit: (path: string) => void;
	onBack: () => void;
	/** Root path to scan for ZIPs. Defaults to homedir() */
	scanRoot?: string;
}

type ScanStatus = "idle" | "scanning" | "complete" | "error";

export function FileUpload({ onSubmit, onBack, scanRoot }: FileUploadProps) {
	const rootPath = scanRoot || homedir();
	const [currentPath, setCurrentPath] = useState(rootPath);
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [searchQuery, setSearchQuery] = useState("");
	const [isSearchFocused, setIsSearchFocused] = useState(false);

	// Global ZIP scan state
	const [allZips, setAllZips] = useState<ZipFile[]>([]);
	const [scanStatus, setScanStatus] = useState<ScanStatus>("idle");
	const scanAbortRef = useRef<boolean>(false);

	// Scan filesystem for all ZIP files
	const doScan = useCallback(async () => {
		setScanStatus("scanning");
		setAllZips([]); // Clear old data before new scan
		scanAbortRef.current = false;

		const result = await scanForZips({ rootPath });

		if (scanAbortRef.current) return;

		if (result.error) {
			setScanStatus("error");
		} else {
			setAllZips(result.zips);
			setScanStatus("complete");
		}
	}, [rootPath]);

	// Start scan on mount
	useEffect(() => {
		doScan();
		return () => {
			scanAbortRef.current = true;
		};
	}, [doScan]);

	// Build entries for current directory view
	const entries = useMemo(() => {
		return buildEntries(allZips, currentPath, rootPath);
	}, [allZips, currentPath, rootPath]);

	// Filter entries based on search
	const filteredEntries = useMemo(() => {
		return filterEntries(entries, searchQuery);
	}, [entries, searchQuery]);

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
			onSubmit(selectedEntry.fullPath);
			return;
		}

		if ("zipCount" in selectedEntry) {
			setCurrentPath(selectedEntry.fullPath);
		}
	};

	useKeyboard((key) => {
		if (key.name === "backspace" && currentPath !== rootPath && !isSearchFocused) {
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
		if (key.name === "r" && key.ctrl) {
			doScan();
		}
	});

	const breadcrumbs = pathToBreadcrumbs(currentPath);

	// Get display info for each entry
	const getEntryDisplay = (
		entry: SearchableEntry
	): { icon: string; name: string; description: string } => {
		if ("isParent" in entry && entry.isParent) {
			return { icon: "", name: "..", description: "Parent directory" };
		}

		if ("type" in entry && entry.type === "zip") {
			const sizeStr = entry.size !== undefined ? formatSize(entry.size) : "";
			return { icon: "📦", name: entry.name, description: sizeStr };
		}

		const dirEntry = entry as DirEntry;
		const zipLabel = dirEntry.zipCount === 1 ? "1 ZIP" : `${dirEntry.zipCount} ZIPs`;
		return { icon: "📁", name: dirEntry.name, description: zipLabel };
	};

	const getScanStatusText = (): string => {
		switch (scanStatus) {
			case "scanning":
				return "Scanning...";
			case "complete":
				return `${allZips.length} ZIPs found`;
			case "error":
				return "Scan failed";
			default:
				return "";
		}
	};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 1"
				title="Select Projects"
				description="Browse for your project zip file"
			/>

			<box flexGrow={1} flexDirection="column" padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.gold}
					flexDirection="column"
				>
					{/* Search Bar */}
					<box
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
						flexDirection="column"
						gap={1}
					>
						<box flexDirection="row" justifyContent="flex-end">
							<text>
								<span fg={scanStatus === "scanning" ? theme.gold : theme.success}>
									{getScanStatusText()}
								</span>
							</text>
						</box>

						<box
							border
							borderStyle="rounded"
							borderColor={isSearchFocused ? theme.cyan : theme.goldDim}
							paddingLeft={1}
							paddingRight={1}
							flexDirection="row"
							alignItems="center"
							gap={1}
						>
							<text>
								<span fg={isSearchFocused ? theme.cyan : theme.textDim}>🔍</span>
							</text>
							<input
								value={searchQuery}
								onChange={setSearchQuery}
								placeholder="Search for ZIP files..."
								focused={isSearchFocused}
								width={60}
							/>
							{searchQuery && (
								<text>
									<span fg={theme.cyan}>
										{getMatchCount(filteredEntries)} matches
									</span>
								</text>
							)}
						</box>
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
										value: entry.fullPath || entry.name,
									};
								})}
								onChange={(index) => setSelectedIndex(index)}
								onSelect={handleSelect}
								selectedIndex={selectedIndex}
								focused={!isSearchFocused}
								height={16}
								showScrollIndicator
							/>
						)}
					</box>

					{/* Breadcrumb Bar */}
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
							{breadcrumbs.map((crumb, i) => (
								<>
									<span
										key={i}
										fg={i === breadcrumbs.length - 1 ? theme.cyan : theme.textSecondary}
									>
										{crumb === "/" ? "~" : crumb}
									</span>
									{i < breadcrumbs.length - 1 && (
										<span fg={theme.textDim}> / </span>
									)}
								</>
							))}
						</text>
						{selectedEntry && "type" in selectedEntry && selectedEntry.type === "zip" ? (
							<text>
								<span fg={theme.success}>⏎ Select this ZIP</span>
							</text>
						) : selectedEntry && "zipCount" in selectedEntry && !("isParent" in selectedEntry && selectedEntry.isParent) ? (
							<text>
								<span fg={theme.textDim}>⏎ Open folder</span>
							</text>
						) : null}
					</box>
				</box>
			</box>
		</box>
	);
}
