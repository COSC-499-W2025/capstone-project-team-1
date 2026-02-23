import { homedir } from "node:os";
import { dirname } from "node:path";
import { useKeyboard } from "@opentui/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/endpoints";
import type { PipelineIntakeResponse } from "../api/types";
import { theme } from "../types";
import {
	buildEntries,
	type DirEntry,
	filterEntries,
	formatSize,
	getMatchCount,
	pathToBreadcrumbs,
	type SearchableEntry,
	scanForZips,
	toErrorMessage,
	type ZipFile,
} from "../utils";
import { TopBar } from "./TopBar";

interface FileUploadProps {
	onIntakeCreated: (zipPath: string, intake: PipelineIntakeResponse) => void;
	onBack: () => void;
	scanRoot?: string;
}

type ScanStatus = "idle" | "scanning" | "complete" | "error";

export function FileUpload({
	onIntakeCreated,
	onBack,
	scanRoot,
}: FileUploadProps) {
	const rootPath = scanRoot || homedir();
	const [currentPath, setCurrentPath] = useState(rootPath);
	const [selectedIndex, setSelectedIndex] = useState(0);
	const [searchQuery, setSearchQuery] = useState("");
	const [isSearchFocused, setIsSearchFocused] = useState(false);
	const [isSubmitting, setIsSubmitting] = useState(false);
	const [errorMessage, setErrorMessage] = useState<string | null>(null);

	const [allZips, setAllZips] = useState<ZipFile[]>([]);
	const [scanStatus, setScanStatus] = useState<ScanStatus>("idle");
	const scanAbortRef = useRef<boolean>(false);

	const doScan = useCallback(async () => {
		setScanStatus("scanning");
		setAllZips([]);
		scanAbortRef.current = false;
		setErrorMessage(null);

		const result = await scanForZips({ rootPath });

		if (scanAbortRef.current) {
			return;
		}

		if (result.error) {
			setScanStatus("error");
			setErrorMessage(result.error);
			return;
		}

		setAllZips(result.zips);
		setScanStatus("complete");
	}, [rootPath]);

	useEffect(() => {
		doScan();
		return () => {
			scanAbortRef.current = true;
		};
	}, [doScan]);

	const entries = useMemo(() => {
		return buildEntries(allZips, currentPath, rootPath);
	}, [allZips, currentPath, rootPath]);

	const filteredEntries = useMemo(() => {
		return filterEntries(entries, searchQuery);
	}, [entries, searchQuery]);

	useEffect(() => {
		if (filteredEntries.length < 0 || !currentPath) {
			return;
		}
		setSelectedIndex(0);
	}, [filteredEntries.length, currentPath]);

	useEffect(() => {
		if (!currentPath) {
			return;
		}
		setSearchQuery("");
		setIsSearchFocused(false);
	}, [currentPath]);

	const selectedEntry = filteredEntries[selectedIndex];

	const submitZip = useCallback(
		async (zipPath: string) => {
			if (isSubmitting) {
				return;
			}

			setIsSubmitting(true);
			setErrorMessage(null);
			try {
				const intake = await api.createPipelineIntake(zipPath);
				onIntakeCreated(zipPath, intake);
			} catch (error) {
				setErrorMessage(toErrorMessage(error));
			} finally {
				setIsSubmitting(false);
			}
		},
		[isSubmitting, onIntakeCreated],
	);

	const handleSelect = useCallback(() => {
		if (!selectedEntry || isSubmitting) {
			return;
		}

		if ("isParent" in selectedEntry && selectedEntry.isParent) {
			setCurrentPath(dirname(currentPath));
			return;
		}

		if ("type" in selectedEntry && selectedEntry.type === "zip") {
			void submitZip(selectedEntry.fullPath);
			return;
		}

		if ("zipCount" in selectedEntry) {
			setCurrentPath(selectedEntry.fullPath);
		}
	}, [currentPath, isSubmitting, selectedEntry, submitZip]);

	useKeyboard((key) => {
		if (
			key.name === "backspace" &&
			currentPath !== rootPath &&
			!isSearchFocused
		) {
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
			return;
		}

		if (key.name === "escape" && !isSearchFocused && !isSubmitting) {
			onBack();
			return;
		}

		if ((key.name === "return" || key.name === "enter") && isSearchFocused) {
			setIsSearchFocused(false);
		}

		if (key.name === "r" && key.ctrl) {
			void doScan();
		}
	});

	const breadcrumbs = pathToBreadcrumbs(currentPath);
	const breadcrumbItems = useMemo(() => {
		const counts = new Map<string, number>();
		let position = 0;
		return breadcrumbs.map((crumb) => {
			position += 1;
			const nextCount = (counts.get(crumb) || 0) + 1;
			counts.set(crumb, nextCount);
			return {
				crumb,
				isLast: position === breadcrumbs.length,
				key: `${crumb}-${nextCount}`,
			};
		});
	}, [breadcrumbs]);

	const getEntryDisplay = (
		entry: SearchableEntry,
	): { icon: string; name: string; description: string } => {
		if ("isParent" in entry && entry.isParent) {
			return { icon: "", name: "..", description: "Parent directory" };
		}

		if ("type" in entry && entry.type === "zip") {
			const sizeStr = entry.size !== undefined ? formatSize(entry.size) : "";
			return { icon: "", name: entry.name, description: sizeStr };
		}

		const dirEntry = entry as DirEntry;
		const zipLabel =
			dirEntry.zipCount === 1 ? "1 ZIP" : `${dirEntry.zipCount} ZIPs`;
		return { icon: "", name: dirEntry.name, description: zipLabel };
	};

	const getScanStatusText = (): string => {
		if (isSubmitting) {
			return "Preparing intake...";
		}
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
				title="Choose Intake ZIP"
				description="Select exactly one ZIP to start a local pipeline run"
			/>

			<box flexGrow={1} flexDirection="column" padding={1}>
				<box
					flexGrow={1}
					border
					borderStyle="rounded"
					borderColor={theme.gold}
					flexDirection="column"
				>
					<box
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
						flexDirection="column"
						gap={1}
					>
						<box flexDirection="row" justifyContent="space-between">
							<text>
								<span fg={theme.textDim}>Root: {rootPath}</span>
							</text>
							<text>
								<span fg={isSubmitting ? theme.warning : theme.success}>
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
								<span fg={isSearchFocused ? theme.cyan : theme.textDim}>◉</span>
							</text>
							<input
								value={searchQuery}
								onChange={setSearchQuery}
								placeholder="Search ZIP files"
								focused={isSearchFocused}
								width={58}
							/>
							{searchQuery ? (
								<text>
									<span fg={theme.cyan}>
										{getMatchCount(filteredEntries)} matches
									</span>
								</text>
							) : null}
						</box>

						{errorMessage ? (
							<text>
								<span fg={theme.error}>{errorMessage}</span>
							</text>
						) : null}
					</box>

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
										{searchQuery
											? "No matches found"
											: "No ZIP files in this location"}
									</span>
								</text>
							</box>
						) : (
							<select
								options={filteredEntries.map((entry) => {
									const display = getEntryDisplay(entry);
									return {
										name: display.icon
											? `${display.icon} ${display.name}`
											: display.name,
										description: display.description,
										value: entry.fullPath || entry.name,
									};
								})}
								onChange={(index) => setSelectedIndex(index)}
								onSelect={handleSelect}
								selectedIndex={selectedIndex}
								focused={!isSearchFocused && !isSubmitting}
								height={16}
								showScrollIndicator
								itemSpacing={1}
							/>
						)}
					</box>

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
							{breadcrumbItems.map((crumb) => (
								<span
									key={crumb.key}
									fg={crumb.isLast ? theme.cyan : theme.textSecondary}
								>
									{crumb.crumb === "/" ? "~" : crumb.crumb}
									{!crumb.isLast ? <span fg={theme.textDim}> / </span> : null}
								</span>
							))}
						</text>

						{textHint(selectedEntry)}
					</box>
				</box>
			</box>
		</box>
	);
}

function textHint(selectedEntry: SearchableEntry | undefined) {
	if (!selectedEntry) {
		return null;
	}

	if ("type" in selectedEntry && selectedEntry.type === "zip") {
		return (
			<text>
				<span fg={theme.success}>Enter Select ZIP</span>
			</text>
		);
	}

	if (
		"zipCount" in selectedEntry &&
		!("isParent" in selectedEntry && selectedEntry.isParent)
	) {
		return (
			<text>
				<span fg={theme.textDim}>Enter Open folder</span>
			</text>
		);
	}

	return null;
}
