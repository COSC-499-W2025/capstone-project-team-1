import { useEffect, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { codexApi } from "../api/codex";
import { theme } from "../types";
import { TopBar } from "./TopBar";

interface CloudGenerationProps {
	zipPath: string;
	onComplete: (markdown: string) => void;
	onBack: () => void;
}

type Phase =
	| "checking-server"
	| "checking-auth"
	| "awaiting-login"
	| "generating"
	| "done"
	| "error";

const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export function CloudGeneration({
	zipPath,
	onComplete,
	onBack,
}: CloudGenerationProps) {
	const [phase, setPhase] = useState<Phase>("checking-server");
	const [error, setError] = useState<string | null>(null);
	const [email, setEmail] = useState<string | null>(null);
	const [plan, setPlan] = useState<string | null>(null);
	const [spinnerIndex, setSpinnerIndex] = useState(0);
	const [markdown, setMarkdown] = useState<string | null>(null);

	// Spinner animation
	useEffect(() => {
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, []);

	// Main flow
	useEffect(() => {
		let cancelled = false;

		async function run() {
			try {
				// 1. Check codex-server is reachable
				setPhase("checking-server");
				await codexApi.health();
				if (cancelled) return;

				// 2. Check auth
				setPhase("checking-auth");
				const acct = await codexApi.account();
				if (cancelled) return;

				if (acct.account) {
					setEmail(acct.account.email);
					setPlan(acct.account.planType);
				} else {
					// Need to log in
					setPhase("awaiting-login");
					await codexApi.login();
					if (cancelled) return;

					const acct2 = await codexApi.account();
					if (cancelled) return;
					if (acct2.account) {
						setEmail(acct2.account.email);
						setPlan(acct2.account.planType);
					}
				}

				// 3. Generate
				setPhase("generating");
				const result = await codexApi.generate(zipPath);
				if (cancelled) return;

				if (result.error) {
					setPhase("error");
					setError(result.error);
					return;
				}

				setMarkdown(result.markdown);
				setPhase("done");
			} catch (err) {
				if (cancelled) return;
				setPhase("error");
				setError(
					err instanceof Error ? err.message : "Unknown error occurred",
				);
			}
		}

		run();
		return () => {
			cancelled = true;
		};
	}, [zipPath]);

	// Navigate when done
	useEffect(() => {
		if (phase === "done" && markdown) {
			const timer = setTimeout(() => onComplete(markdown), 500);
			return () => clearTimeout(timer);
		}
	}, [phase, markdown, onComplete]);

	useKeyboard((key) => {
		if (key.name === "escape") {
			onBack();
		}
	});

	const phaseLabel: Record<Phase, string> = {
		"checking-server": "Connecting to Codex server...",
		"checking-auth": "Checking ChatGPT account...",
		"awaiting-login": "Waiting for ChatGPT login (check your browser)...",
		generating: "Generating resume from your code...",
		done: "Done!",
		error: "Error",
	};

	const phaseColor: Record<Phase, string> = {
		"checking-server": theme.cyan,
		"checking-auth": theme.cyan,
		"awaiting-login": theme.gold,
		generating: theme.cyan,
		done: theme.success,
		error: theme.error,
	};

	const steps: { label: string; doneAt: Phase[] }[] = [
		{
			label: "Connect to Codex server",
			doneAt: [
				"checking-auth",
				"awaiting-login",
				"generating",
				"done",
			],
		},
		{
			label: "Authenticate with ChatGPT",
			doneAt: ["generating", "done"],
		},
		{ label: "Analyze code & generate resume", doneAt: ["done"] },
	];

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="Cloud Generation"
				description="Generating your resume using Codex and your ChatGPT subscription."
			/>

			<box
				flexGrow={1}
				flexDirection="column"
				alignItems="center"
				justifyContent="center"
				gap={3}
			>
				{/* Account info */}
				{email && (
					<box
						border
						borderStyle="rounded"
						borderColor={theme.goldDim}
						paddingLeft={2}
						paddingRight={2}
						paddingTop={1}
						paddingBottom={1}
					>
						<text>
							<span fg={theme.textDim}>Signed in as </span>
							<span fg={theme.gold}>
								<strong>{email}</strong>
							</span>
							{plan && (
								<span fg={theme.textDim}> ({plan} plan)</span>
							)}
						</text>
					</box>
				)}

				{/* Step checklist */}
				<box
					flexDirection="column"
					border
					borderStyle="rounded"
					borderColor={theme.goldDim}
					padding={2}
					width={55}
				>
					{steps.map((step, index) => {
						const isDone = step.doneAt.includes(phase);
						const isCurrent =
							!isDone &&
							(index === 0 ||
								steps[index - 1].doneAt.includes(phase));

						return (
							<box key={index} flexDirection="row" gap={2}>
								<text>
									{isDone ? (
										<span fg={theme.success}>✓</span>
									) : isCurrent ? (
										<span fg={theme.cyan}>
											{spinnerFrames[spinnerIndex]}
										</span>
									) : (
										<span fg={theme.textDim}>○</span>
									)}
								</text>
								<text>
									<span
										fg={
											isDone
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

				{/* Status */}
				<text>
					<span fg={phaseColor[phase]}>
						{phase !== "done" && phase !== "error"
							? `${spinnerFrames[spinnerIndex]} `
							: ""}
						{phaseLabel[phase]}
					</span>
				</text>

				{/* Error display */}
				{phase === "error" && error && (
					<box
						border
						borderStyle="single"
						borderColor={theme.error}
						padding={2}
						width={60}
					>
						<text>
							<span fg={theme.error}>{error}</span>
						</text>
					</box>
				)}
			</box>

			{/* Footer hint */}
			<box paddingLeft={2} paddingBottom={1}>
				<text>
					<span fg={theme.textDim}>
						Press <span fg={theme.cyan}>Esc</span> to go back
					</span>
				</text>
			</box>
		</box>
	);
}
