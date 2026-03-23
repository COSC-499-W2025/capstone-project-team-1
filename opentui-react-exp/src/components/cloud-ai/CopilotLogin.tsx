import { useEffect, useRef, useState } from "react";
import { useKeyboard } from "@opentui/react";
import { fetchGitHubUser, loginCopilot, type GitHubUser } from "../../agent";
import { theme } from "../../types";
import { TopBar } from "../TopBar";
import { ModelList, type ModelListResult } from "./ModelList";
import { openInBrowser, spinnerFrames } from "./shared";

interface CopilotLoginProps {
	onComplete: (result: ModelListResult) => void;
	onBack: () => void;
}

export function CopilotLogin({ onComplete, onBack }: CopilotLoginProps) {
	const [deviceUrl, setDeviceUrl] = useState<string | null>(null);
	const [deviceCode, setDeviceCode] = useState<string | null>(null);
	const [loginProgress, setLoginProgress] = useState<string | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loggedIn, setLoggedIn] = useState(false);
	const [ghUser, setGhUser] = useState<GitHubUser | null>(null);
	const [spinnerIndex, setSpinnerIndex] = useState(0);
	const abortRef = useRef<AbortController | null>(null);

	useEffect(() => {
		if (error || loggedIn) return;
		const interval = setInterval(() => {
			setSpinnerIndex((i) => (i + 1) % spinnerFrames.length);
		}, 80);
		return () => clearInterval(interval);
	}, [error, loggedIn]);

	useEffect(() => {
		const abortController = new AbortController();
		abortRef.current = abortController;

		(async () => {
			try {
				await loginCopilot({
					onAuth: (info) => {
						setDeviceUrl(info.url);
						openInBrowser(info.url);
						if (info.instructions) {
							const code = info.instructions.replace("Enter code: ", "");
							setDeviceCode(code);
						}
					},
					onPrompt: async () => "",
					onProgress: (message) => setLoginProgress(message),
					signal: abortController.signal,
				});
				// Fetch user profile after successful login
				try {
					const user = await fetchGitHubUser();
					setGhUser(user);
				} catch {
					// Non-fatal — proceed without user info
				}
				setLoggedIn(true);
			} catch (err) {
				if (abortController.signal.aborted) return;
				setError(err instanceof Error ? err.message : String(err));
			}
		})();

		return () => {
			abortController.abort();
		};
	}, []);

	useKeyboard((key) => {
		// ModelList handles its own keyboard when logged in
		if (loggedIn) return;

		if (key.name === "escape") {
			abortRef.current?.abort();
			onBack();
		}
	});

	if (loggedIn) {
		return (
			<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
				<TopBar
					title="GitHub Copilot Login"
					description="Sign in with your GitHub account to use AI-powered resume generation."
				/>
				<ModelList
					successMessage="✓ Successfully logged in to GitHub Copilot!"
					user={ghUser}
					onSelect={onComplete}
					onBack={onBack}
				/>
			</box>
		);
	}

	return (
		<box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
			<TopBar
				title="GitHub Copilot Login"
				description="Sign in with your GitHub account to use AI-powered resume generation."
			/>

			<box
				flexGrow={1}
				flexDirection="column"
				alignItems="center"
				justifyContent="center"
				gap={3}
			>
				{error ? (
					<box
						border
						borderStyle="single"
						borderColor={theme.error}
						padding={2}
						width={60}
					>
						<text wrap selectable>
							<span fg={theme.error}>{error}</span>
						</text>
					</box>
				) : deviceUrl && deviceCode ? (
					<>
						<text>
							<span fg={theme.success}>
								✓ Opened GitHub in your browser
							</span>
						</text>

						<box flexDirection="column" alignItems="center" gap={1}>
							<text>
								<span fg={theme.textDim}>
									If it didn't open, go to:
								</span>
							</text>
							<text selectable>
								<span fg={theme.cyan}>
									<strong><u>{deviceUrl}</u></strong>
								</span>
							</text>
						</box>

						<box
							border
							borderStyle="rounded"
							borderColor={theme.gold}
							paddingLeft={4}
							paddingRight={4}
							paddingTop={1}
							paddingBottom={1}
						>
							<text selectable>
								<span fg={theme.textDim}>Enter code: </span>
								<span fg={theme.gold}>
									<strong>{deviceCode}</strong>
								</span>
							</text>
						</box>

						<text>
							<span fg={theme.cyan}>
								{spinnerFrames[spinnerIndex]} Waiting for
								authorization...
							</span>
						</text>

						{loginProgress && (
							<text>
								<span fg={theme.textDim}>{loginProgress}</span>
							</text>
						)}
					</>
				) : (
					<text>
						<span fg={theme.cyan}>
							{spinnerFrames[spinnerIndex]} Connecting to GitHub...
						</span>
					</text>
				)}

				<box
					border
					borderStyle="rounded"
					borderColor={theme.textDim}
					padding={1}
					width={55}
				>
					<text wrap>
						<span fg={theme.textDim}>
							Students with GitHub Education get free access to
							Copilot, which includes Claude and GPT models at no
							cost.
						</span>
					</text>
				</box>
			</box>
		</box>
	);
}
