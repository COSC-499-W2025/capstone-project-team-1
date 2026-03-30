import type { KeyAction, Screen } from "../types";
import { theme } from "../types";

export interface Breadcrumb {
	screen: Screen;
	label: string;
	visited: boolean;
}

interface BottomBarProps {
	actions: KeyAction[];
	hint?: string;
	breadcrumbs?: Breadcrumb[];
	currentScreen?: Screen;
	onNavigate?: (screen: Screen) => void;
	onForward?: () => void;
	forwardLabel?: string;
}

export function BottomBar({
	actions,
	hint,
	breadcrumbs,
	currentScreen,
	onNavigate,
	onForward,
	forwardLabel = "Continue",
}: BottomBarProps) {
	return (
		<box
			width="100%"
			flexDirection="row"
			justifyContent="space-between"
			alignItems="center"
			paddingLeft={2}
			paddingRight={2}
			paddingTop={1}
			paddingBottom={1}
			backgroundColor={theme.bgDark}
		>
			<box flexDirection="row" alignItems="center">
				{breadcrumbs?.map((crumb, i) => {
					const isCurrent = crumb.screen === currentScreen;
					const canClick = crumb.visited && !isCurrent;
					const color = isCurrent
						? theme.gold
						: crumb.visited
							? theme.textSecondary
							: theme.textDim;

					return (
						<box key={crumb.screen} flexDirection="row">
							<box
								// biome-ignore lint/a11y/noStaticElementInteractions: breadcrumb nav
								onMouseDown={
									canClick ? () => onNavigate?.(crumb.screen) : undefined
								}
							>
								<text>
									<span fg={color}>
										{isCurrent ? <strong>{crumb.label}</strong> : crumb.label}
									</span>
								</text>
							</box>
							{i < breadcrumbs.length - 1 ? (
								<text>
									<span fg={theme.textDim}>{" › "}</span>
								</text>
							) : null}
						</box>
					);
				})}
			</box>

			<box flexGrow={1} paddingLeft={breadcrumbs?.length ? 2 : 0} paddingRight={2}>
				{hint ? (
					<text>
						<span fg={theme.textDim}>{hint}</span>
					</text>
				) : null}
			</box>

			<box flexDirection="row" alignItems="center" gap={3}>
				{actions.map((action) => (
					<box key={`${action.key}-${action.label}`} flexDirection="row" gap={1}>
						<text>
							<span fg={theme.goldDark}>{action.key}</span>
						</text>
						<text>
							<span fg={theme.textDim}>{action.label}</span>
						</text>
					</box>
				))}
				{onForward ? (
					/* biome-ignore lint/a11y/noStaticElementInteractions: footer CTA */
					<box onMouseDown={onForward}>
						<text>
							<span fg={theme.gold}>
								{forwardLabel}
								{" ›"}
							</span>
						</text>
					</box>
				) : null}
			</box>
		</box>
	);
}
