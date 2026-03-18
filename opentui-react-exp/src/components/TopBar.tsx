import { theme } from "../types";

interface TopBarProps {
	title: string;
}

export function TopBar({ title }: TopBarProps) {
	return (
		<box width="100%" flexDirection="row" justifyContent="center" paddingTop={1} paddingBottom={1} backgroundColor={theme.bgDark}>
			<text>
				<span fg={theme.gold}>
					<strong>{title}</strong>
				</span>
			</text>
		</box>
	);
}
