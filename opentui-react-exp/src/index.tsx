import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { api } from "./api/endpoints";
import { BottomBar } from "./components/BottomBar";
import { CloudAuth, CloudFlow } from "./components/cloud-ai";
import { SnakeWithProgress } from "./components/cloud-ai/SnakeWithProgress";
import { CloudResumePreview } from "./components/CloudResumePreview";
import { ConfigureScreen } from "./components/ConfigureScreen";
import { ConsentScreen } from "./components/ConsentScreen";
import { DraftPauseScreen } from "./components/DraftPauseScreen";
import { FileUpload } from "./components/FileUpload";
import { Landing } from "./components/Landing";
import { ResumePreview } from "./components/ResumePreview";
import { ToastProvider } from "./components/Toast";
import { AppProvider, useAppState } from "./context/AppContext";
import { useSelectionCopy } from "./hooks/useSelectionCopy";
import type { ConsentLevel, DeveloperProfile } from "./api/types";
import { type KeyAction, type Screen, theme } from "./types";
import type { Breadcrumb } from "./components/BottomBar";
import { toErrorMessage } from "./utils";

// Screens shown in breadcrumbs (in order)
const LOCAL_BREADCRUMB_SCREENS: { screen: Screen; label: string }[] = [
	{ screen: "consent", label: "Consent" },
	{ screen: "file-upload", label: "Upload" },
	{ screen: "configure", label: "Configure" },
	{ screen: "analysis", label: "Generate" },
	{ screen: "draft-pause", label: "Draft" },
	{ screen: "resume-preview", label: "Resume" },
];

const CLOUD_BREADCRUMB_SCREENS: { screen: Screen; label: string }[] = [
	{ screen: "consent", label: "Consent" },
	// cloud-auth is a transparent gate (skips if already logged in)
	{ screen: "file-upload", label: "Upload" },
	{ screen: "configure", label: "Configure" },
	{ screen: "cloud-generation", label: "Generate" },
	{ screen: "cloud-resume", label: "Resume" },
];

// Key actions for each screen
const screenActions: Record<Screen, KeyAction[]> = {
	landing: [
		{ key: "Enter", label: "Get Started" },
		{ key: "Esc", label: "Exit" },
	],
	consent: [
		{ key: "←/→", label: "Navigate" },
		{ key: "Enter", label: "Confirm" },
		{ key: "Esc", label: "Back" },
	],
	"consent-policy": [{ key: "Esc", label: "Back" }],
	"file-upload": [
		{ key: "↑/↓", label: "Navigate" },
		{ key: "←/→", label: "Browse" },
		{ key: "/", label: "Search" },
		{ key: "Enter", label: "Open/Select" },
		{ key: "Esc", label: "Back" },
	],
	configure: [
		{ key: "Tab", label: "Switch Panel" },
		{ key: "Space", label: "Toggle" },
		{ key: "a/d", label: "All/None" },
		{ key: "Enter", label: "Confirm" },
		{ key: "Esc", label: "Back" },
	],
	"project-list": [
		{ key: "↑/↓/←/→", label: "Navigate" },
		{ key: "Space", label: "Toggle" },
		{ key: "a/d", label: "All/None" },
		{ key: "Enter", label: "Continue" },
		{ key: "Esc", label: "Back" },
	],
	identity: [
		{ key: "↑/↓", label: "Navigate" },
		{ key: "Enter", label: "Confirm" },
		{ key: "Esc", label: "Back" },
	],
	"pipeline-launch": [
		{ key: "Enter", label: "Start" },
		{ key: "Esc", label: "Back" },
	],
	analysis: [{ key: "", label: "Processing..." }],
	polishing: [{ key: "", label: "Processing..." }],
	"draft-pause": [
		{ key: "Enter", label: "Continue" },
		{ key: "Esc", label: "Back" },
	],
	feedback: [
		{ key: "Tab", label: "Next Field" },
		{ key: "Enter", label: "Submit" },
		{ key: "Esc", label: "Cancel" },
	],
	"resume-preview": [
		{ key: "Tab", label: "Switch View" },
		{ key: "↑/↓", label: "Scroll" },
		{ key: "r", label: "Restart" },
		{ key: "Esc", label: "Exit" },
	],
	"cloud-auth": [
		// Only shown when user needs to log in (CopilotLogin handles keyboard)
		{ key: "Esc", label: "Back" },
	],
	"cloud-generation": [{ key: "Esc", label: "Back" }],
	"cloud-resume": [
		{ key: "1/2/3/4", label: "Switch Tab" },
		{ key: "↑/↓", label: "Scroll" },
		{ key: "r", label: "Restart" },
		{ key: "Esc", label: "Exit" },
	],
};

function App() {
	const renderer = useRenderer();
	useSelectionCopy();
	const {
		state,
		reset,
		resetRunState,
		setContributors,
		setDetectedRepos,
		setIntakeId,
		setPipelineNotice,
		setSelectedEmail,
		setSelectedRepoIds,
		setResumeV3Draft,
		setResumeV3Output,
		setZipPath: setContextZipPath,
	} = useAppState();
	const [screen, setScreen] = useState<Screen>("landing");
	const [filePath, setFilePath] = useState("");
	const [consentLevel, setConsentLevel] = useState<ConsentLevel>("local-llm");
	const [cloudModelId, setCloudModelId] = useState("");
	const [cloudGitIdentity, setCloudGitIdentity] = useState<{
		login: string;
		name: string | null;
		email: string;
	} | null>(null);
	const [cloudProfile, setCloudProfile] = useState<DeveloperProfile | null>(
		null,
	);
	const [isLandingIntroPhase, setIsLandingIntroPhase] = useState(true);
	const [visitedScreens, setVisitedScreens] = useState<Set<Screen>>(new Set());
	const [localFlowError, setLocalFlowError] = useState<string | null>(null);

	const localProjects = useMemo(
		() =>
			state.detectedRepos.map((repo) => ({
				id: repo.id,
				name: repo.name,
				language: "Local repo",
				description: repo.rel_path,
				technologies: [],
				commits: 0,
				files: 0,
				lastUpdated: "Ready for analysis",
			})),
		[state.detectedRepos],
	);

	const navigateTo = (target: Screen) => {
		setScreen(target);
	};

	const resetLocalFlow = () => {
		reset();
		setFilePath("");
		setLocalFlowError(null);
		setScreen("landing");
	};

	const loadLocalPipelineContext = async (path: string) => {
		setLocalFlowError(null);
		setFilePath(path);
		setContextZipPath(path);
		setPipelineNotice(null);
		resetRunState();
		setSelectedEmail(null);
		setContributors([]);

		try {
			const intake = await api.createPipelineIntake(path);
			setIntakeId(intake.intake_id);
			setDetectedRepos(intake.repos);
			setSelectedRepoIds([]);
			setContributors([]);

			setScreen("configure");
		} catch (error) {
			setLocalFlowError(toErrorMessage(error));
		}
	};

	useEffect(() => {
		if (screen === "landing") {
			setIsLandingIntroPhase(true);
		} else {
			setVisitedScreens((prev) => {
				if (prev.has(screen)) return prev;
				const next = new Set(prev);
				next.add(screen);
				return next;
			});
		}
	}, [screen]);

	// Global keyboard handler
	useKeyboard((key) => {
		// Exit on Ctrl+C
		if (key.ctrl && key.name === "c") {
			renderer.destroy();
			return;
		}

		switch (screen) {
			case "landing":
				if (key.name === "return") {
					setScreen("consent");
				} else if (key.name === "escape") {
					renderer.destroy();
				}
				break;

			case "consent":
				// Consent wizard handles its own keyboard events
				break;

			case "cloud-auth":
				// CloudAuth handles its own keyboard (Esc via CopilotLogin)
				break;

			case "consent-policy":
			case "identity":
			case "pipeline-launch":
			case "draft-pause":
			case "feedback":
				break;

			case "file-upload":
				if (key.name === "escape") {
					setScreen(consentLevel === "cloud" ? "cloud-auth" : "consent");
				}
				break;

			case "configure":
				// ConfigureScreen handles its own keyboard events
				break;

			case "project-list":
				break;

			case "resume-preview":
				break;

			case "analysis":
				break;

			case "cloud-generation":
				// CloudFlow added in PR 3 — escape back to file-upload in the meantime
				if (key.name === "escape") {
					setScreen("file-upload");
				}
				break;

			case "cloud-resume":
				if (key.name === "r") {
					setScreen("landing");
				} else if (key.name === "escape") {
					renderer.destroy();
				}
				break;
		}
	});

	const renderScreen = () => {
		switch (screen) {
			case "landing":
				return (
					<Landing
						onReady={() => setScreen("consent")}
						onIntroPhaseChange={setIsLandingIntroPhase}
					/>
				);

			case "consent":
				return (
					<ConsentScreen
						onContinue={(level?: ConsentLevel) => {
							if (level) setConsentLevel(level);
							setScreen(level === "cloud" ? "cloud-auth" : "file-upload");
						}}
						onBack={() => setScreen("landing")}
					/>
				);

			case "cloud-auth":
				return (
					<CloudAuth
						onComplete={(result) => {
							setCloudModelId(result.modelId);
							setCloudGitIdentity(result.gitIdentity);
							setScreen("file-upload");
						}}
						onBack={() => setScreen("consent")}
					/>
				);

			case "file-upload":
				return (
					<FileUpload
						onSubmit={(path) => loadLocalPipelineContext(path)}
						onBack={() =>
							setScreen(consentLevel === "cloud" ? "cloud-auth" : "consent")
						}
					/>
				);

			case "configure":
				return (
					<ConfigureScreen
						consentLevel={consentLevel}
						projects={localProjects}
						initialSelectedIds={state.selectedRepoIds}
						initialEmail={
							state.selectedEmail ??
							cloudGitIdentity?.email ??
							""
						}
						cloudLogin={cloudGitIdentity?.login}
						cloudName={cloudGitIdentity?.name}
						onContinue={(result) => {
							setSelectedRepoIds(result.selectedProjectIds);
							setSelectedEmail(result.email);

							if (consentLevel === "cloud" && result.modelId) {
								setCloudModelId(result.modelId);
								setCloudGitIdentity({
									login: cloudGitIdentity?.login ?? "",
									name: cloudGitIdentity?.name ?? null,
									email: result.email,
								});
								setScreen("cloud-generation");
							} else {
								setScreen("analysis");
							}
						}}
						onBack={() => setScreen("file-upload")}
					/>
				);

			case "project-list":
			case "identity":
				// Legacy — redirect to configure
				return null;

			case "pipeline-launch":
				// Legacy — falls through to analysis
			case "analysis":
				return (
					<SnakeWithProgress
						mode="local"
						intakeId={state.intakeId ?? ""}
						repoIds={state.selectedRepoIds}
						userEmail={state.selectedEmail ?? ""}
						onDraftReady={(draft) => {
							setResumeV3Draft(draft);
							setScreen("draft-pause");
						}}
						onComplete={(output) => {
							setResumeV3Output(output);
							setScreen("resume-preview");
						}}
						onBack={() => setScreen("configure")}
					/>
				);

			case "polishing":
				return (
					<SnakeWithProgress
						mode="local"
						intakeId={state.intakeId ?? ""}
						repoIds={state.selectedRepoIds}
						userEmail={state.selectedEmail ?? ""}
						pollOnly
						onDraftReady={(draft) => {
							setResumeV3Draft(draft);
							setScreen("draft-pause");
						}}
						onComplete={(output) => {
							setResumeV3Output(output);
							setScreen("resume-preview");
						}}
						onBack={() => setScreen("draft-pause")}
					/>
				);

			case "draft-pause":
				return (
					<DraftPauseScreen
						onNext={(target) => setScreen(target as Screen)}
					/>
				);

			case "resume-preview":
				return (
					<ResumePreview
						onBack={() => setScreen("configure")}
						onPolishAgain={() => setScreen("draft-pause")}
						onRestart={resetLocalFlow}
					/>
				);

			case "cloud-generation":
				return (
					<CloudFlow
						zipPath={filePath}
						modelId={cloudModelId}
						gitIdentity={cloudGitIdentity}
						selectedRepoPaths={state.selectedRepoIds}
						onComplete={(profile) => {
							setCloudProfile(profile);
							setScreen("cloud-resume");
						}}
						onBack={() => setScreen("configure")}
					/>
				);

			case "cloud-resume":
				return cloudProfile ? (
					<CloudResumePreview
						profile={cloudProfile}
						onBack={() => setScreen("cloud-generation")}
						onRestart={() => setScreen("landing")}
					/>
				) : null;

			case "feedback":
			case "consent-policy":
				return null;
		}
	};

	const screenForward: Record<
		string,
		{ onForward?: () => void; forwardLabel?: string }
	> = {};

	const forward = screenForward[screen] ?? {};
	const visibleActions =
		screen === "landing" && isLandingIntroPhase ? [] : screenActions[screen];

	const activeBreadcrumbScreens =
		consentLevel === "cloud"
			? CLOUD_BREADCRUMB_SCREENS
			: LOCAL_BREADCRUMB_SCREENS;

	const breadcrumbs: Breadcrumb[] | undefined =
		screen === "landing"
			? undefined
			: activeBreadcrumbScreens.map(({ screen: s, label }) => ({
					screen: s,
					label,
					visited: visitedScreens.has(s),
				}));

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			{/* Main content area */}
			<box flexGrow={1}>{renderScreen()}</box>

			{localFlowError ? (
				<box paddingLeft={2} paddingRight={2} paddingBottom={1}>
					<text>
						<span fg={theme.error}>{localFlowError}</span>
					</text>
				</box>
			) : null}

			{/* Bottom bar */}
			<BottomBar
				actions={visibleActions}
				breadcrumbs={breadcrumbs}
				currentScreen={screen === "polishing" ? "analysis" : screen}
				onNavigate={navigateTo}
				onForward={forward.onForward}
				forwardLabel={forward.forwardLabel}
			/>
		</box>
	);
}

const renderer = await createCliRenderer();
createRoot(renderer).render(
	<AppProvider>
		<ToastProvider>
			<App />
		</ToastProvider>
	</AppProvider>,
);
