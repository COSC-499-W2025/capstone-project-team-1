import { useState } from "react";
import { useKeyboard } from "@opentui/react";
import { TopBar } from "./TopBar";
import { theme } from "../types";

interface ConsentScreenProps {
  onContinue: (useLLM: boolean) => void;
  onBack: () => void;
}

type Selection = "cloud" | "offline";

export function ConsentScreen({ onContinue, onBack }: ConsentScreenProps) {
  const [selected, setSelected] = useState<Selection>("offline");

  useKeyboard((key) => {
    if (key.name === "left" || key.name === "right") {
      setSelected((prev) => (prev === "cloud" ? "offline" : "cloud"));
    }
    if (key.name === "return") {
      onContinue(selected === "cloud");
    }
    if (key.name === "escape") {
      onBack();
    }
  });

  const isCloudSelected = selected === "cloud";
  const isOfflineSelected = selected === "offline";

  return (
    <box flexGrow={1} flexDirection="column" backgroundColor={theme.bgDark}>
      <TopBar 
        step="Privacy" 
        title="Settings" 
        description="Choose how your project metadata is analyzed."
      />

      {/* Main split-screen container */}
      <box flexGrow={1} flexDirection="row" gap={1} paddingLeft={2} paddingRight={2} paddingBottom={2}>
        {/* Cloud Analysis Panel */}
        <box
          flexGrow={1}
          flexDirection="column"
          padding={2}
          border
          borderStyle={isCloudSelected ? "double" : "single"}
          borderColor={isCloudSelected ? theme.gold : theme.textDim}
          backgroundColor={isCloudSelected ? theme.bgMedium : theme.bgDark}
          gap={1}
        >
          <text>
            <span fg={isCloudSelected ? theme.gold : theme.textSecondary}>
              <strong>Cloud Analysis</strong>
            </span>
          </text>

          <box flexDirection="column" gap={1}>
            <text>
              <span fg={theme.textDim}>Pros:</span>
            </text>
            <text>
              <span fg={theme.success}>  + Enhanced skill detection</span>
            </text>
            <text>
              <span fg={theme.success}>  + Smarter summaries</span>
            </text>
            <text>
              <span fg={theme.success}>  + Better project insights</span>
            </text>
          </box>

          <box flexDirection="column" gap={1}>
            <text>
              <span fg={theme.textDim}>Cons:</span>
            </text>
            <text>
              <span fg={theme.warning}>  - Requires network</span>
            </text>
            <text>
              <span fg={theme.warning}>  - Metadata sent to OpenAI</span>
            </text>
            <text>
              <span fg={theme.warning}>  - Less privacy</span>
            </text>
          </box>

          <box marginTop={1} paddingTop={1}>
            <text>
              <span fg={theme.textDim}>─────────────────────────</span>
            </text>
            <text>
              <span fg={theme.textDim}>
                Sends: file names, commit messages, technology names
              </span>
            </text>
          </box>
        </box>

        {/* Offline Analysis Panel */}
        <box
          flexGrow={1}
          flexDirection="column"
          padding={2}
          border
          borderStyle={isOfflineSelected ? "double" : "single"}
          borderColor={isOfflineSelected ? theme.gold : theme.textDim}
          backgroundColor={isOfflineSelected ? theme.bgMedium : theme.bgDark}
          gap={1}
        >
          <text>
            <span fg={isOfflineSelected ? theme.gold : theme.textSecondary}>
              <strong>Offline</strong>
            </span>
          </text>

          <box flexDirection="column" gap={1}>
            <text>
              <span fg={theme.textDim}>Pros:</span>
            </text>
            <text>
              <span fg={theme.success}>  + All processing local</span>
            </text>
            <text>
              <span fg={theme.success}>  + Complete privacy</span>
            </text>
            <text>
              <span fg={theme.success}>  + No data transmitted</span>
            </text>
          </box>

          <box flexDirection="column" gap={1}>
            <text>
              <span fg={theme.textDim}>Cons:</span>
            </text>
            <text>
              <span fg={theme.warning}>  - Pattern-based analysis</span>
            </text>
            <text>
              <span fg={theme.warning}>  - Less detailed insights</span>
            </text>
            <text>
              <span fg={theme.warning}>  - Basic skill detection</span>
            </text>
          </box>

          <box marginTop={1} paddingTop={1}>
            <text>
              <span fg={theme.textDim}>─────────────────────────</span>
            </text>
            <text>
              <span fg={theme.textDim}>
                All analysis happens on your machine. Zero external calls.
              </span>
            </text>
          </box>
        </box>
      </box>

      {/* Demo Mode Banner */}
      <box height={3} border borderStyle="single" borderColor={theme.error} paddingLeft={2} paddingRight={2} paddingTop={1} paddingBottom={1}>
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
