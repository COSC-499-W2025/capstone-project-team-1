import { createCliRenderer } from "@opentui/core";
import { createRoot, useRenderer, useKeyboard } from "@opentui/react";
import { useState } from "react";

import { type Screen, type KeyAction, theme } from "./types";
import { mockProjects, mockResumeData } from "./data/mockProjects";

import { BottomBar } from "./components/BottomBar";
import { Landing } from "./components/Landing";
import { ConsentScreen } from "./components/ConsentScreen";
import { FileUpload } from "./components/FileUpload";
import { ProjectList } from "./components/ProjectList";
import { Analysis } from "./components/Analysis";
import { ResumePreview } from "./components/ResumePreview";

// Key actions for each screen
const screenActions: Record<Screen, KeyAction[]> = {
  landing: [
    { key: "Enter", label: "Get Started" },
    { key: "Esc", label: "Exit" },
  ],
  consent: [
    { key: "←/→", label: "Navigate" },
    { key: "Enter", label: "Confirm" },
    { key: "Esc", label: "Back" },
  ],
  "file-upload": [
    { key: "Enter", label: "Continue" },
    { key: "Esc", label: "Back" },
  ],
  "project-list": [
    { key: "↑/↓", label: "Navigate" },
    { key: "Enter", label: "Analyze" },
    { key: "Esc", label: "Back" },
  ],
  analysis: [
    { key: "", label: "Processing..." },
  ],
  "resume-preview": [
    { key: "↑/↓", label: "Scroll" },
    { key: "r", label: "Restart" },
    { key: "Esc", label: "Exit" },
  ],
};

function App() {
  const renderer = useRenderer();
  const [screen, setScreen] = useState<Screen>("landing");
  const [filePath, setFilePath] = useState("");
  const [useLLM, setUseLLM] = useState(false);

  // Global keyboard handler
  useKeyboard((key) => {
    // Exit on Ctrl+C
    if (key.ctrl && key.name === "c") {
      renderer.destroy();
      return;
    }

    switch (screen) {
      case "landing":
        if (key.name === "return") {
          setScreen("consent");
        } else if (key.name === "escape") {
          renderer.destroy();
        }
        break;

      case "consent":
        // Consent wizard handles its own keyboard events
        break;

      case "file-upload":
        if (key.name === "return") {
          setScreen("project-list");
        } else if (key.name === "escape") {
          setScreen("consent");
        }
        break;

      case "project-list":
        if (key.name === "return") {
          setScreen("analysis");
        } else if (key.name === "escape") {
          setScreen("file-upload");
        }
        break;

      case "analysis":
        // No keyboard actions during analysis
        break;

      case "resume-preview":
        if (key.name === "r") {
          setScreen("landing");
        } else if (key.name === "escape") {
          renderer.destroy();
        }
        break;
    }
  });

  const renderScreen = () => {
    switch (screen) {
      case "landing":
        return <Landing onGetStarted={() => setScreen("consent")} />;

      case "consent":
        return (
          <ConsentScreen
            onContinue={(llmChoice) => {
              setUseLLM(llmChoice);
              setScreen("file-upload");
            }}
            onBack={() => setScreen("landing")}
          />
        );

      case "file-upload":
        return (
          <FileUpload
            onSubmit={(path) => {
              setFilePath(path);
              setScreen("project-list");
            }}
            onBack={() => setScreen("consent")}
          />
        );

      case "project-list":
        return (
          <ProjectList
            projects={mockProjects}
            onContinue={() => setScreen("analysis")}
            onBack={() => setScreen("file-upload")}
          />
        );

      case "analysis":
        return (
          <Analysis
            onComplete={() => setScreen("resume-preview")}
            onBack={() => setScreen("project-list")}
          />
        );

      case "resume-preview":
        return (
          <ResumePreview
            data={mockResumeData}
            onBack={() => setScreen("analysis")}
            onRestart={() => setScreen("landing")}
          />
        );
    }
  };

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      backgroundColor={theme.bgDark}
    >
      {/* Main content area */}
      <box flexGrow={1}>
        {renderScreen()}
      </box>

      {/* Bottom bar with keyboard shortcuts */}
      <BottomBar actions={screenActions[screen]} />
    </box>
  );
}

const renderer = await createCliRenderer();
createRoot(renderer).render(<App />);
