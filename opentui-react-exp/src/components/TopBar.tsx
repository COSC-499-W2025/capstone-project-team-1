import { theme } from "../types";

interface TopBarProps {
	title: string;
	description?: string;
}

export function TopBar({ title, description }: TopBarProps) {
	return (
		<box width="100%" flexDirection="column" gap={1} backgroundColor={theme.bgDark}>
			<box flexDirection="row" justifyContent="center" paddingTop={1}>
				<text>
					<span fg={theme.gold}>
						<strong>{title}</strong>
					</span>
				</text>
			</box>
			{description ? (
				<box paddingLeft={4} paddingRight={4} paddingBottom={2} alignItems="center">
					<text>
						<span fg={theme.textSecondary}>{description}</span>
					</text>
				</box>
			) : null}
		</box>
	);
}
