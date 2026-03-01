import React from "react";
import RuneSignUp from "../rune-output/SignUp";
import VibeSignUp from "../vibe-output/SignUp";
import FigmaDevSignUp from "../figma-dev-output/SignUp";

export default {
  title: "Figma Comparison",
};

export const RuneOutput = () => <RuneSignUp />;
RuneOutput.storyName = "Rune Output";

export const VibeOutput = () => <VibeSignUp />;
VibeOutput.storyName = "VibeFigma Output";

export const FigmaDevOutput = () => <FigmaDevSignUp />;
FigmaDevOutput.storyName = "Figma Dev Mode Output";

export const SideBySide = () => (
  <div
    style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr 1fr",
      gap: 24,
      padding: 24,
      minHeight: "100vh",
      background: "#f9fafb",
    }}
  >
    <div>
      <h2
        style={{
          fontSize: 16,
          fontWeight: 600,
          marginBottom: 12,
          color: "#374151",
        }}
      >
        Rune (figma-to-react)
      </h2>
      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <RuneSignUp />
      </div>
    </div>
    <div>
      <h2
        style={{
          fontSize: 16,
          fontWeight: 600,
          marginBottom: 12,
          color: "#374151",
        }}
      >
        VibeFigma
      </h2>
      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <VibeSignUp />
      </div>
    </div>
    <div>
      <h2
        style={{
          fontSize: 16,
          fontWeight: 600,
          marginBottom: 12,
          color: "#374151",
        }}
      >
        Figma Dev Mode
      </h2>
      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <FigmaDevSignUp />
      </div>
    </div>
  </div>
);
SideBySide.storyName = "Side by Side (3-way)";

export const RuneVsFigmaDev = () => (
  <div
    style={{
      display: "grid",
      gridTemplateColumns: "1fr 1fr",
      gap: 32,
      padding: 24,
      minHeight: "100vh",
    }}
  >
    <div>
      <h2
        style={{
          fontSize: 18,
          fontWeight: 600,
          marginBottom: 16,
          color: "#374151",
        }}
      >
        Rune (figma-to-react)
      </h2>
      <div
        style={{
          border: "1px solid #e5e7eb",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <RuneSignUp />
      </div>
    </div>
    <div>
      <h2
        style={{
          fontSize: 18,
          fontWeight: 600,
          marginBottom: 16,
          color: "#dc2626",
        }}
      >
        Figma Dev Mode (target quality)
      </h2>
      <div
        style={{
          border: "2px solid #dc2626",
          borderRadius: 8,
          overflow: "hidden",
        }}
      >
        <FigmaDevSignUp />
      </div>
    </div>
  </div>
);
RuneVsFigmaDev.storyName = "Rune vs Figma Dev Mode";
