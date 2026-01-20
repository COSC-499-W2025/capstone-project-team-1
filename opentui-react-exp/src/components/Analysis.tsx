import { useEffect, useState } from "react";
import { analysisSteps } from "../data/mockProjects";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface AnalysisProps {
	onComplete: () => void;
	onBack: () => void;
}

const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export function Analysis({ onComplete, onBack }: AnalysisProps) {
	const [currentStep, setCurrentStep] = useState(0);
	const [spinnerIndex, setSpinnerIndex] = useState(0);
	const [progress, setProgress] = useState(0);
	const [logs, setLogs] = useState<string[]>([]);

	// Spinner animation
	useEffect(() => {
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, []);

	// Progress simulation
	useEffect(() => {
		if (currentStep >= analysisSteps.length) {
			setTimeout(onComplete, 500);
			return;
		}

		const stepDuration = 600 + Math.random() * 400;
		const step = analysisSteps[currentStep];

		if (!step) return;

		// Add log entry
		setLogs((prev) => [
			...prev,
			`[${new Date().toLocaleTimeString()}] ${step.label}`,
		]);

		const timer = setTimeout(() => {
			setProgress(Math.round(((currentStep + 1) / analysisSteps.length) * 100));
			setCurrentStep((s) => s + 1);
		}, stepDuration);

		return () => clearTimeout(timer);
	}, [currentStep, onComplete]);

	const progressBarWidth = 50;
	const filledWidth = Math.round((progress / 100) * progressBarWidth);
	const progressBar =
		"█".repeat(filledWidth) + "░".repeat(progressBarWidth - filledWidth);

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				step="Step 3"
				title="Analysis"
				description="Mining artifacts and generating insights..."
			/>

			{/* Main content */}
			<box
				flexGrow={1}
				flexDirection="column"
				alignItems="center"
				justifyContent="center"
				gap={3}
			>
				{/* ASCII Art Animation */}
				{/* <box flexDirection="column" alignItems="center">
          <text>
            <span fg={theme.cyan}>
              {"    "}╭─────────────────────────────╮{"\n"}
              {"    "}│ {spinnerFrames[spinnerIndex]} Mining artifacts...     │{"\n"}
              {"    "}╰─────────────────────────────╯
            </span>
          </text>
        </box> */}

				{/* Step checklist */}
				<box
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					width={50}
				>
					{analysisSteps.map((step, index) => {
						const isCompleted = index < currentStep;
						const isCurrent = index === currentStep;

						return (
							<box key={step.id} flexDirection="row" gap={2}>
								<text>
									{isCompleted ? (
										<span fg={theme.success}>✓</span>
									) : isCurrent ? (
										<span fg={theme.cyan}>{spinnerFrames[spinnerIndex]}</span>
									) : (
										<span fg={theme.textDim}>○</span>
									)}
								</text>
								<text>
									<span
										fg={
											isCompleted
												? theme.success
												: isCurrent
													? theme.cyan
													: theme.textDim
										}
									>
										{step.label}
									</span>
								</text>
							</box>
						);
					})}
				</box>

				{/* Progress bar */}
				<box flexDirection="column" alignItems="center" gap={1}>
					<text>
						<span fg={theme.gold}>{progressBar}</span>
					</text>
					<text>
						<span fg={theme.textPrimary}>
							<strong>{progress}%</strong>
						</span>
						<span fg={theme.textDim}> complete</span>
					</text>
				</box>

				{/* Live log */}
				{/* <box
          flexDirection="column"
          width={60}
          height={5}
          backgroundColor={theme.bgMedium}
          padding={1}
          border
          borderStyle="single"
          borderColor={theme.textDim}
        >
          <text>
            <span fg={theme.textDim}>
              <strong>Log:</strong>
            </span>
          </text>
          {logs.slice(-3).map((log, i) => (
            <text key={i}>
              <span fg={theme.textDim}>{log}</span>
            </text>
          ))}
        </box> */}
			</box>

			{/* Demo Mode Banner */}
			<box
				height={3}
				border
				borderStyle="single"
				borderColor={theme.error}
				paddingLeft={2}
				paddingRight={2}
				paddingTop={1}
				paddingBottom={1}
			>
				<text>
					<span fg={theme.goldDark}>Demo Mode:</span>
					<span fg={theme.textDim}> Press </span>
					<span fg={theme.cyan}>Enter</span>
					<span fg={theme.textDim}> to continue</span>
				</text>
			</box>
		</box>
	);
}
