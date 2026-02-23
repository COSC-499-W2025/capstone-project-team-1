import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useEffect, useMemo, useState } from "react";
import { Analysis } from "./components/Analysis";
import { BottomBar } from "./components/BottomBar";
import { ConsentScreen } from "./components/ConsentScreen";
import { DraftPauseScreen } from "./components/DraftPauseScreen";
import { FeedbackScreen } from "./components/FeedbackScreen";
import { FileUpload } from "./components/FileUpload";
import { IdentityScreen } from "./components/IdentityScreen";
import { Landing } from "./components/Landing";
import { PipelineLaunchScreen } from "./components/PipelineLaunchScreen";
import { ProjectList } from "./components/ProjectList";
import { ResumePreview } from "./components/ResumePreview";
import { AppProvider, useAppState } from "./context/AppContext";
import { type AnalysisMode, type KeyAction, type Screen, theme } from "./types";

function screenHint(screen: Screen): string {
	switch (screen) {
		case "landing":
			return "Transform your repos into a polished, recruiter-ready resume";
		case "consent-policy":
			return "Check the box to confirm you're happy to proceed";
		case "file-upload":
			return "Select the ZIP file from your GitHub export";
		case "project-list":
			return "Pick the repos to include in your resume";
		case "identity":
			return "We use your email to filter which commits count as yours";
		case "pipeline-launch":
			return "Ready? The local AI will generate your resume on-device";
		case "analysis":
			return "Processing locally — your data never leaves this machine";
		case "draft-pause":
			return "Review each section, add feedback notes, then press Enter to start Stage 3";
		case "feedback":
			return "Your notes guide the AI in the next pass";
		case "resume-preview":
			return "Your resume is ready — navigate sections, compare changes, or save";
		default:
			return "";
	}
}

function screenActions(screen: Screen): KeyAction[] {
	switch (screen) {
		case "landing":
			return [
				{ key: "Enter", label: "Get Started" },
				{ key: "Esc", label: "Exit" },
			];
		case "consent-policy":
			return [
				{ key: "Space", label: "Toggle" },
				{ key: "Enter", label: "Accept" },
				{ key: "Esc", label: "Back" },
			];
		case "file-upload":
			return [
				{ key: "Up/Down", label: "Navigate" },
				{ key: "Enter", label: "Open/Select" },
				{ key: "Backspace", label: "Up" },
				{ key: "Esc", label: "Back" },
			];
		case "project-list":
			return [
				{ key: "Space", label: "Toggle" },
				{ key: "A", label: "Select All" },
				{ key: "N", label: "Clear" },
				{ key: "Enter", label: "Continue" },
				{ key: "Esc", label: "Back" },
			];
		case "identity":
			return [
				{ key: "Up/Down", label: "Navigate" },
				{ key: "Enter", label: "Select" },
				{ key: "Tab", label: "Manual" },
				{ key: "Esc", label: "Back" },
			];
		case "pipeline-launch":
			return [
				{ key: "Enter", label: "Start" },
				{ key: "Esc", label: "Back" },
			];
		case "analysis":
			return [{ key: "Esc", label: "Cancel Job" }];
		case "draft-pause":
			return [
				{ key: "↑↓", label: "Navigate" },
				{ key: "Tab", label: "Next Field" },
				{ key: "Enter", label: "Submit" },
				{ key: "Esc", label: "Cancel Job" },
			];
		case "feedback":
			return [
				{ key: "Tab", label: "Next Field" },
				{ key: "Enter", label: "Submit" },
				{ key: "Esc", label: "Cancel Job" },
			];
		case "resume-preview":
			return [
				{ key: "↑↓", label: "Section" },
				{ key: "1-5", label: "Jump" },
				{ key: "S", label: "Save" },
				{ key: "Tab", label: "Mode" },
				{ key: "P", label: "Polish" },
				{ key: "R", label: "Restart" },
				{ key: "Esc", label: "Exit" },
			];
		default:
			return [];
	}
}

function App() {
	const renderer = useRenderer();
	const {
		state,
		setZipPath,
		setIntakeId,
		setDetectedRepos,
		setSelectedRepoIds,
		setContributors,
		setSelectedEmail,
		setPipelineNotice,
		reset,
		resetRunState,
	} = useAppState();

	const [screen, setScreen] = useState<Screen>("landing");
	const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("phase1");
	const [hint, setHint] = useState(() => screenHint("landing"));
	const [landingReady, setLandingReady] = useState(false);

	useEffect(() => {
		setHint(screenHint(screen));
		if (screen === "landing") setLandingReady(false);
	}, [screen]);

	useKeyboard((key) => {
		if (key.ctrl && key.name === "c") {
			renderer.destroy();
			return;
		}

		if (screen === "landing") {
			if (key.name === "return" || key.name === "enter") {
				setScreen("consent-policy");
			}
			if (key.name === "escape") {
				renderer.destroy();
			}
		}
	});

	const actions = useMemo(() => screenActions(screen), [screen]);
	const bottomBarReady = screen !== "landing" || landingReady;

	const startNewRun = () => {
		reset();
		setScreen("landing");
		setAnalysisMode("phase1");
	};

	const renderScreen = () => {
		switch (screen) {
			case "landing":
				return <Landing onReady={() => setLandingReady(true)} />;

			case "consent-policy":
				return (
					<ConsentScreen
						onContinue={() => setScreen("file-upload")}
						onBack={() => setScreen("landing")}
						onHintChange={setHint}
					/>
				);

			case "file-upload":
				return (
					<FileUpload
						onIntakeCreated={(zipPath, intake) => {
							setZipPath(zipPath);
							setIntakeId(intake.intake_id);
							setDetectedRepos(intake.repos);
							setSelectedRepoIds([]);
							setContributors([]);
							setSelectedEmail(null);
							resetRunState();
							setPipelineNotice(null);
							setScreen("project-list");
						}}
						onBack={() => setScreen("consent-policy")}
					/>
				);

			case "project-list":
				return (
					<ProjectList
						repos={state.detectedRepos}
						selectedRepoIds={state.selectedRepoIds}
						onChangeSelection={setSelectedRepoIds}
						onContinue={() => {
							setPipelineNotice(null);
							setScreen("identity");
						}}
						onBack={() => setScreen("file-upload")}
						notice={state.pipelineNotice}
					/>
				);

			case "identity":
				return (
					<IdentityScreen
						onContinue={() => setScreen("pipeline-launch")}
						onBack={() => setScreen("project-list")}
					/>
				);

			case "pipeline-launch":
				return (
					<PipelineLaunchScreen
						onStarted={() => {
							setAnalysisMode("phase1");
							setScreen("analysis");
						}}
						onBack={() => setScreen("identity")}
					/>
				);

			case "analysis":
				return (
					<Analysis
						mode={analysisMode}
						onDraftReady={() => setScreen("draft-pause")}
						onReady={() => setScreen("resume-preview")}
						onCancelReturn={() => {
							setAnalysisMode("phase1");
							setScreen("project-list");
						}}
					/>
				);

			case "draft-pause":
				return (
					<DraftPauseScreen
						onSubmitted={() => {
							setAnalysisMode("phase3");
							setScreen("analysis");
						}}
						onCancelReturn={() => {
							setAnalysisMode("phase1");
							setScreen("project-list");
						}}
					/>
				);

			case "feedback":
				return (
					<FeedbackScreen
						onSubmitted={() => {
							setAnalysisMode("phase3");
							setScreen("analysis");
						}}
						onCancelReturn={() => {
							setAnalysisMode("phase1");
							setScreen("project-list");
						}}
					/>
				);

			case "resume-preview":
				return (
					<ResumePreview
						onPolishAgain={() => setScreen("feedback")}
						onRestart={startNewRun}
						onExit={() => renderer.destroy()}
					/>
				);
		}
	};

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<box flexGrow={1}>{renderScreen()}</box>
			<BottomBar
				hint={bottomBarReady ? hint : ""}
				actions={bottomBarReady ? actions : []}
			/>
		</box>
	);
}

const renderer = await createCliRenderer();
createRoot(renderer).render(
	<AppProvider>
		<App />
	</AppProvider>,
);
