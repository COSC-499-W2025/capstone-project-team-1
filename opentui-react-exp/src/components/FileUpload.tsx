import { useKeyboard } from "@opentui/react";
import { homedir } from "node:os";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { theme } from "../types";
import { TopBar } from "./TopBar";
import {
    scanForZips,
    buildEntries,
    formatSize,
    type ZipFile,
    type DirEntry,
    type SearchableEntry,
} from "../utils";

interface FileUploadProps {
    onSubmit: (path: string) => void;
    onBack: () => void;
    scanRoot?: string;
}

type ScanStatus = "idle" | "scanning" | "complete" | "error";

interface Column {
    path: string;
    selectedIndex: number;
}

const MAX_VISIBLE_COLUMNS = 4;

export function FileUpload({ onSubmit, onBack, scanRoot }: FileUploadProps) {
    const rootPath = scanRoot || homedir();

    // Global ZIP scan state
    const [allZips, setAllZips] = useState<ZipFile[]>([]);
    const [scanStatus, setScanStatus] = useState<ScanStatus>("idle");
    const scanAbortRef = useRef<boolean>(false);

    // Miller columns state
    const [columns, setColumns] = useState<Column[]>([
        { path: rootPath, selectedIndex: 0 },
    ]);
    const [activeColumnIndex, setActiveColumnIndex] = useState(0);

    // Search state
    const [searchQuery, setSearchQuery] = useState("");
    const [isSearchFocused, setIsSearchFocused] = useState(false);

    // Scanning progress animation
    const [scanProgress, setScanProgress] = useState(0);
    useEffect(() => {
        if (scanStatus !== "scanning") return;
        const interval = setInterval(() => {
            setScanProgress((p) => (p + 1) % 30);
        }, 80);
        return () => clearInterval(interval);
    }, [scanStatus]);

    const doScan = useCallback(async () => {
        setScanStatus("scanning");
        setAllZips([]);
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

    useEffect(() => {
        doScan();
        return () => {
            scanAbortRef.current = true;
        };
    }, [doScan]);

    // Build entries for a given column path
    const getColumnEntries = useCallback(
        (path: string) => {
            return buildEntries(allZips, path, rootPath);
        },
        [allZips, rootPath],
    );

    // Get entries for all visible columns
    const visibleColumns = columns.slice(-MAX_VISIBLE_COLUMNS);
    const visibleStartIndex = Math.max(0, columns.length - MAX_VISIBLE_COLUMNS);

    const columnEntries = useMemo(() => {
        return visibleColumns.map((col) => getColumnEntries(col.path));
    }, [visibleColumns, getColumnEntries]);

    const getEntryDisplay = (
        entry: SearchableEntry,
    ): { icon: string; name: string; detail: string; isDir: boolean } => {
        if ("isParent" in entry && entry.isParent) {
            return { icon: "‹", name: "..", detail: "", isDir: true };
        }
        if ("type" in entry && entry.type === "zip") {
            const sizeStr =
                entry.size !== undefined ? formatSize(entry.size) : "";
            return {
                icon: "📦",
                name: entry.name,
                detail: sizeStr,
                isDir: false,
            };
        }
        const dir = entry as DirEntry;
        const label = dir.zipCount === 1 ? "1 ZIP" : `${dir.zipCount} ZIPs`;
        return { icon: "📁", name: dir.name, detail: label, isDir: true };
    };

    const handleItemClick = (colIdx: number, entryIdx: number) => {
        const realColIdx = visibleStartIndex + colIdx;
        const entries = columnEntries[colIdx];
        const entry = entries[entryIdx];
        if (!entry) return;

        // Update selection in the clicked column
        const newColumns = columns.slice(0, realColIdx + 1);
        newColumns[realColIdx] = {
            ...newColumns[realColIdx],
            selectedIndex: entryIdx,
        };

        if ("isParent" in entry && entry.isParent) {
            // Go up: remove this column, go back
            newColumns.pop();
            setColumns(newColumns);
            setActiveColumnIndex(Math.max(0, newColumns.length - 1));
            return;
        }

        if ("type" in entry && entry.type === "zip") {
            setColumns(newColumns);
            setActiveColumnIndex(realColIdx);
            onSubmit(entry.fullPath);
            return;
        }

        if ("zipCount" in entry) {
            // Open folder in next column
            newColumns.push({ path: entry.fullPath, selectedIndex: 0 });
            setColumns(newColumns);
            setActiveColumnIndex(newColumns.length - 1);
        }
    };

    // Search results: flat list of matching ZIPs
    const searchResults = useMemo(() => {
        if (!searchQuery) return [];
        const q = searchQuery.toLowerCase();
        return allZips.filter((z) => z.name.toLowerCase().includes(q));
    }, [allZips, searchQuery]);

    const [searchSelectedIndex, setSearchSelectedIndex] = useState(0);
    useEffect(() => {
        setSearchSelectedIndex(0);
    }, [searchQuery]);

    // Keyboard navigation
    useKeyboard((key) => {
        // Search focus toggle
        if (key.sequence === "/" && !isSearchFocused) {
            setIsSearchFocused(true);
            return;
        }
        if (key.name === "escape" && isSearchFocused) {
            if (searchQuery) {
                setSearchQuery("");
            } else {
                setIsSearchFocused(false);
            }
            return;
        }
        if (isSearchFocused) {
            // Only intercept Escape — let the input handle everything else
            return;
        }

        // Column navigation
        const realActiveIdx = activeColumnIndex;
        const col = columns[realActiveIdx];
        if (!col) return;

        const visColIdx = realActiveIdx - visibleStartIndex;
        const entries =
            visColIdx >= 0 && visColIdx < columnEntries.length
                ? columnEntries[visColIdx]
                : [];

        if (key.name === "up" || key.name === "k") {
            const newIdx = Math.max(0, col.selectedIndex - 1);
            const newCols = [...columns];
            newCols[realActiveIdx] = { ...col, selectedIndex: newIdx };
            setColumns(newCols);
        }
        if (key.name === "down" || key.name === "j") {
            const newIdx = Math.min(entries.length - 1, col.selectedIndex + 1);
            const newCols = [...columns];
            newCols[realActiveIdx] = { ...col, selectedIndex: newIdx };
            setColumns(newCols);
        }
        if (key.name === "return" || key.name === "right" || key.name === "l") {
            handleItemClick(visColIdx, col.selectedIndex);
        }
        if (
            key.name === "left" ||
            key.name === "h" ||
            key.name === "backspace"
        ) {
            if (activeColumnIndex > 0) {
                setActiveColumnIndex(activeColumnIndex - 1);
                setColumns(columns.slice(0, activeColumnIndex + 1));
            }
        }
        if (key.name === "escape") {
            onBack();
        }
    });

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
            <TopBar title="Upload" />

            {/* Header area — description, search, breadcrumbs */}
            <box
                flexDirection="column"
                paddingLeft={2}
                paddingRight={2}
                gap={1}
                paddingBottom={1}
            >
                <text>
                    <span fg={theme.textSecondary}>
                        {
                            "Select a ZIP file containing your project repositories."
                        }
                    </span>
                </text>

                 {/* Search bar — hidden during scan */}
                 {scanStatus !== "scanning" ? (
                     <box
                         borderBottom
                         borderTop={false}
                         borderLeft={false}
                         borderRight={false}
                         borderColor={isSearchFocused ? theme.cyan : theme.bgLight}
                         paddingLeft={1}
                         paddingBottom={1}
                         flexDirection="row"
                         alignItems="center"
                         gap={1}
                         onMouseDown={() => setIsSearchFocused(true)}
                     >
                         <text>
                             <span fg={isSearchFocused ? theme.cyan : theme.textDim}>
                                 {"🔍"}
                             </span>
                         </text>
                        <input
                            value={searchQuery}
                            onChange={setSearchQuery}
                            placeholder="Search for ZIP files..."
                            focused={isSearchFocused}
                            backgroundColor={theme.bgDark}
                            focusedBackgroundColor={theme.bgDark}
                            textColor={theme.textPrimary}
                            focusedTextColor={theme.textPrimary}
                            cursorColor={theme.cyan}
                            placeholderColor={theme.textDim}
                            flexGrow={1}
                        />
                        {searchQuery ? (
                            <text>
                                <span fg={theme.cyan}>
                                    {searchResults.length} matches
                                </span>
                            </text>
                        ) : scanStatus === "complete" ? (
                            <text>
                                <span fg={theme.success}>
                                    {allZips.length} ZIPs found
                                </span>
                            </text>
                        ) : null}
                    </box>
                ) : null}

                {/* Breadcrumbs */}
                {!searchQuery && scanStatus !== "scanning" ? (
                    <box flexDirection="row" alignItems="center">
                        {columns.map((col, i) => {
                            const name =
                                col.path === rootPath
                                    ? "~"
                                    : col.path.split("/").pop() || "/";
                            const isLast = i === columns.length - 1;
                            return (
                                <box
                                    key={col.path}
                                    flexDirection="row"
                                    onMouseDown={() => {
                                        setColumns(columns.slice(0, i + 1));
                                        setActiveColumnIndex(i);
                                    }}
                                >
                                    <text>
                                        <span
                                            fg={
                                                isLast
                                                    ? theme.gold
                                                    : theme.textDim
                                            }
                                        >
                                            {isLast ? (
                                                <strong>{name}</strong>
                                            ) : (
                                                name
                                            )}
                                        </span>
                                        {!isLast ? (
                                            <span fg={theme.textDim}>
                                                {" / "}
                                            </span>
                                        ) : null}
                                    </text>
                                </box>
                            );
                        })}
                    </box>
                ) : null}
            </box>

            {/* Scanning progress — centered overlay */}
            {scanStatus === "scanning" ? (
                <box
                    flexGrow={1}
                    flexDirection="column"
                    justifyContent="center"
                    alignItems="center"
                    gap={1}
                >
                    <text>
                        <span fg={theme.gold}>
                            <strong>Scanning your files...</strong>
                        </span>
                    </text>
                    <box width={40} flexDirection="row">
                        <text>
                            <span fg={theme.textDim}>{"["}</span>
                            <span fg={theme.gold}>
                                {"█".repeat(scanProgress)}
                                {"░".repeat(30 - scanProgress)}
                            </span>
                            <span fg={theme.textDim}>{"]"}</span>
                        </text>
                    </box>
                </box>
            ) : searchQuery ? (
                /* Search results view */
                <box flexGrow={1} flexDirection="column" padding={1}>
                    <scrollbox flexGrow={1}>
                        {searchResults.length === 0 ? (
                            <box
                                padding={2}
                                flexDirection="row"
                                justifyContent="center"
                            >
                                <text>
                                    <span fg={theme.textDim}>
                                        No ZIP files matching "{searchQuery}"
                                    </span>
                                </text>
                            </box>
                        ) : (
                            searchResults.map((zip, i) => {
                                const isSelected = i === searchSelectedIndex;
                                const bg = isSelected
                                    ? "#1a1a00"
                                    : i % 2 === 0
                                      ? theme.bgDark
                                      : "#111111";
                                const sizeStr =
                                    zip.size !== undefined
                                        ? formatSize(zip.size)
                                        : "";
                                return (
                                    <box
                                        key={zip.fullPath}
                                        backgroundColor={bg}
                                        paddingLeft={1}
                                        paddingRight={1}
                                        paddingTop={1}
                                        paddingBottom={1}
                                        onMouseDown={() =>
                                            onSubmit(zip.fullPath)
                                        }
                                    >
                                        <text>
                                            <span
                                                fg={
                                                    isSelected
                                                        ? theme.gold
                                                        : theme.textDim
                                                }
                                            >
                                                {"📦 "}
                                            </span>
                                            <span
                                                fg={
                                                    isSelected
                                                        ? theme.gold
                                                        : theme.textSecondary
                                                }
                                            >
                                                <strong>{zip.name}</strong>
                                            </span>
                                            <span fg={theme.textDim}>
                                                {"  "}
                                                {sizeStr}
                                                {"  "}
                                                {zip.fullPath}
                                            </span>
                                        </text>
                                    </box>
                                );
                            })
                        )}
                    </scrollbox>
                </box>
            ) : (
                /* Miller columns */
                <box flexGrow={1} flexDirection="row" padding={1} gap={0}>
                    {visibleColumns.map((col, colIdx) => {
                        const entries = columnEntries[colIdx] ?? [];
                        const realColIdx = visibleStartIndex + colIdx;
                        const isActive = realColIdx === activeColumnIndex;

                        return (
                            <box
                                key={col.path}
                                flexGrow={1}
                                flexDirection="column"
                                border
                                borderStyle="single"
                                borderColor={
                                    isActive ? theme.gold : theme.bgLight
                                }
                            >
                                {/* Column header */}
                                <box
                                    paddingLeft={1}
                                    paddingRight={1}
                                    backgroundColor={
                                        isActive ? theme.bgMedium : theme.bgDark
                                    }
                                >
                                    <text>
                                        <span
                                            fg={
                                                isActive
                                                    ? theme.gold
                                                    : theme.textDim
                                            }
                                        >
                                            <strong>
                                                {col.path.split("/").pop() ||
                                                    "~"}
                                            </strong>
                                        </span>
                                    </text>
                                </box>

                                {/* Column entries */}
                                <scrollbox flexGrow={1} focused={isActive}>
                                    {entries.map((entry, i) => {
                                        const display = getEntryDisplay(entry);
                                        const isSelected =
                                            i === col.selectedIndex;
                                        const bg = isSelected
                                            ? isActive
                                                ? "#1a1a00"
                                                : theme.bgMedium
                                            : i % 2 === 0
                                              ? theme.bgDark
                                              : "#111111";

                                        return (
                                            <box
                                                key={
                                                    entry.fullPath || entry.name
                                                }
                                                backgroundColor={bg}
                                                paddingLeft={1}
                                                paddingRight={1}
                                                paddingTop={1}
                                                paddingBottom={1}
                                                onMouseDown={() =>
                                                    handleItemClick(colIdx, i)
                                                }
                                            >
                                                <text>
                                                    <span
                                                        fg={
                                                            isSelected &&
                                                            isActive
                                                                ? theme.gold
                                                                : isSelected
                                                                  ? theme.textSecondary
                                                                  : theme.textDim
                                                        }
                                                    >
                                                        {display.icon}{" "}
                                                    </span>
                                                    <span
                                                        fg={
                                                            isSelected &&
                                                            isActive
                                                                ? theme.gold
                                                                : theme.textSecondary
                                                        }
                                                    >
                                                        {display.isDir ? (
                                                            display.name
                                                        ) : (
                                                            <strong>
                                                                {display.name}
                                                            </strong>
                                                        )}
                                                    </span>
                                                    {display.detail ? (
                                                        <span
                                                            fg={theme.textDim}
                                                        >
                                                            {" "}
                                                            {display.detail}
                                                        </span>
                                                    ) : null}
                                                    {display.isDir &&
                                                    !("isParent" in entry) ? (
                                                        <span
                                                            fg={theme.textDim}
                                                        >
                                                            {" ›"}
                                                        </span>
                                                    ) : null}
                                                </text>
                                            </box>
                                        );
                                    })}
                                </scrollbox>
                            </box>
                        );
                    })}
                </box>
            )}
        </box>
    );
}
