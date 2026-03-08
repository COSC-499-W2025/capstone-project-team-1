import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useState } from "react";
import { Analysis } from "./components/Analysis";
import { BottomBar } from "./components/BottomBar";
import { ConsentScreen } from "./components/ConsentScreen";
import { FileUpload } from "./components/FileUpload";
import { Landing } from "./components/Landing";
import { ProjectList } from "./components/ProjectList";
import { ResumePreview } from "./components/ResumePreview";
import { AppProvider } from "./context/AppContext";
import { mockProjects, mockResumeData } from "./data/mockProjects";
import { type KeyAction, type Screen, theme } from "./types";

// Key actions for each screen
const screenActions: Record<Screen, KeyAction[]> = {
	landing: [
		{ key: "Enter", label: "Get Started" },
		{ key: "Esc", label: "Exit" },
	],
	"consent-policy": [
		{ key: "←/→", label: "Navigate" },
		{ key: "Enter", label: "Confirm" },
		{ key: "Esc", label: "Back" },
	],
	"file-upload": [
		{ key: "↑/↓", label: "Navigate" },
		{ key: "Enter", label: "Open/Select" },
		{ key: "Backspace", label: "Up" },
		{ key: "Ctrl+H", label: "Hidden" },
		{ key: "Esc", label: "Back" },
	],
	"project-list": [
		{ key: "↑/↓", label: "Navigate" },
		{ key: "Enter", label: "Analyze" },
		{ key: "Esc", label: "Back" },
	],
	analysis: [{ key: "", label: "Processing..." }],
	identity: [],
	"pipeline-launch": [],
	"draft-pause": [],
	feedback: [],
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
					setScreen("consent-policy");
				} else if (key.name === "escape") {
					renderer.destroy();
				}
				break;

			case "consent-policy":
				// Consent wizard handles its own keyboard events
				break;

			case "file-upload":
				if (key.name === "escape") {
					setScreen("consent-policy");
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
				return <Landing onGetStarted={() => setScreen("consent-policy")} />;

			case "consent-policy":
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
						onBack={() => setScreen("consent-policy")}
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

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			{/* Main content area */}
			<box flexGrow={1}>{renderScreen()}</box>

			{/* Bottom bar with keyboard shortcuts */}
			<BottomBar actions={screenActions[screen]} />
		</box>
	);
}

const renderer = await createCliRenderer();
createRoot(renderer).render(
	<AppProvider>
		<App />
	</AppProvider>
);
