import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useEffect, useState } from "react";
import { Analysis } from "./components/Analysis";
import { BottomBar } from "./components/BottomBar";
import { ConsentScreen } from "./components/ConsentScreen";
import { FileUpload } from "./components/FileUpload";
import { Landing } from "./components/Landing";
import { ProjectList } from "./components/ProjectList";
import { ResumePreview } from "./components/ResumePreview";
import { ToastProvider } from "./components/Toast";
import { AppProvider } from "./context/AppContext";
import { mockProjects, mockResumeData } from "./data/mockProjects";
import { type KeyAction, type Screen, theme } from "./types";
import type { Breadcrumb } from "./components/BottomBar";

// Screens shown in breadcrumbs (in order)
const BREADCRUMB_SCREENS: { screen: Screen; label: string }[] = [
	{ screen: "consent", label: "Consent" },
	{ screen: "file-upload", label: "Upload" },
	{ screen: "project-list", label: "Projects" },
	{ screen: "analysis", label: "Analyze" },
	{ screen: "resume-preview", label: "Resume" },
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
	analysis: [{ key: "", label: "Processing..." }],
	"resume-preview": [
		{ key: "↑/↓", label: "Scroll" },
		{ key: "r", label: "Restart" },
		{ key: "Esc", label: "Exit" },
	],
};

function App() {
	const renderer = useRenderer();
	const [screen, setScreen] = useState<Screen>("landing");
	const [filePath, setFilePath] = useState("");
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

			case "file-upload":
				if (key.name === "escape") {
					setScreen("consent");
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
		}
	});

	const renderScreen = () => {
		switch (screen) {
			case "landing":
				return (
					<Landing
						onGetStarted={() => setScreen("consent")}
						onIntroPhaseChange={setIsLandingIntroPhase}
					/>
				);

			case "consent":
				return (
					<ConsentScreen
						onContinue={() => {
							setScreen("file-upload");
						}}
						onBack={() => setScreen("landing")}
					/>
				);

			case "file-upload":
				return (
					<FileUpload
						onSubmit={(path) => {
							setFilePath(path);
							setScreen("project-list");
						}}
						onBack={() => setScreen("consent")}
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
		}
	};

	const screenForward: Record<string, { onForward?: () => void; forwardLabel?: string }> = {
		"project-list": {
			onForward: () => setScreen("analysis"),
			forwardLabel: "Analyze",
		},
	};

	const forward = screenForward[screen] ?? {};
	const visibleActions =
		screen === "landing" && isLandingIntroPhase ? [] : screenActions[screen];

	const breadcrumbs: Breadcrumb[] | undefined =
		screen === "landing"
			? undefined
			: BREADCRUMB_SCREENS.map(({ screen: s, label }) => ({
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
