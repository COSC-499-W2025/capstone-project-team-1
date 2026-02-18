import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useMemo, useState } from "react";
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

function screenActions(screen: Screen): KeyAction[] {
	switch (screen) {
		case "landing":
			return [
				{ key: "Enter", label: "Get Started" },
				{ key: "Esc", label: "Exit" },
			];
		case "consent-policy":
			return [
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
				{ key: "Enter", label: "Feedback" },
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
				{ key: "Tab", label: "Draft/Final/Diff" },
				{ key: "P", label: "Polish Again" },
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

	const startNewRun = () => {
		reset();
		setScreen("landing");
		setAnalysisMode("phase1");
	};

	const renderScreen = () => {
			switch (screen) {
				case "landing":
					return <Landing />;

			case "consent-policy":
				return (
					<ConsentScreen
						onContinue={() => setScreen("file-upload")}
						onBack={() => setScreen("landing")}
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
						onContinue={() => setScreen("feedback")}
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
			<BottomBar actions={actions} />
		</box>
	);
}

const renderer = await createCliRenderer();
createRoot(renderer).render(
	<AppProvider>
		<App />
	</AppProvider>,
);
