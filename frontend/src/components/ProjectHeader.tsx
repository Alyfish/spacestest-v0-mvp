import Link from "next/link";

interface ProjectHeaderProps {
  projectId: string;
}

export function ProjectHeader({ projectId }: ProjectHeaderProps) {
  return (
    <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-slate-200 dark:border-gray-700">
      <div className="h-[60px] px-5 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="p-2 -ml-2 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
            aria-label="Back to home"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m15 18-6-6 6-6" />
            </svg>
          </Link>
          <div>
            <h1 className="text-base font-semibold text-gray-900 dark:text-white">
              Project
            </h1>
            <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              {projectId.slice(0, 8)}...
            </p>
          </div>
        </div>
        <span className="text-lg font-extrabold text-gray-900 dark:text-white tracking-tight">
          Spaces<span className="text-rose-500">.</span>
        </span>
      </div>
    </header>
  );
}
