'use client';

import { Check, Palette, X } from 'lucide-react';
import { useState } from 'react';

interface ColorPalette {
  name: string;
  colors: string[];
  description?: string;
}

interface ColorSchemeSelectorProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (palette: ColorPalette | null) => void;
  currentColors?: string[];
}

const predefinedPalettes: ColorPalette[] = [
  {
    name: "Let AI Decide",
    colors: ["#A8DADC", "#457B9D", "#1D3557", "#F1FAEE", "#E63946"],
    description: "AI will choose the best colors"
  },
  {
    name: "Greens",
    colors: ["#D4E09B", "#A4C3A2", "#6B9080", "#4A7C59", "#2D3E40"],
    description: "Natural and calming greens"
  },
  {
    name: "High Reds",
    colors: ["#FFCDB2", "#FFB4A2", "#E5989B", "#B5838D", "#6D6875"],
    description: "Warm and energetic reds"
  },
  {
    name: "Warm Reds",
    colors: ["#FFDDD2", "#EEA990", "#C97064", "#A44A3F", "#8B2635"],
    description: "Cozy and inviting warm tones"
  },
  {
    name: "Deep Blues",
    colors: ["#CAF0F8", "#90E0EF", "#00B4D8", "#0077B6", "#03045E"],
    description: "Cool and sophisticated blues"
  },
  {
    name: "Modern Neutrals",
    colors: ["#F8F9FA", "#E9ECEF", "#ADB5BD", "#6C757D", "#212529"],
    description: "Timeless neutral palette"
  },
  {
    name: "Earthy Tones",
    colors: ["#E9C46A", "#F4A261", "#E76F51", "#A8763E", "#6F4E37"],
    description: "Warm earth-inspired colors"
  },
  {
    name: "Pastels",
    colors: ["#FFE5E5", "#FFEAA7", "#DFE6E9", "#FADBD8", "#E0BBE4"],
    description: "Soft and gentle pastels"
  }
];

export default function ColorSchemeSelector({
  isOpen,
  onClose,
  onConfirm,
  currentColors
}: ColorSchemeSelectorProps) {
  const [selectedPalette, setSelectedPalette] = useState<ColorPalette | null>(null);
  const [keepOriginal, setKeepOriginal] = useState(false);

  if (!isOpen) return null;

  const handleConfirm = () => {
    if (keepOriginal) {
      onConfirm(null); // null means keep original colors
    } else {
      onConfirm(selectedPalette || predefinedPalettes[0]); // Default to "Let AI Decide"
    }
    // Don't call onClose() here - let the parent handle it
    // This allows the parent to transition to the next modal without losing state
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-3xl w-full mx-4 max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Palette className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Choose Colors
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                Select a color scheme for your AI-generated design
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {/* Keep Original Option */}
          <div className="mb-6">
            <button
              onClick={() => {
                setKeepOriginal(!keepOriginal);
                setSelectedPalette(null);
              }}
              className={`w-full p-4 rounded-xl border-2 transition-all ${
                keepOriginal 
                  ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20' 
                  : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                    keepOriginal ? 'border-purple-500 bg-purple-500' : 'border-gray-300 dark:border-gray-600'
                  }`}>
                    {keepOriginal && <Check className="w-3 h-3 text-white" />}
                  </div>
                  <div className="text-left">
                    <p className="font-medium text-gray-900 dark:text-white">
                      Keep Original Colors
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Maintain the current color scheme of your space
                    </p>
                  </div>
                </div>
                {currentColors && (
                  <div className="flex gap-1">
                    {currentColors.slice(0, 5).map((color, idx) => (
                      <div
                        key={idx}
                        className="w-8 h-8 rounded-md border border-gray-200 dark:border-gray-700"
                        style={{ backgroundColor: color }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-white dark:bg-gray-900 text-sm text-gray-500 dark:text-gray-400">
                Or choose a new palette
              </span>
            </div>
          </div>

          {/* Color Palettes Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {predefinedPalettes.map((palette) => (
              <button
                key={palette.name}
                onClick={() => {
                  setSelectedPalette(palette);
                  setKeepOriginal(false);
                }}
                className={`p-4 rounded-xl border-2 transition-all text-left ${
                  selectedPalette?.name === palette.name
                    ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                    : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      selectedPalette?.name === palette.name 
                        ? 'border-purple-500 bg-purple-500' 
                        : 'border-gray-300 dark:border-gray-600'
                    }`}>
                      {selectedPalette?.name === palette.name && (
                        <Check className="w-3 h-3 text-white" />
                      )}
                    </div>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {palette.name}
                    </p>
                  </div>
                  {palette.name === "Let AI Decide" && (
                    <span className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 px-2 py-1 rounded-full">
                      AI
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 ml-7">
                  {palette.description}
                </p>
                <div className="flex gap-1 ml-7">
                  {palette.colors.map((color, idx) => (
                    <div
                      key={idx}
                      className="flex-1 h-8 rounded-md border border-gray-200 dark:border-gray-700"
                      style={{ backgroundColor: color }}
                    />
                  ))}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors font-medium"
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            className="px-6 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors font-medium flex items-center gap-2"
          >
            <Check className="w-4 h-4" />
            Continue
          </button>
        </div>
      </div>
    </div>
  );
}

