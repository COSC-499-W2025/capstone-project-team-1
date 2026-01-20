import { useState } from "react";
import { TopBar } from "./TopBar";
import { theme } from "../types";

interface FileUploadProps {
  onSubmit: (path: string) => void;
  onBack: () => void;
}

export function FileUpload({ onSubmit, onBack }: FileUploadProps) {
  const [filePath, setFilePath] = useState("");
  const [isValid, setIsValid] = useState(false);

  const handleChange = (value: string) => {
    setFilePath(value);
    // Simple validation: check if ends with .zip
    setIsValid(value.trim().endsWith(".zip"));
  };

  const handleSubmit = () => {
    if (isValid) {
      onSubmit(filePath);
    }
  };

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      backgroundColor={theme.bgDark}
    >
      <TopBar 
        step="Step 1" 
        title="Select Your Projects" 
        description="Enter the path to your zip file containing git repositories"
      />

      {/* Main content */}
      <box
        flexGrow={1}
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        gap={3}
      >
        {/* Icon/illustration */}
        <box flexDirection="column" alignItems="center">
          <text>
            <span fg={theme.cyan}>
              ┌─────────────────┐{"\n"}
              │   📁  →  📄    │{"\n"}
              │  .zip   resume │{"\n"}
              └─────────────────┘
            </span>
          </text>
        </box>

        {/* Instructions */}
        <box flexDirection="column" alignItems="center" gap={1}>
          <text>
            <span fg={theme.textPrimary}>
              Enter the path to your zip file containing git repositories
            </span>
          </text>
          <text>
            <span fg={theme.textDim}>
              We'll analyze your code and extract skills, technologies, and project info
            </span>
          </text>
        </box>

        {/* Input field */}
        <box flexDirection="column" alignItems="center" gap={1}>
          <box flexDirection="row" alignItems="center" gap={2}>
            <text>
              <span fg={theme.goldDark}>Path:</span>
            </text>
            <input
              value={filePath}
              onChange={handleChange}
              placeholder="/path/to/your/projects.zip"
              width={50}
              focused
              backgroundColor={theme.bgMedium}
              textColor={theme.textPrimary}
              cursorColor={theme.cyan}
              placeholderColor={theme.textDim}
            />
          </box>
          
          {filePath && (
            <text>
              {isValid ? (
                <span fg={theme.success}>✓ Valid zip file path</span>
              ) : (
                <span fg={theme.error}>✗ Please enter a .zip file path</span>
              )}
            </text>
          )}
        </box>

        {/* Submit button */}
        <box
          border
          borderStyle="rounded"
          borderColor={isValid ? theme.cyan : theme.textDim}
          backgroundColor={isValid ? theme.cyanDim : theme.bgMedium}
          paddingLeft={3}
          paddingRight={3}
          paddingTop={1}
          paddingBottom={1}
          onMouseDown={handleSubmit}
        >
          <text>
            <span fg={isValid ? theme.textPrimary : theme.textDim}>
              <strong>Analyze Projects</strong>
            </span>
          </text>
        </box>

        {/* Demo hint */}
        <text>
          <span fg={theme.textDim}>
            Demo: Press Enter to continue with mock data
          </span>
        </text>
      </box>
    </box>
  );
}
