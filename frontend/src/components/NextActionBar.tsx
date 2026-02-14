"use client";

import type { WorkflowStep } from "@/components/WorkflowStepper";

interface NextActionBarProps {
  nextStep?: WorkflowStep;
}

const scrollToStep = (id: string) => {
  if (typeof window === "undefined") return;
  const target = document.getElementById(id);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
};

export function NextActionBar({ nextStep }: NextActionBarProps) {
  if (!nextStep) {
    return null;
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-indigo-200/60 bg-white/95 p-3 shadow-lg backdrop-blur-md dark:border-indigo-900/50 dark:bg-slate-900/95">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-900 dark:text-slate-100">
            Next: {nextStep.label}
          </p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {nextStep.hint}
          </p>
        </div>
        <button
          type="button"
          onClick={() => scrollToStep(nextStep.id)}
          className="shrink-0 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-700"
        >
          Go to Step
        </button>
      </div>
      <div style={{ paddingBottom: "env(safe-area-inset-bottom)" }} />
    </div>
  );
}
