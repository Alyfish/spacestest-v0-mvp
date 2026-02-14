"use client";

export interface WorkflowStep {
  id: string;
  label: string;
  hint: string;
  completed: boolean;
}

interface WorkflowStepperProps {
  steps: WorkflowStep[];
}

const scrollToStep = (id: string) => {
  if (typeof window === "undefined") return;
  const target = document.getElementById(id);
  if (!target) return;
  target.scrollIntoView({ behavior: "smooth", block: "start" });
};

export function WorkflowStepper({ steps }: WorkflowStepperProps) {
  const firstIncompleteIndex = steps.findIndex((step) => !step.completed);
  const activeIndex =
    firstIncompleteIndex === -1 ? Math.max(steps.length - 1, 0) : firstIncompleteIndex;

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white/90 p-4 shadow-sm backdrop-blur-sm dark:border-slate-700 dark:bg-slate-900/80">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-slate-900 dark:text-slate-100">
          Project Progress
        </h2>
        <span className="text-xs text-slate-500 dark:text-slate-400">
          Step {Math.min(activeIndex + 1, steps.length)} of {steps.length}
        </span>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {steps.map((step, index) => {
          const isActive = index === activeIndex;
          const isComplete = step.completed;

          return (
            <button
              key={step.id}
              type="button"
              onClick={() => scrollToStep(step.id)}
              className={`min-w-[180px] rounded-xl border px-3 py-3 text-left transition-colors ${
                isComplete
                  ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-700/60 dark:bg-emerald-900/20 dark:text-emerald-200"
                  : isActive
                  ? "border-indigo-300 bg-indigo-50 text-indigo-900 dark:border-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-100"
                  : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-slate-600"
              }`}
            >
              <div className="mb-1 flex items-center gap-2">
                <span
                  className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-semibold ${
                    isComplete
                      ? "bg-emerald-600 text-white"
                      : isActive
                      ? "bg-indigo-600 text-white"
                      : "bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200"
                  }`}
                >
                  {isComplete ? "✓" : index + 1}
                </span>
                <span className="text-sm font-semibold">{step.label}</span>
              </div>
              <p className="line-clamp-2 text-xs opacity-85">{step.hint}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
