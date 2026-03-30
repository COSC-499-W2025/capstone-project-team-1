import { theme } from "../types";

interface TopBarProps {
	step?: string;
	title: string;
	description?: string;
}

export function TopBar({ step, title, description }: TopBarProps) {
	// Fixed height: 1 padding + 1 title + (1 description if present) + 1 padding
	const barHeight = description ? 4 : 3;

	return (
		<box
			width="100%"
			height={barHeight}
			flexDirection="column"
			paddingTop={1}
			paddingBottom={1}
			backgroundColor={theme.bgDark}
			overflow="hidden"
			flexShrink={0}
		>
			<box
				width="100%"
				height={1}
				flexDirection="row"
				justifyContent="center"
				paddingLeft={2}
				paddingRight={2}
				overflow="hidden"
			>
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
				<box
					width="100%"
					height={1}
					flexDirection="row"
					justifyContent="center"
					paddingLeft={4}
					paddingRight={4}
					overflow="hidden"
				>
					<text>
						<span fg={theme.textDim}>{description}</span>
					</text>
				</box>
			) : null}
		</box>
	);
}
