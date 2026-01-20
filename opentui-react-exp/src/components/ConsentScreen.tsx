import { useState } from "react";
import { useKeyboard } from "@opentui/react";
import { theme } from "../types";

interface ConsentScreenProps {
  onContinue: (useLLM: boolean) => void;
  onBack: () => void;
}

type WizardStep = 1 | 2 | 3;

export function ConsentScreen({ onContinue, onBack }: ConsentScreenProps) {
  const [step, setStep] = useState<WizardStep>(1);
  const [selectedChoice, setSelectedChoice] = useState<0 | 1>(1); // Default to Basic

  useKeyboard((key) => {
    if (step === 3) {
      if (key.name === "left" || key.name === "right") {
        setSelectedChoice((prev) => (prev === 0 ? 1 : 0));
      }
      if (key.name === "return") {
        onContinue(selectedChoice === 0);
      }
    }

    if (key.name === "return" && step < 3) {
      setStep((prev) => (prev + 1) as WizardStep);
    }

    if (key.name === "escape" || key.name === "backspace") {
      if (step > 1) {
        setStep((prev) => (prev - 1) as WizardStep);
      } else {
        onBack();
      }
    }
  });

  const renderProgressBar = () => (
    <box flexDirection="row" justifyContent="center" gap={2} paddingTop={1} paddingBottom={1}>
      <text>
        <span fg={step >= 1 ? theme.gold : theme.textDim}>
          {step >= 1 ? "[x] Understand" : "[ ] Understand"}
        </span>
      </text>
      <text>
        <span fg={theme.textDim}>---</span>
      </text>
      <text>
        <span fg={step >= 2 ? theme.gold : theme.textDim}>
          {step >= 2 ? "[x] Privacy" : "[ ] Privacy"}
        </span>
      </text>
      <text>
        <span fg={theme.textDim}>---</span>
      </text>
      <text>
        <span fg={step >= 3 ? theme.gold : theme.textDim}>
          {step >= 3 ? "[x] Choose" : "[ ] Choose"}
        </span>
      </text>
    </box>
  );

  const renderStep1 = () => (
    <box flexDirection="column" alignItems="center" gap={2} padding={2}>
      <text>
        <span fg={theme.gold}>
          <strong>How would you like us to analyze your projects?</strong>
        </span>
      </text>

      <box flexDirection="column" alignItems="center" gap={1} marginTop={1}>
        <text>
          <span fg={theme.textPrimary}>
            You can choose AI-Enhanced analysis or Basic analysis.
          </span>
        </text>
        <text>
          <span fg={theme.textSecondary}>
            This choice controls whether project metadata is sent to OpenAI.
          </span>
        </text>
      </box>

      <box
        flexDirection="column"
        alignItems="center"
        marginTop={2}
        border
        borderStyle="single"
        borderColor={theme.bgLight}
        padding={2}
        width={86}
      >
        <box flexDirection="column" alignItems="center">
          <box
            border
            borderStyle="rounded"
            borderColor={theme.cyan}
            paddingLeft={3}
            paddingRight={3}
          >
            <text>
              <span fg={theme.cyan}>Your Code Projects</span>
            </text>
          </box>
        </box>

        <text><span fg={theme.textDim}>|</span></text>
        <text><span fg={theme.textDim}>v</span></text>

        <box flexDirection="row" gap={8} marginTop={1}>
          <box flexDirection="column" alignItems="center" gap={1}>
            <box
              border
              borderStyle="rounded"
              borderColor={theme.gold}
              paddingLeft={2}
              paddingRight={2}
              backgroundColor={theme.bgMedium}
            >
              <text>
                <span fg={theme.gold}>AI-Enhanced</span>
              </text>
            </box>
            <text><span fg={theme.textDim}>|</span></text>
            <text>
              <span fg={theme.textSecondary}>Sends metadata</span>
            </text>
            <text>
              <span fg={theme.textSecondary}>to OpenAI</span>
            </text>
            <text><span fg={theme.textDim}>|</span></text>
            <text><span fg={theme.textDim}>v</span></text>
            <text>
              <span fg={theme.success}>Detailed insights</span>
            </text>
          </box>

          <box flexDirection="column" justifyContent="center">
            <text>
              <span fg={theme.textDim}>OR</span>
            </text>
          </box>

          <box flexDirection="column" alignItems="center" gap={1}>
            <box
              border
              borderStyle="rounded"
              borderColor={theme.cyan}
              paddingLeft={2}
              paddingRight={2}
              backgroundColor={theme.bgMedium}
            >
              <text>
                <span fg={theme.cyan}>Basic</span>
              </text>
            </box>
            <text><span fg={theme.textDim}>|</span></text>
            <text>
              <span fg={theme.textSecondary}>Stays on your</span>
            </text>
            <text>
              <span fg={theme.textSecondary}>computer only</span>
            </text>
            <text><span fg={theme.textDim}>|</span></text>
            <text><span fg={theme.textDim}>v</span></text>
            <text>
              <span fg={theme.warning}>Basic insights</span>
            </text>
          </box>
        </box>

        <box flexDirection="row" justifyContent="center" marginTop={2}>
          <text><span fg={theme.textDim}>--------------------------------------</span></text>
        </box>
        <text><span fg={theme.textDim}>v</span></text>
        <box
          border
          borderStyle="rounded"
          borderColor={theme.success}
          paddingLeft={3}
          paddingRight={3}
          marginTop={1}
        >
          <text>
            <span fg={theme.success}>Your Professional Resume</span>
          </text>
        </box>
      </box>

      <box marginTop={2}>
        <text>
          <span fg={theme.textDim}>Press </span>
          <span fg={theme.gold}>Enter</span>
          <span fg={theme.textDim}> to learn about privacy, or </span>
          <span fg={theme.gold}>Esc</span>
          <span fg={theme.textDim}> to go back</span>
        </text>
      </box>
    </box>
  );

  const renderStep2 = () => (
    <box flexDirection="column" alignItems="center" gap={2} padding={2}>
      <text>
        <span fg={theme.gold}>
          <strong>Your Privacy Matters</strong>
        </span>
      </text>

      <text>
        <span fg={theme.textSecondary}>
          This is exactly what AI can and cannot see.
        </span>
      </text>

      <box flexDirection="row" gap={4} marginTop={2} justifyContent="center">
        <box
          flexDirection="column"
          border
          borderStyle="single"
          borderColor={theme.success}
          padding={2}
          width={42}
          gap={1}
        >
          <box flexDirection="row" gap={1} marginBottom={1}>
            <text>
              <span fg={theme.success}>OK</span>
            </text>
            <text>
              <span fg={theme.success}>
                <strong>AI Sees</strong>
              </span>
            </text>
          </box>

          <text>
            <span fg={theme.textDim}>[FILES]</span>
            <span fg={theme.textSecondary}> File names and folders</span>
          </text>
          <text>
            <span fg={theme.textDim}>[COMMITS]</span>
            <span fg={theme.textSecondary}> Commit messages</span>
          </text>
          <text>
            <span fg={theme.textDim}>[TECH]</span>
            <span fg={theme.textSecondary}> Technology names</span>
          </text>
          <text>
            <span fg={theme.textDim}>[STATS]</span>
            <span fg={theme.textSecondary}> Code statistics</span>
          </text>
        </box>

        <box
          flexDirection="column"
          border
          borderStyle="single"
          borderColor={theme.error}
          padding={2}
          width={42}
          gap={1}
        >
          <box flexDirection="row" gap={1} marginBottom={1}>
            <text>
              <span fg={theme.error}>NO</span>
            </text>
            <text>
              <span fg={theme.error}>
                <strong>AI Never Sees</strong>
              </span>
            </text>
          </box>

          <text>
            <span fg={theme.textDim}>[CODE]</span>
            <span fg={theme.textSecondary}> Your actual code</span>
          </text>
          <text>
            <span fg={theme.textDim}>[SECRETS]</span>
            <span fg={theme.textSecondary}> Passwords or API keys</span>
          </text>
          <text>
            <span fg={theme.textDim}>[PERSONAL]</span>
            <span fg={theme.textSecondary}> Personal information</span>
          </text>
          <text>
            <span fg={theme.textDim}>[DATA]</span>
            <span fg={theme.textSecondary}> Database contents</span>
          </text>
        </box>
      </box>

      <box
        flexDirection="column"
        alignItems="center"
        marginTop={2}
        border
        borderStyle="single"
        borderColor={theme.bgLight}
        padding={1}
        paddingLeft={3}
        paddingRight={3}
      >
        <text>
          <span fg={theme.textDim}>Provider: </span>
          <span fg={theme.cyan}>OpenAI GPT-4</span>
          <span fg={theme.textDim}> (data deleted after processing)</span>
        </text>
      </box>

      <box
        flexDirection="column"
        alignItems="center"
        marginTop={1}
      >
        <text>
          <span fg={theme.textSecondary}>
            Choosing AI means you explicitly allow sharing the items in "AI Sees".
          </span>
        </text>
      </box>

      <box marginTop={2}>
        <text>
          <span fg={theme.textDim}>Press </span>
          <span fg={theme.gold}>Enter</span>
          <span fg={theme.textDim}> to make your choice, or </span>
          <span fg={theme.gold}>Esc</span>
          <span fg={theme.textDim}> to go back</span>
        </text>
      </box>
    </box>
  );

  const renderStep3 = () => (
    <box flexDirection="column" alignItems="center" gap={3} padding={2}>
      <text>
        <span fg={theme.gold}>
          <strong>Make Your Choice</strong>
        </span>
      </text>

      <text>
        <span fg={theme.textSecondary}>
          Select how you'd like us to analyze your projects.
        </span>
      </text>

      <box flexDirection="row" gap={4} marginTop={2}>
        <box
          flexDirection="column"
          alignItems="center"
          gap={1}
          border
          borderStyle="rounded"
          borderColor={selectedChoice === 0 ? theme.gold : theme.bgLight}
          backgroundColor={selectedChoice === 0 ? theme.bgMedium : theme.bgDark}
          padding={2}
          paddingLeft={4}
          paddingRight={4}
          width={42}
        >
          <text>
            <span fg={selectedChoice === 0 ? theme.gold : theme.textDim}>
              <strong>AI-Enhanced Analysis</strong>
            </span>
          </text>
          <text>
            <span fg={theme.textDim}>--------------------</span>
          </text>
          <text>
            <span fg={theme.success}>+</span>
            <span fg={theme.textSecondary}> Sends metadata to OpenAI</span>
          </text>
          <text>
            <span fg={theme.success}>+</span>
            <span fg={theme.textSecondary}> Detailed skill detection</span>
          </text>
          <text>
            <span fg={theme.success}>+</span>
            <span fg={theme.textSecondary}> Better summaries</span>
          </text>
          <text>
            <span fg={theme.warning}>-</span>
            <span fg={theme.textSecondary}> Not fully private</span>
          </text>
          <box marginTop={1}>
            <text>
              <span fg={selectedChoice === 0 ? theme.gold : theme.textDim}>
                {selectedChoice === 0 ? ">> SELECTED" : "   Press Left to select"}
              </span>
            </text>
          </box>
        </box>

        <box
          flexDirection="column"
          alignItems="center"
          gap={1}
          border
          borderStyle="rounded"
          borderColor={selectedChoice === 1 ? theme.cyan : theme.bgLight}
          backgroundColor={selectedChoice === 1 ? theme.bgMedium : theme.bgDark}
          padding={2}
          paddingLeft={4}
          paddingRight={4}
          width={42}
        >
          <text>
            <span fg={selectedChoice === 1 ? theme.cyan : theme.textDim}>
              <strong>Basic Analysis</strong>
            </span>
          </text>
          <text>
            <span fg={theme.textDim}>--------------------</span>
          </text>
          <text>
            <span fg={theme.success}>+</span>
            <span fg={theme.textSecondary}> Stays on your computer</span>
          </text>
          <text>
            <span fg={theme.success}>+</span>
            <span fg={theme.textSecondary}> No data leaves your device</span>
          </text>
          <text>
            <span fg={theme.warning}>-</span>
            <span fg={theme.textSecondary}> Less detailed insights</span>
          </text>
          <box marginTop={1}>
            <text>
              <span fg={selectedChoice === 1 ? theme.cyan : theme.textDim}>
                {selectedChoice === 1 ? ">> SELECTED" : "   Press Right to select"}
              </span>
            </text>
          </box>
        </box>
      </box>

      <box marginTop={2} flexDirection="column" alignItems="center" gap={1}>
        <text>
          <span fg={theme.textDim}>Use Left/Right arrows to switch, Enter to confirm.</span>
        </text>
        <text>
          <span fg={theme.textDim}>Press Esc to review privacy details.</span>
        </text>
        <text>
          <span fg={theme.textDim}>You can change this later in Settings.</span>
        </text>
      </box>
    </box>
  );

  return (
    <box
      flexGrow={1}
      flexDirection="column"
      backgroundColor={theme.bgDark}
    >
      <box
        paddingLeft={2}
        paddingTop={1}
        paddingBottom={1}
        backgroundColor={theme.bgMedium}
      >
        <text>
          <span fg={theme.gold}>
            <strong>Before We Begin</strong>
          </span>
          <span fg={theme.textDim}> - Understanding Your Options</span>
        </text>
      </box>

      {renderProgressBar()}

      <box flexGrow={1} justifyContent="center" alignItems="center">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </box>
    </box>
  );
}
