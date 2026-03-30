import { theme } from "../types";

interface TopBarProps {
	step?: string;
	title: string;
	description?: string;
}

export function TopBar({ step, title, description }: TopBarProps) {
	return (
		<box
			width="100%"
			flexDirection="column"
			paddingTop={1}
			paddingBottom={1}
			backgroundColor={theme.bgDark}
		>
			<box width="100%" flexDirection="row" justifyContent="center">
				<text>
					{step ? (
						<span fg={theme.gold}>
							<strong>{step}</strong>
						</span>
					) : null}
					{step ? <span fg={theme.textDim}>{" | "}</span> : null}
					<span fg={step ? theme.textPrimary : theme.gold}>
						<strong>{title}</strong>
					</span>
				</text>
			</box>
			{description ? (
				<box width="100%" flexDirection="row" justifyContent="center">
					<text>
						<span fg={theme.textDim}>{description}</span>
					</text>
				</box>
			) : null}
		</box>
	);
}
