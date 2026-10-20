import { useEffect, useState } from "react";
import { formatDuration } from "../../utils/pg";

interface AnalysisProgressProps {
  startedAt: number;
  files: number;
  words: string[];
  unscripted: boolean; // some files are transcribed by speech recognition first
  onCancel: () => void;
}

// The server sends no progress events, so show what is happening and for how long
const AnalysisProgress = ({
  startedAt,
  files,
  words,
  unscripted,
  onCancel,
}: AnalysisProgressProps) => {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
      <div className="flex flex-wrap items-start gap-3">
        <svg
          className="w-6 h-6 shrink-0 text-blue-700 motion-safe:animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        <div className="flex-1 min-w-[12rem] space-y-1 text-blue-900">
          <p role="status" className="font-semibold">
            Analysing {files} recording{files === 1 ? "" : "s"} of{" "}
            {words.map((word) => `“${word}”`).join(", ")}
          </p>
          <p className="text-sm">
            The server is locating each word, scoring every candidate variant
            and building the operability table. This can take several minutes
            on a CPU, and longer the first time while the phone model loads.
            {unscripted &&
              " Unscripted audio is transcribed by speech recognition first, which takes longer still."}{" "}
            You can switch to the chat in the meantime.
          </p>
          <p className="text-sm">
            Elapsed{" "}
            <span className="font-mono tabular-nums">
              {formatDuration((now - startedAt) / 1000)}
            </span>
          </p>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border border-blue-300 bg-white text-blue-800 font-semibold hover:bg-blue-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
        >
          Cancel
        </button>
      </div>
      <div
        role="progressbar"
        aria-label="Analysis in progress"
        className="mt-3 h-1.5 overflow-hidden rounded-full bg-blue-100"
      >
        <div className="h-full w-1/3 rounded-full bg-blue-600 motion-safe:animate-indeterminate motion-reduce:w-full motion-reduce:opacity-40" />
      </div>
    </div>
  );
};

export default AnalysisProgress;
