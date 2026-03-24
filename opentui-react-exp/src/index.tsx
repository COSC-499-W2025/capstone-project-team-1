import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useEffect, useState } from "react";
import { Analysis } from "./components/Analysis";
import { BottomBar } from "./components/BottomBar";
import { CloudAuth, CloudFlow } from "./components/cloud-ai";
import { CloudResumePreview } from "./components/CloudResumePreview";
import { ConsentScreen } from "./components/ConsentScreen";
import { FileUpload } from "./components/FileUpload";
import { Landing } from "./components/Landing";
import { ProjectList } from "./components/ProjectList";
import { ResumePreview } from "./components/ResumePreview";
import { ToastProvider } from "./components/Toast";
import { AppProvider } from "./context/AppContext";
import { useSelectionCopy } from "./hooks/useSelectionCopy";
import type { ConsentLevel, DeveloperProfile } from "./api/types";
import { mockProjects, mockResumeData } from "./data/mockProjects";
import { type KeyAction, type Screen, theme } from "./types";
import type { Breadcrumb } from "./components/BottomBar";

// Screens shown in breadcrumbs (in order)
const LOCAL_BREADCRUMB_SCREENS: { screen: Screen; label: string }[] = [
	{ screen: "consent", label: "Consent" },
	{ screen: "file-upload", label: "Upload" },
	{ screen: "project-list", label: "Projects" },
	{ screen: "analysis", label: "Analyze" },
	{ screen: "resume-preview", label: "Resume" },
];

const CLOUD_BREADCRUMB_SCREENS: { screen: Screen; label: string }[] = [
	{ screen: "consent", label: "Consent" },
	{ screen: "cloud-auth", label: "Configure" },
	{ screen: "file-upload", label: "Upload" },
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
	"project-list": [
		{ key: "↑/↓", label: "Navigate" },
		{ key: "Enter", label: "Analyze" },
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
		{ key: "↑/↓", label: "Scroll" },
		{ key: "r", label: "Restart" },
		{ key: "Esc", label: "Exit" },
	],
	"cloud-auth": [
		{ key: "↑/↓", label: "Navigate" },
		{ key: "Enter", label: "Confirm" },
		{ key: "Esc", label: "Back" },
	],
	"cloud-generation": [{ key: "Esc", label: "Back" }],
	"cloud-resume": [
		{ key: "1/2/3", label: "Switch Tab" },
		{ key: "↑/↓", label: "Scroll" },
		{ key: "r", label: "Restart" },
		{ key: "Esc", label: "Exit" },
	],
};

function App() {
	const renderer = useRenderer();
	useSelectionCopy();
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

	const navigateTo = (target: Screen) => {
		setScreen(target);
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

			case "project-list":
				if (key.name === "return") {
					setScreen("analysis");
				} else if (key.name === "escape") {
					setScreen("file-upload");
				}
				break;

			case "analysis":
				// No keyboard actions during analysis
				break;

			case "resume-preview":
				if (key.name === "r") {
					setScreen("landing");
				} else if (key.name === "escape") {
					renderer.destroy();
				}
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
						onSubmit={(path) => {
							setFilePath(path);
							setScreen(
								consentLevel === "cloud" ? "cloud-generation" : "project-list",
							);
						}}
						onBack={() =>
							setScreen(consentLevel === "cloud" ? "cloud-auth" : "consent")
						}
					/>
				);

			case "project-list":
				return (
					<ProjectList
						projects={mockProjects}
						onContinue={() => setScreen("analysis")}
						onBack={() => setScreen("file-upload")}
					/>
				);

			case "analysis":
				return (
					<Analysis
						onComplete={() => setScreen("resume-preview")}
						onBack={() => setScreen("project-list")}
					/>
				);

			case "resume-preview":
				return (
					<ResumePreview
						data={mockResumeData}
						onBack={() => setScreen("analysis")}
						onRestart={() => setScreen("landing")}
					/>
				);

			case "cloud-generation":
				return (
					<CloudFlow
						zipPath={filePath}
						modelId={cloudModelId}
						gitIdentity={cloudGitIdentity}
						onComplete={(profile) => {
							setCloudProfile(profile);
							setScreen("cloud-resume");
						}}
						onBack={() => setScreen("file-upload")}
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

			case "consent-policy":
			case "identity":
			case "pipeline-launch":
			case "draft-pause":
			case "feedback":
				return null;
		}
	};

	const screenForward: Record<
		string,
		{ onForward?: () => void; forwardLabel?: string }
	> = {
		"project-list": {
			onForward: () => setScreen("analysis"),
			forwardLabel: "Analyze",
		},
	};

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

			{/* Bottom bar */}
			<BottomBar
				actions={visibleActions}
				breadcrumbs={breadcrumbs}
				currentScreen={screen}
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
