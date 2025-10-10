"use client";

import { useState } from "react";

interface StyleOption {
  name: string;
  description: string;
  emoji: string;
}

interface StyleSelectorProps {
  onClose: () => void;
  onConfirm: (style: { style_name: string; keep_original?: boolean }) => void;
}

const DESIGN_STYLES: StyleOption[] = [
  {
    name: "Bohemian",
    description: "Eclectic, layered textures, rich colors, global influences",
    emoji: "🌿",
  },
  {
    name: "Scandinavian",
    description: "Minimalist, light colors, natural materials, cozy hygge",
    emoji: "❄️",
  },
  {
    name: "Contemporary",
    description: "Clean lines, neutral palette, sleek modern furniture",
    emoji: "🏢",
  },
  {
    name: "Coastal",
    description: "Light and airy, whites and blues, beach-inspired",
    emoji: "🌊",
  },
  {
    name: "Modern",
    description: "Geometric shapes, monochromatic, minimalist cutting-edge",
    emoji: "⚡",
  },
  {
    name: "Art Deco",
    description: "Luxurious, geometric patterns, rich jewel tones, glamour",
    emoji: "💎",
  },
];

export function StyleSelector({ onClose, onConfirm }: StyleSelectorProps) {
  const [selectedStyle, setSelectedStyle] = useState<string | null>(null);

  const handleConfirm = () => {
    console.log("✅ StyleSelector handleConfirm clicked, selectedStyle:", selectedStyle);
    
    if (!selectedStyle) {
      alert("Please select a style first");
      return;
    }

    let styleData;
    if (selectedStyle === "original") {
      styleData = { style_name: "Original", keep_original: true };
    } else if (selectedStyle === "ai-decide") {
      styleData = { style_name: "Let AI Decide" };
    } else {
      styleData = { style_name: selectedStyle };
    }
    
    console.log("📤 StyleSelector calling onConfirm with:", styleData);
    onConfirm(styleData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-6 z-10">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                🎨 Choose Design Style
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Select a style for your AI-generated visualization
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-2xl"
            >
              ×
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Keep Original Option */}
          <button
            onClick={() => setSelectedStyle("original")}
            className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
              selectedStyle === "original"
                ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900 dark:text-white text-lg">
                  ✨ Keep Original Style
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Maintain the existing design aesthetic of your room
                </p>
              </div>
              {selectedStyle === "original" && (
                <div className="text-purple-600 dark:text-purple-400 text-2xl">
                  ✓
                </div>
              )}
            </div>
          </button>

          {/* AI Decide Option */}
          <button
            onClick={() => setSelectedStyle("ai-decide")}
            className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
              selectedStyle === "ai-decide"
                ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="font-semibold text-gray-900 dark:text-white text-lg">
                  🤖 Let AI Decide
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Let AI choose the best style to complement your product and
                  room
                </p>
              </div>
              {selectedStyle === "ai-decide" && (
                <div className="text-purple-600 dark:text-purple-400 text-2xl">
                  ✓
                </div>
              )}
            </div>
          </button>

          {/* Design Styles Grid */}
          <div className="pt-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Or choose a specific style:
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {DESIGN_STYLES.map((style) => (
                <button
                  key={style.name}
                  onClick={() => setSelectedStyle(style.name)}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    selectedStyle === style.name
                      ? "border-purple-500 bg-purple-50 dark:bg-purple-900/20"
                      : "border-gray-200 dark:border-gray-700 hover:border-purple-300 dark:hover:border-purple-700"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-2xl">{style.emoji}</span>
                        <p className="font-semibold text-gray-900 dark:text-white">
                          {style.name}
                        </p>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {style.description}
                      </p>
                    </div>
                    {selectedStyle === style.name && (
                      <div className="text-purple-600 dark:text-purple-400 text-xl ml-2">
                        ✓
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 p-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={!selectedStyle}
            className={`px-6 py-2 rounded-lg font-semibold transition-colors ${
              selectedStyle
                ? "bg-purple-600 text-white hover:bg-purple-700"
                : "bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed"
            }`}
            title={!selectedStyle ? "Please select a style first" : "Confirm your style selection"}
          >
            {selectedStyle ? `Confirm "${selectedStyle === "original" ? "Original Style" : selectedStyle === "ai-decide" ? "Let AI Decide" : selectedStyle}"` : "Select a Style"}
          </button>
        </div>
      </div>
    </div>
  );
}

