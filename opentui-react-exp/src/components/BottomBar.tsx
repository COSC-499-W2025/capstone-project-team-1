import type { KeyAction, Screen } from "../types";
import { theme } from "../types";

export interface Breadcrumb {
	screen: Screen;
	label: string;
	visited: boolean;
}

interface BottomBarProps {
	actions: KeyAction[];
	breadcrumbs?: Breadcrumb[];
	currentScreen?: Screen;
	onNavigate?: (screen: Screen) => void;
	onForward?: () => void;
	forwardLabel?: string;
}

export function BottomBar({ actions, breadcrumbs, currentScreen, onNavigate, onForward, forwardLabel = "Continue" }: BottomBarProps) {
	return (
		<box
			width="100%"
			flexDirection="row"
			alignItems="center"
			paddingLeft={2}
			paddingRight={2}
			height={1}
			backgroundColor={theme.bgDark}
		>
			{/* Left: breadcrumbs */}
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
							{/* biome-ignore lint/a11y/noStaticElementInteractions: breadcrumb nav */}
							<box
								onMouseDown={canClick ? () => onNavigate?.(crumb.screen) : undefined}
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

			{/* Spacer */}
			<box flexGrow={1} />

			{/* Right: keyboard shortcuts + forward button */}
			<box flexDirection="row" alignItems="center" gap={3}>
				{actions.map((action, index) => (
					<box key={index} flexDirection="row" gap={1}>
						<text>
							<span fg={theme.goldDark}>{action.key}</span>
						</text>
						<text>
							<span fg={theme.textDim}>{action.label}</span>
						</text>
					</box>
				))}
				{onForward ? (
					<box onMouseDown={onForward}>
						<text>
							<span fg={theme.gold}>{forwardLabel}{" ›"}</span>
						</text>
					</box>
				) : null}
			</box>
		</box>
	);
}
