import { theme } from "../types";

interface TopBarProps {
  step: string;
  title: string;
  description?: string;
}

export function TopBar({ step, title, description }: TopBarProps) {
  return (
    <box
      width="100%"
      flexDirection="column"
      justifyContent="center"
      alignItems="center"
      gap={0}
      padding={1}
      backgroundColor={theme.bgDark}
    >
      <box flexDirection="row" gap={1}>
        <text>
          <span fg={theme.gold}>
            <strong>{step}</strong>
          </span>
        </text>
        <text>
          <span fg={theme.textDim}>|</span>
        </text>
        <text>
          <span fg={theme.textPrimary}>
            <strong>{title}</strong>
          </span>
        </text>
      </box>
      
      {description && (
        <text>
          <span fg={theme.textDim}>{description}</span>
        </text>
      )}
    </box>
  );
}
