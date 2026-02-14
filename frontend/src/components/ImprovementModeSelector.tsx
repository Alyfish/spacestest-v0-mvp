"use client";

import { RefreshCw, Sparkles } from "lucide-react";

interface ImprovementModeSelectorProps {
  onSelect: (mode: "iterative" | "complete_revamp") => void;
}

export function ImprovementModeSelector({
  onSelect,
}: ImprovementModeSelectorProps) {
  return (
    <div className="space-y-5">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white">
          How would you like to design your space?
        </h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Choose a path. You can iterate quickly or generate a full redesign.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onSelect("iterative")}
          className="flex min-h-40 flex-col items-start gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-left transition-all hover:-translate-y-0.5 hover:border-indigo-300 hover:bg-indigo-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-indigo-600 dark:hover:bg-indigo-900/20"
        >
          <div className="rounded-lg bg-indigo-100 p-2 dark:bg-indigo-900/40">
            <RefreshCw className="h-6 w-6 text-indigo-600 dark:text-indigo-300" />
          </div>
          <span className="font-semibold text-slate-900 dark:text-white">
            Iterative Improvements
          </span>
          <span className="text-sm text-slate-500 dark:text-slate-400">
            Enhance your current setup in focused steps.
          </span>
        </button>

        <button
          type="button"
          onClick={() => onSelect("complete_revamp")}
          className="flex min-h-40 flex-col items-start gap-2 rounded-2xl border border-slate-200 bg-white p-6 text-left transition-all hover:-translate-y-0.5 hover:border-indigo-300 hover:bg-indigo-50/60 dark:border-slate-700 dark:bg-slate-900 dark:hover:border-indigo-600 dark:hover:bg-indigo-900/20"
        >
          <div className="rounded-lg bg-indigo-100 p-2 dark:bg-indigo-900/40">
            <Sparkles className="h-6 w-6 text-indigo-600 dark:text-indigo-300" />
          </div>
          <span className="font-semibold text-slate-900 dark:text-white">
            Complete Revamp
          </span>
          <span className="text-sm text-slate-500 dark:text-slate-400">
            Redesign the room from scratch around a new vision.
          </span>
        </button>
      </div>
    </div>
  );
}
