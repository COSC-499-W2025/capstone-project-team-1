// ZIP Scanner
export {
	scanForZips,
	buildDirsWithZips,
	getZipsInDir,
	getChildDirsWithZips,
	buildEntries,
	DEFAULT_EXCLUDE_DIRS,
	type ZipFile,
	type DirEntry,
	type ScanOptions,
	type ScanResult,
} from "./zipScanner";

// Search & Filter
export {
	createSearchIndex,
	filterEntries,
	getMatchCount,
	type SearchableEntry,
	type SearchOptions,
} from "./searchFilter";

// Path Helpers
export {
	pathToBreadcrumbs,
	formatSize,
	shortenPath,
	getParentPath,
	isAtOrAboveRoot,
} from "./pathHelpers";

// API / parsing helpers
export { toErrorMessage } from "./errorMessage";

// Resume preview rendering
export {
	resumeToLines,
	resumeToText,
	resumeToSections,
	resumeStats,
	createUnifiedDiff,
	buildLineDiff,
	keyedLines,
	type DiffRow,
	type ResumeSection,
	type StatLine,
} from "./resumeText";
