/**
 * Unified Snake game + progress screen for both Cloud and Local LLM flows.
 *
 * Snake on the left, humanized activity sidebar on the right.
 *
 * - Cloud mode: uploads zip, extracts, runs generateResume() streaming events
 * - Local mode: starts the local pipeline, polls for status, translates messages
 */
import { mkdir, readFile, rm, symlink } from "node:fs/promises";
import { basename, join } from "node:path";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useKeyboard, useTerminalDimensions } from "@opentui/react";
import { generateResume, type ResumeEvent } from "../../agent";
import { api } from "../../api/endpoints";
import type {
	DeveloperProfile,
	PipelineStage,
	PipelineStatusResponse,
	ResumeV3Output,
} from "../../api/types";
import { theme } from "../../types";
import { toErrorMessage } from "../../utils";
import { useToast } from "../Toast";
import { TopBar } from "../TopBar";
import { SnakeGame } from "./SnakeGame";
import {
	humanizeToolCall,
	inferPhase,
	PHASE_LABELS,
	type Phase as HumanPhase,
} from "./humanize";

// ── Shared Types ─────────────────────────────────────────────────────────────

interface GitIdentity {
	login: string;
	name: string | null;
	email: string;
}

interface ActivityEntry {
	tool: string;
	detail: string;
	status: "done" | "active";
}

type FlowPhase = "extracting" | "generating" | "done" | "error";

// Limit activity entries to prevent TUI rendering issues with large lists
const MAX_ACTIVITY = 25;

const glowColors = [
	"#8B7500",
	"#B8960B",
	"#DAB520",
	"#FFD700",
	"#FFED66",
	"#FFD700",
	"#DAB520",
	"#B8960B",
];

// ── Local Pipeline Humanization ──────────────────────────────────────────────

const STEP_MAP: Array<[string, string]> = [
	["Extracting README", "Reading project documentation"],
	["Classifying commits", "Analyzing commit history"],
	["Extracting structure", "Mapping project structure"],
	["Extracting code constructs", "Scanning code constructs"],
	["Inferring project type", "Detecting project type"],
	["Extracting git stats", "Gathering git statistics"],
	["Computing test ratio", "Measuring test coverage"],
	["Scoring commit quality", "Scoring commit quality"],
	["Measuring module breadth", "Measuring module breadth"],
	["Computing style metrics", "Analyzing code style"],
	["Computing complexity metrics", "Measuring code complexity"],
	["Computing skill timeline", "Building skill timeline"],
	["Extracting enriched constructs", "Deep code analysis"],
	["Analyzing import graph", "Mapping dependencies"],
	["Extracting config fingerprint", "Reading project configuration"],
	["Inferring project purpose", "AI: Inferring project purpose"],
	["Running project query for", "AI: Writing project description"],
	["Running project query", "AI: Writing project bullets"],
	["Running portfolio query for summary", "AI: Writing professional summary"],
	["Running portfolio query for developer", "AI: Writing developer profile"],
	["Running portfolio query", "AI: Composing portfolio summary"],
	["Writing grounded draft", "AI: Drafting your resume"],
	["Assembling resume", "Assembling resume document"],
];

const NOISE_PREFIXES = [
	"Pipeline request",
	"Phase 1 worker",
	"Pipeline started",
	"Phase 3 worker",
	"Phase 3 started",
	"Checking model",
	"Found ",
	"Analyzing [",
];

function toFriendlyStep(msg: string): string | null {
	for (const [prefix, friendly] of STEP_MAP) {
		if (msg.startsWith(prefix)) return friendly;
	}
	for (const noise of NOISE_PREFIXES) {
		if (msg.startsWith(noise)) return null;
	}
	const trimmed = msg.replace(/\.{2,}$/, "").trim();
	return trimmed.length > 0 ? trimmed : null;
}

const LOCAL_STAGE_LABELS: Record<PipelineStage, string> = {
	ANALYZE: "Reading your repositories",
	FACTS: "Compiling facts & evidence",
	DRAFT: "Writing your resume",
	POLISH: "Polishing with your feedback",
};

const DEFAULT_STAGE1_MODEL = "qwen3.5-2b-q4";
const DEFAULT_STAGE2_MODEL = "qwen3.5-2b-q4";
const DEFAULT_STAGE3_MODEL = "qwen3.5-2b-q4";

// ── Cloud Mode Props ─────────────────────────────────────────────────────────

interface CloudModeProps {
	mode: "cloud";
	zipPath: string;
	modelId: string;
	gitIdentity: GitIdentity | null;
	selectedRepoPaths: string[];
	onComplete: (result: {
		profile: DeveloperProfile;
		portfolioId: string;
		zipId: number;
	}) => void;
	onBack: () => void;
}

// ── Local Mode Props ─────────────────────────────────────────────────────────

interface LocalModeProps {
	mode: "local";
	intakeId: string;
	repoIds: string[];
	userEmail: string;
	onDraftReady: (draft: ResumeV3Output) => void;
	onComplete: (output: ResumeV3Output) => void;
	onBack: () => void;
}

type SnakeWithProgressProps = CloudModeProps | LocalModeProps;

// ── Component ────────────────────────────────────────────────────────────────

export function SnakeWithProgress(props: SnakeWithProgressProps) {
	const { width: termW, height: termH } = useTerminalDimensions();
	const toast = useToast();

	const [flowPhase, setFlowPhase] = useState<FlowPhase>("extracting");
	const [activity, setActivity] = useState<ActivityEntry[]>([]);
	const [totalActivityCount, setTotalActivityCount] = useState(0);
	const [showSnake, setShowSnake] = useState(false);
	const [isStreamingText, setIsStreamingText] = useState(false);
	const [glowIndex, setGlowIndex] = useState(0);
	const [isCancelling, setIsCancelling] = useState(false);

	// Cloud-specific refs
	const cloudResultRef = useRef<DeveloperProfile | null>(null);
	const cloudPortfolioIdRef = useRef<string | null>(null);
	const cloudZipIdRef = useRef<number | null>(null);
	const phaseRef = useRef(flowPhase);
	phaseRef.current = flowPhase;

	// Local-specific state
	const [localStage, setLocalStage] = useState<PipelineStage | null>(null);
	const localDraftRef = useRef<ResumeV3Output | null>(null);
	const localOutputRef = useRef<ResumeV3Output | null>(null);
	const handledStatusRef = useRef<string | null>(null);

	// Glow animation
	useEffect(() => {
		if (flowPhase === "done" || flowPhase === "error") return;
		const interval = setInterval(() => {
			setGlowIndex((i) => (i + 1) % glowColors.length);
		}, 250);
		return () => clearInterval(interval);
	}, [flowPhase]);

	// Toast on done
	useEffect(() => {
		if (flowPhase === "done") {
			toast.show({
				title: "Resume Ready!",
				message: "Press Enter to view your resume",
				variant: "success",
				duration: 10000,
			});
		}
	}, [flowPhase]);

	function pushActivity(
		tool: string,
		detail: string,
		status: "done" | "active" = "active",
	) {
		setTotalActivityCount((c) => c + 1);
		setActivity((prev) => {
			const updated = prev.map((e) =>
				e.status === "active" ? { ...e, status: "done" as const } : e,
			);
			return [...updated, { tool, detail, status }].slice(-MAX_ACTIVITY);
		});
	}

	// ── Infer human phase ──
	const humanPhase: HumanPhase = useMemo(() => {
		if (flowPhase === "done") return "done";

		if (props.mode === "local") {
			if (!localStage || localStage === "ANALYZE") return "exploring";
			if (localStage === "FACTS") return "analyzing";
			return "writing";
		}

		// Cloud
		if (flowPhase === "extracting") return "exploring";
		return inferPhase(activity, isStreamingText);
	}, [flowPhase, activity, isStreamingText, props.mode, localStage]);

	// ── Local phase label override ──
	const statusLabel = useMemo(() => {
		if (flowPhase === "done") return "All done!";
		if (props.mode === "local" && localStage) {
			return LOCAL_STAGE_LABELS[localStage] ?? PHASE_LABELS[humanPhase];
		}
		return PHASE_LABELS[humanPhase];
	}, [flowPhase, humanPhase, props.mode, localStage]);

	// ═══════════════════════════════════════════════════════════════════════════
	// CLOUD MODE — upload + generateResume streaming
	// ═══════════════════════════════════════════════════════════════════════════

	useEffect(() => {
		if (props.mode !== "cloud") return;

		let cancelled = false;
		const abortController = new AbortController();

		const onEvent = (event: ResumeEvent) => {
			if (cancelled) return;
			switch (event.type) {
				case "text":
					if (!isStreamingText) setIsStreamingText(true);
					break;
				case "tool_start": {
					const detail = humanizeToolCall(event.toolName, event.args);
					pushActivity(event.toolName, detail);
					break;
				}
				case "tool_end":
					setActivity((prev) =>
						prev.map((e) =>
							e.status === "active" ? { ...e, status: "done" as const } : e,
						),
					);
					break;
				case "agent_end":
					pushActivity("system", "Your developer profile is ready!", "done");
					setFlowPhase("done");
					break;
				case "error":
					setFlowPhase("error");
					toast.show({ variant: "error", message: event.message, duration: 0 });
					break;
			}
		};

		let filteredDir: string | null = null;

		(async () => {
			try {
				setFlowPhase("extracting");
				pushActivity("system", "Reading archive...");
				const archiveBuffer = await readFile(props.zipPath);
				if (cancelled) return;

				const sizeMb = (archiveBuffer.length / (1024 * 1024)).toFixed(1);
				pushActivity("system", `Archive loaded (${sizeMb} MB)`, "done");
				pushActivity("system", "Uploading to server...");

				// Convert Buffer to Uint8Array for Blob compatibility
				const zipFilename = basename(props.zipPath);
				const uint8Array = new Uint8Array(archiveBuffer);
				const upload = await api.uploadZip(
					new Blob([uint8Array], { type: "application/zip" }),
					undefined,
					zipFilename,
				);
				cloudPortfolioIdRef.current = upload.portfolio_id;
				cloudZipIdRef.current = upload.zip_id;
				if (cancelled) return;
				pushActivity("system", "Archive uploaded.", "done");
				pushActivity("system", "Unpacking your projects...");
				const { extraction_path } = await api.extractLocal(upload.zip_id);
				if (cancelled) return;
				pushActivity("system", "Found your projects!", "done");

				// Hard isolation: create a temp directory with symlinks
				// to only the user-selected repos so the agent cannot
				// see unselected repositories.
				let agentCwd = extraction_path;
				const hasRootRepo = props.selectedRepoPaths.includes(".");
				if (props.selectedRepoPaths.length > 0 && !hasRootRepo) {
					pushActivity("system", "Preparing selected projects...");
					filteredDir = mkdtempSync(join(tmpdir(), "am-cloud-"));
					for (const relPath of props.selectedRepoPaths) {
						const src = join(extraction_path, relPath);
						const dest = join(filteredDir, relPath);
						// Support nested rel_paths (e.g. "subdir/project")
						const parentParts = relPath.split("/").slice(0, -1);
						if (parentParts.length > 0) {
							await mkdir(join(filteredDir, ...parentParts), {
								recursive: true,
							});
						}
						await symlink(src, dest, "dir");
					}
					agentCwd = filteredDir;
					pushActivity(
						"system",
						`Scoped to ${props.selectedRepoPaths.length} selected project${props.selectedRepoPaths.length === 1 ? "" : "s"}.`,
						"done",
					);
				}

				setFlowPhase("generating");
				pushActivity("system", "Getting the AI started...");
				const profile = await generateResume(
					agentCwd,
					onEvent,
					props.modelId,
					props.gitIdentity ?? undefined,
					{ signal: abortController.signal },
				);
				cloudResultRef.current = profile;
			} catch (err) {
				if (cancelled) return;
				if (err instanceof Error && err.name === "AbortError") return;
				setFlowPhase("error");
				const msg = err instanceof Error ? err.message : String(err);
				const isConnErr =
					msg.includes("Unable to connect") ||
					msg.includes("ECONNREFUSED") ||
					msg.includes("fetch failed");
				toast.show({
					variant: "error",
					title: isConnErr ? "Backend Offline" : "Generation Failed",
					message: isConnErr
						? "Start the backend: uv run uvicorn artifactminer.api.app:app"
						: msg,
					duration: 0,
				});
			} finally {
				// Clean up the filtered symlink directory
				if (filteredDir) {
					rm(filteredDir, { recursive: true, force: true }).catch(() => {});
				}
			}
		})();

		return () => {
			cancelled = true;
			abortController.abort();
			// Also clean up on unmount if still around
			if (filteredDir) {
				rm(filteredDir, { recursive: true, force: true }).catch(() => {});
			}
		};
	}, [
		props.mode === "cloud" ? props.gitIdentity : null,
		props.mode === "cloud" ? props.modelId : null,
		props.mode === "cloud" ? props.zipPath : null,
		props.mode === "cloud" ? props.selectedRepoPaths : null,
		props.mode,
	]);

	// ═══════════════════════════════════════════════════════════════════════════
	// LOCAL MODE — start pipeline + poll for status
	// ═══════════════════════════════════════════════════════════════════════════

	useEffect(() => {
		if (props.mode !== "local") return;

		let disposed = false;
		let pollInterval: ReturnType<typeof setInterval> | null = null;

		const stopPolling = () => {
			if (pollInterval) {
				clearInterval(pollInterval);
				pollInterval = null;
			}
		};

		// Track message indexes we've already converted to activity entries
		let lastMessageIndex = 0;

		const processMessages = (messages: string[]) => {
			const newMessages = messages.slice(lastMessageIndex);
			lastMessageIndex = messages.length;

			for (const msg of newMessages) {
				const friendly = toFriendlyStep(msg);
				if (friendly) {
					pushActivity("local", friendly);
				}
			}
		};

		const pollStatus = async () => {
			try {
				const response: PipelineStatusResponse = await api.getPipelineStatus();
				if (disposed) return;

				setLocalStage(response.stage);
				processMessages(response.messages);

				// Store refs for completion handlers
				if (response.draft) localDraftRef.current = response.draft;
				if (response.output) localOutputRef.current = response.output;

				if (
					response.status === "complete" &&
					handledStatusRef.current !== "complete"
				) {
					stopPolling();
					handledStatusRef.current = "complete";
					pushActivity("system", "Your resume is ready!", "done");
					setFlowPhase("done");
					return;
				}

				if (
					response.status === "draft_ready" &&
					handledStatusRef.current !== "draft_ready"
				) {
					stopPolling();
					handledStatusRef.current = "draft_ready";
					pushActivity("system", "Draft complete — review & refine", "done");
					setFlowPhase("done");
					return;
				}

				if (
					response.status === "error" ||
					response.status === "cancelled" ||
					response.status === "failed_resource_guard"
				) {
					stopPolling();
					setFlowPhase("error");
					const msg =
						response.error ||
						(response.status === "cancelled"
							? "Pipeline cancelled."
							: response.status === "failed_resource_guard"
								? "Pipeline stopped: resource limits reached."
								: "Pipeline failed.");
					toast.show({
						variant: response.status === "cancelled" ? "warning" : "error",
						title:
							response.status === "cancelled" ? "Cancelled" : "Pipeline Error",
						message: msg,
						duration: 0,
					});
					return;
				}
			} catch (pollError) {
				if (!disposed) {
					toast.show({
						variant: "warning",
						title: "Poll Error",
						message: toErrorMessage(pollError),
					});
				}
			}
		};

		// Start the pipeline
		(async () => {
			try {
				setFlowPhase("extracting");
				pushActivity("system", "Starting local AI pipeline...");

				const response = await api.startPipeline({
					intake_id: props.intakeId,
					repo_ids: props.repoIds,
					user_email: props.userEmail,
					stage1_model: DEFAULT_STAGE1_MODEL,
					stage2_model: DEFAULT_STAGE2_MODEL,
					stage3_model: DEFAULT_STAGE3_MODEL,
				});

				if (disposed) return;
				pushActivity("system", "Pipeline started!", "done");
				setFlowPhase("generating");

				// Begin polling
				pollInterval = setInterval(() => {
					void pollStatus();
				}, 2000);
				void pollStatus();
			} catch (startErr) {
				if (disposed) return;
				setFlowPhase("error");
				const msg =
					startErr instanceof Error ? startErr.message : String(startErr);
				const isConnErr =
					msg.includes("Unable to connect") ||
					msg.includes("ECONNREFUSED") ||
					msg.includes("fetch failed");
				toast.show({
					variant: "error",
					title: isConnErr ? "Backend Offline" : "Pipeline Failed to Start",
					message: isConnErr
						? "Start the backend: uv run uvicorn artifactminer.api.app:app"
						: msg,
					duration: 0,
				});
			}
		})();

		return () => {
			disposed = true;
			stopPolling();
		};
	}, [
		props.mode === "local" ? props.intakeId : null,
		props.mode === "local" ? props.repoIds : null,
		props.mode === "local" ? props.userEmail : null,
		props.mode,
	]);

	// ═══════════════════════════════════════════════════════════════════════════
	// Cancel (local only)
	// ═══════════════════════════════════════════════════════════════════════════

	const cancelLocalPipeline = async () => {
		if (props.mode !== "local" || isCancelling) return;
		setIsCancelling(true);
		toast.show({
			variant: "info",
			message: "Cancelling pipeline...",
			duration: 3000,
		});
		try {
			const response = await api.cancelPipeline();
			if (response.ok && response.status === "cancelled") {
				setFlowPhase("error");
				toast.show({
					variant: "warning",
					title: "Cancelled",
					message: "Pipeline was cancelled.",
					duration: 0,
				});
			}
		} catch (cancelError) {
			toast.show({ variant: "error", message: toErrorMessage(cancelError) });
		} finally {
			setIsCancelling(false);
		}
	};

	// ═══════════════════════════════════════════════════════════════════════════
	// Keyboard
	// ═══════════════════════════════════════════════════════════════════════════

	useKeyboard(
		useCallback(
			(key: { name: string }) => {
				if (key.name === "escape") {
					if (showSnake) {
						setShowSnake(false);
						return;
					}
					if (
						props.mode === "local" &&
						flowPhase !== "done" &&
						flowPhase !== "error"
					) {
						void cancelLocalPipeline();
						return;
					}
					props.onBack();
					return;
				}

				if (phaseRef.current === "done" && key.name === "return") {
					if (
						props.mode === "cloud" &&
						cloudResultRef.current &&
						cloudPortfolioIdRef.current &&
						cloudZipIdRef.current !== null
					) {
						props.onComplete({
							profile: cloudResultRef.current,
							portfolioId: cloudPortfolioIdRef.current,
							zipId: cloudZipIdRef.current,
						});
					} else if (props.mode === "local") {
						if (
							handledStatusRef.current === "draft_ready" &&
							localDraftRef.current
						) {
							(props as LocalModeProps).onDraftReady(localDraftRef.current);
						} else if (localOutputRef.current) {
							(props as LocalModeProps).onComplete(localOutputRef.current);
						}
					}
					return;
				}

				if (!showSnake && (key.name === "s" || key.name === "p")) {
					setShowSnake(true);
				}
			},
			[showSnake, props.onBack, flowPhase, props.mode],
		),
	);

	// ═══════════════════════════════════════════════════════════════════════════
	// Layout
	// ═══════════════════════════════════════════════════════════════════════════

	const halfW = Math.floor(termW / 2);
	const snakeW = Math.max(6, Math.floor((halfW - 4) / 4));
	const snakeH = Math.max(4, Math.floor((termH - 14) / 2));
	const isActive = flowPhase !== "done" && flowPhase !== "error";

	const description =
		props.mode === "cloud"
			? "An AI agent is exploring your code repositories, analyzing your skills, and crafting a professional resume. This may take a minute or two depending on the size of your projects."
			: "Your local AI is analyzing repositories, extracting facts, and writing your resume. This runs entirely on your machine.";

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title={
					props.mode === "cloud" ? "AI Resume Generation" : "Local AI Analysis"
				}
				description={description}
			/>

			<box flexGrow={1} flexDirection="row">
				{/* Left: Snake game panel */}
				<box flexGrow={1} flexBasis={0} flexDirection="column">
					{showSnake ? (
						<SnakeGame width={snakeW} height={snakeH} />
					) : (
						<box
							flexGrow={1}
							flexDirection="column"
							border
							borderStyle="rounded"
							borderColor={theme.goldDim}
							onMouseDown={() => setShowSnake(true)}
						>
							{Array.from({ length: snakeH * 2 }, (_, i) => (
								<text key={i}>
									<span fg="#222222">
										{(i % 2 === 0 ? " ·" : "  ")
											.repeat(snakeW)
											.slice(0, snakeW * 4)}
									</span>
								</text>
							))}
							<box
								position="absolute"
								top={0}
								left={0}
								right={0}
								bottom={0}
								alignItems="center"
								justifyContent="center"
								flexDirection="column"
								gap={1}
							>
								<ascii-font text="SNAKE" font="tiny" color={theme.goldDim} />
								<box
									border
									borderStyle="rounded"
									borderColor={theme.gold}
									paddingLeft={3}
									paddingRight={3}
									paddingTop={1}
									paddingBottom={1}
									onMouseDown={() => setShowSnake(true)}
								>
									<text>
										<span fg={theme.gold}>
											<strong>LET'S PLAY!</strong>
										</span>
									</text>
								</box>
								<text>
									<span fg={theme.textDim}>
										Play while your resume generates
									</span>
								</text>
							</box>
						</box>
					)}
				</box>

				{/* Right: Activity sidebar - enclosed in bordered panel like snake */}
				<box flexGrow={1} flexBasis={0} flexDirection="column" paddingLeft={1}>
					<box
						flexGrow={1}
						flexDirection="column"
						border
						borderStyle="rounded"
						borderColor={theme.goldDim}
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						overflow="hidden"
					>
						{/* Layer 1: Glowing status label */}
						<box flexDirection="column" marginBottom={1}>
							{flowPhase === "done" ? (
								<text>
									<span fg={theme.success}>
										<strong>✓ Complete</strong>
									</span>
									<span fg={theme.textDim}>{" - press Enter to view"}</span>
								</text>
							) : (
								<text>
									<span fg={isActive ? glowColors[glowIndex] : theme.gold}>
										<strong>{statusLabel}</strong>
									</span>
								</text>
							)}
						</box>

						{/* Gold divider */}
						<box marginBottom={1}>
							<text>
								<span fg={theme.goldDim}>
									{"─".repeat(Math.max(1, halfW - 8))}
								</span>
							</text>
						</box>

						{/* Show truncation indicator if there are hidden items */}
						{totalActivityCount > MAX_ACTIVITY && (
							<box marginBottom={1}>
								<text>
									<span fg={theme.textDim}>
										... and {totalActivityCount - MAX_ACTIVITY} earlier
									</span>
								</text>
							</box>
						)}

						{/* Layer 2: Activity log (no scrollbox - fixed height) */}
						<box flexGrow={1} flexShrink={1} overflow="hidden">
							{activity.map((entry, i) => {
								const maxLen = Math.max(10, halfW - 12);
								const text =
									entry.detail.length > maxLen
										? `${entry.detail.slice(0, maxLen - 3)}...`
										: entry.detail;
								return (
									<box key={i} flexDirection="row" gap={1}>
										<text>
											{entry.status === "done" ? (
												<span fg={theme.success}>✓</span>
											) : (
												<span fg={theme.cyan}>●</span>
											)}
										</text>
										<text>
											<span
												fg={
													entry.status === "active"
														? theme.textPrimary
														: theme.textDim
												}
											>
												{text}
											</span>
										</text>
									</box>
								);
							})}
						</box>
					</box>
				</box>
			</box>
		</box>
	);
}
