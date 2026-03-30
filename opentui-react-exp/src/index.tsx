import { createCliRenderer } from "@opentui/core";
import { createRoot, useKeyboard, useRenderer } from "@opentui/react";
import { useEffect, useState } from "react";
import { api } from "./api/endpoints";
import type { ConsentLevel, DeveloperProfile } from "./api/types";
import { Analysis } from "./components/Analysis";
import { BottomBar } from "./components/BottomBar";
import type { Breadcrumb } from "./components/BottomBar";
import { CloudAuth, CloudFlow } from "./components/cloud-ai";
import { CloudResumePreview } from "./components/CloudResumePreview";
import { ConsentScreen } from "./components/ConsentScreen";
import { DraftPauseScreen } from "./components/DraftPauseScreen";
import { FeedbackScreen } from "./components/FeedbackScreen";
import { EducationAwardsScreen } from "./components/EducationAwardsScreen";
import { FileUpload } from "./components/FileUpload";
import { IdentityScreen } from "./components/IdentityScreen";
import { Landing } from "./components/Landing";
import { PipelineLaunchScreen } from "./components/PipelineLaunchScreen";
import { ProjectList } from "./components/ProjectList";
import { ResumePreview } from "./components/ResumePreview";
import { ToastProvider, useToast } from "./components/Toast";
import { TopBar } from "./components/TopBar";
import { AppProvider, useAppState } from "./context/AppContext";
import { useSelectionCopy } from "./hooks/useSelectionCopy";
import { type AnalysisMode, type KeyAction, type Screen, theme } from "./types";

const LOCAL_LLM_BREADCRUMB_SCREENS: { screen: Screen; label: string }[] = [
	{ screen: "consent", label: "Consent" },
	{ screen: "consent-policy", label: "Policy" },
		{ screen: "file-upload", label: "Upload" },
		{ screen: "project-list", label: "Repos" },
		{ screen: "identity", label: "Identity" },
		{ screen: "education-awards", label: "Education/Awards" },
		{ screen: "pipeline-launch", label: "Launch" },
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

function screenHint(screen: Screen, consentLevel: ConsentLevel): string {
	switch (screen) {
		case "landing":
			return "Turn your repos into a polished, recruiter-ready resume";
		case "consent":
			return consentLevel === "cloud"
				? "Choose the cloud path or switch back to a local run"
				: "Choose how this run should be processed";
		case "consent-policy":
			return "Confirm local AI processing before continuing";
		case "file-upload":
			return consentLevel === "cloud"
				? "Select the ZIP file to send into the cloud agent flow"
				: "Select the ZIP file from your GitHub export";
		case "project-list":
			return "Pick the repositories to include in this run";
		case "identity":
			return "Choose the contributor identity that represents your work";
		case "education-awards":
			return "Add the education and awards details that cannot be inferred from your repos";
		case "pipeline-launch":
			return "Review your repo and identity selections before starting";
		case "analysis":
			return "The local pipeline is processing your repositories";
		case "draft-pause":
			return "Review the draft and submit feedback for Stage 3";
		case "feedback":
			return "Enter another round of polish feedback and resubmit";
		case "resume-preview":
			return consentLevel === "cloud"
				? "Review the generated resume"
				: "Review, save, or request another polish pass";
		case "cloud-auth":
			return "Authenticate and pick the cloud model for this run";
		case "cloud-generation":
			return "The cloud agent is generating your resume";
		case "cloud-resume":
			return "Review the cloud-generated resume";
	}
}

function screenActions(screen: Screen, consentLevel: ConsentLevel): KeyAction[] {
	switch (screen) {
		case "landing":
			return [
				{ key: "Enter", label: "Get Started" },
				{ key: "Esc", label: "Exit" },
			];
		case "consent":
			return [
				{ key: "←/→", label: "Navigate" },
				{ key: "Enter", label: "Confirm" },
				{ key: "Esc", label: "Back" },
			];
		case "consent-policy":
			return [
				{ key: "Space", label: "Toggle" },
				{ key: "Enter", label: "Continue" },
				{ key: "Esc", label: "Back" },
			];
		case "file-upload":
			return [
				{ key: "↑/↓", label: "Navigate" },
				{ key: "←/→", label: "Browse" },
				{ key: "/", label: "Search" },
				{ key: "Enter", label: "Open/Select" },
				{ key: "Esc", label: "Back" },
			];
		case "project-list":
			return consentLevel === "cloud"
				? [
						{ key: "↑/↓", label: "Navigate" },
						{ key: "Enter", label: "Analyze" },
						{ key: "Esc", label: "Back" },
					]
				: [
						{ key: "Space", label: "Toggle" },
						{ key: "A", label: "Select All" },
						{ key: "N", label: "Clear" },
						{ key: "Enter", label: "Continue" },
						{ key: "Esc", label: "Back" },
					];
		case "identity":
			return [
				{ key: "↑/↓", label: "Navigate" },
				{ key: "Tab", label: "Manual" },
				{ key: "Enter", label: "Confirm" },
				{ key: "Esc", label: "Back" },
			];
		case "education-awards":
			return [
				{ key: "↑/↓", label: "Navigate" },
				{ key: "←/→", label: "Switch" },
				{ key: "N", label: "Add" },
				{ key: "E", label: "Edit" },
				{ key: "Del", label: "Remove" },
				{ key: "Enter", label: "Continue" },
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
				{ key: "Tab", label: "Toggle Pane" },
				{ key: "1-9", label: "Jump Section" },
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
			return consentLevel === "cloud"
				? [
						{ key: "1/2/3", label: "Switch Tab" },
						{ key: "↑/↓", label: "Scroll" },
						{ key: "R", label: "Restart" },
						{ key: "Esc", label: "Exit" },
					]
				: [
						{ key: "↑/↓", label: "Section" },
						{ key: "1-5", label: "Jump" },
						{ key: "S", label: "Save" },
						{ key: "Tab", label: "Mode" },
						{ key: "P", label: "Polish" },
						{ key: "R", label: "Restart" },
						{ key: "Esc", label: "Exit" },
					];
		case "cloud-auth":
			return [
				{ key: "↑/↓", label: "Navigate" },
				{ key: "Enter", label: "Confirm" },
				{ key: "Esc", label: "Back" },
			];
		case "cloud-generation":
			return [{ key: "Esc", label: "Back" }];
		case "cloud-resume":
			return [
				{ key: "1/2/3", label: "Switch Tab" },
				{ key: "↑/↓", label: "Scroll" },
				{ key: "R", label: "Restart" },
				{ key: "Esc", label: "Exit" },
			];
	}
}

function App() {
	const renderer = useRenderer();
	const toast = useToast();
	useSelectionCopy();
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
	const [analysisMode, setAnalysisMode] = useState<AnalysisMode>("phase1");
	const [policyAccepted, setPolicyAccepted] = useState(false);
	const [isLandingIntroPhase, setIsLandingIntroPhase] = useState(true);
	const [visitedScreens, setVisitedScreens] = useState<Set<Screen>>(new Set());

	const navigateTo = (target: Screen) => {
		setScreen(target);
	};

	const startNewRun = () => {
		reset();
		setScreen("landing");
		setFilePath("");
		setConsentLevel("local-llm");
		setCloudModelId("");
		setCloudGitIdentity(null);
		setCloudProfile(null);
		setAnalysisMode("phase1");
		setPolicyAccepted(false);
		setVisitedScreens(new Set());
	};

	const isCloudFlow = consentLevel === "cloud";

	useEffect(() => {
		if (screen === "landing") {
			setIsLandingIntroPhase(true);
			return;
		}

		setVisitedScreens((prev) => {
			if (prev.has(screen)) {
				return prev;
			}

			const next = new Set(prev);
			next.add(screen);
			return next;
		});
	}, [screen]);

	const handleLocalUpload = async (path: string) => {
		try {
			const intake = await api.createPipelineIntake(path);
			setZipPath(path);
			setIntakeId(intake.intake_id);
			setDetectedRepos(intake.repos);
			setSelectedRepoIds([]);
			setContributors([]);
			setSelectedEmail(null);
			resetRunState();
			setPipelineNotice(
				intake.repos.length
					? null
					: "No repositories were detected in this ZIP intake.",
			);
			setScreen("project-list");
		} catch (error) {
			toast.error(error);
		}
	};

	const handleProjectListContinue = async () => {
		if (!state.selectedRepoIds.length) {
			return;
		}

		try {
			const response = await api.getPipelineContributors({
				repo_ids: state.selectedRepoIds,
			});
			setContributors(response.contributors);
			setPipelineNotice(
				response.contributors.length
					? null
					: "No contributors found in selected repos. Enter an email manually.",
			);
			setScreen("identity");
		} catch (error) {
			toast.error(error);
		}
	};

	const handleAnalysisNext = (target: string) => {
		if (target === "draft-pause") {
			setScreen("draft-pause");
			return;
		}

		if (target === "resume-preview") {
			setScreen("resume-preview");
			return;
		}

		if (target === "project-list") {
			setAnalysisMode("phase1");
			setScreen("project-list");
		}
	};

	const handlePostDraftNext = (target: string) => {
		if (target === "analysis") {
			setAnalysisMode("phase3");
			setScreen("analysis");
			return;
		}

		if (target === "project-list") {
			setAnalysisMode("phase1");
			setScreen("project-list");
		}
	};

	useKeyboard((key) => {
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
			case "consent-policy":
				if (key.name === "space") {
					setPolicyAccepted((prev) => !prev);
					return;
				}
				if (
					(key.name === "return" || key.name === "enter") &&
					policyAccepted
				) {
					setScreen("file-upload");
					return;
				}
				if (key.name === "escape") {
					setScreen("consent");
				}
				break;
			case "cloud-generation":
				if (key.name === "escape") {
					setScreen("file-upload");
				}
				break;
			case "cloud-resume":
				if (key.name === "r") {
					startNewRun();
				} else if (key.name === "escape") {
					renderer.destroy();
				}
				break;
			default:
				break;
		}
	});

	const renderConsentPolicy = () => (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Local Processing Consent"
				description="Confirm the local AI processing flow before you continue."
			/>

			<box flexGrow={1} justifyContent="center" alignItems="center" padding={2}>
				<box
					width={88}
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					gap={1}
				>
					<text>
						<span fg={theme.textSecondary}>
							This path creates a local intake, reads repo metadata, detects
							contributors, and runs the local resume pipeline on your machine.
						</span>
					</text>
					<text>
						<span fg={theme.textSecondary}>
							The cloud flow stays separate. This confirmation only applies to
							the local pipeline path.
						</span>
					</text>

					<box marginTop={1} flexDirection="row" gap={1}>
						<text>
							<span fg={policyAccepted ? theme.success : theme.textDim}>
								{policyAccepted ? "[✓]" : "[ ]"}
							</span>
						</text>
						<text>
							<span fg={theme.textSecondary}>
								I understand this run will use the local AI pipeline.
							</span>
						</text>
					</box>
				</box>
			</box>
		</box>
	);

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
							const nextLevel = level ?? "local-llm";
							setConsentLevel(nextLevel);
							if (nextLevel === "cloud") {
								setScreen("cloud-auth");
								return;
							}
							if (nextLevel === "local") {
								toast.show({
									variant: "warning",
									message:
										"OpenTUI currently continues through the local AI pipeline for non-cloud runs.",
									duration: 4000,
								});
							}
							setPolicyAccepted(false);
							setScreen("consent-policy");
						}}
						onBack={() => setScreen("landing")}
					/>
				);
			case "consent-policy":
				return renderConsentPolicy();
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
						onSubmit={async (path) => {
							setFilePath(path);
							if (isCloudFlow) {
								setScreen("cloud-generation");
								return;
							}
							await handleLocalUpload(path);
						}}
						onBack={() =>
							setScreen(isCloudFlow ? "cloud-auth" : "consent-policy")
						}
					/>
				);
			case "project-list":
				return (
					<ProjectList
						repos={state.detectedRepos}
						selectedRepoIds={state.selectedRepoIds}
						onChangeSelection={setSelectedRepoIds}
						onContinue={() => {
							void handleProjectListContinue();
						}}
						onBack={() => setScreen("file-upload")}
						notice={state.pipelineNotice}
					/>
				);
			case "identity":
				return (
					<IdentityScreen
						onNext={() => setScreen("education-awards")}
						onBack={() => setScreen("project-list")}
					/>
				);
			case "education-awards":
				return (
					<EducationAwardsScreen
						onNext={(target) =>
							setScreen(target === "analysis" ? "pipeline-launch" : (target as Screen))
						}
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
						analysisMode={analysisMode}
						onNext={handleAnalysisNext}
					/>
				);
			case "draft-pause":
				return <DraftPauseScreen onNext={handlePostDraftNext} />;
			case "feedback":
				return <FeedbackScreen onNext={handlePostDraftNext} />;
			case "resume-preview":
				return (
					<ResumePreview
						onPolishAgain={() => setScreen("feedback")}
						onRestart={startNewRun}
						onExit={() => renderer.destroy()}
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
						onRestart={startNewRun}
					/>
				) : null;
		}
	};

	const activeBreadcrumbScreens =
		consentLevel === "cloud"
			? CLOUD_BREADCRUMB_SCREENS
			: LOCAL_LLM_BREADCRUMB_SCREENS;

	const screenForward: Record<
		string,
		{ onForward?: () => void; forwardLabel?: string }
	> = {
		"project-list": {
			onForward: () => {
				void handleProjectListContinue();
			},
			forwardLabel: "Continue",
		},
	};

	const forward = screenForward[screen] ?? {};
	const visibleActions =
		screen === "landing" && isLandingIntroPhase
			? []
			: screenActions(screen, consentLevel);

	const breadcrumbs: Breadcrumb[] | undefined =
		screen === "landing"
			? undefined
			: activeBreadcrumbScreens.map(({ screen: breadcrumbScreen, label }) => ({
					screen: breadcrumbScreen,
					label,
					visited: visitedScreens.has(breadcrumbScreen),
				}));

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<box flexGrow={1}>{renderScreen()}</box>
			<BottomBar
				actions={visibleActions}
				hint={
					screen === "landing" && isLandingIntroPhase
						? ""
						: screenHint(screen, consentLevel)
				}
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
