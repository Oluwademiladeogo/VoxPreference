const steps = ["Evidence", "Variants", "Tenets", "Results"];

export default function ProgressBar({ currentStep }) {
  return (
    <div className="flex flex-wrap justify-center items-center gap-4 my-8 px-4">
      {steps.map((label, idx) => (
        <div key={label} className="flex items-center gap-2">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-base ${
              currentStep === idx + 1
                ? "bg-indigo-600 text-white"
                : "bg-gray-200 text-gray-500"
            }`}
          >
            {idx + 1}
          </div>
          <span
            className={`text-sm font-medium ${
            currentStep === idx + 1 ? "text-indigo-700" : "text-gray-500"
            }`}
          >
            {label}
          </span>
          {idx !== steps.length - 1 && (
            <div className="w-8 h-1 bg-gray-200 rounded" />
          )}
        </div>
      ))}
    </div>
  );
}
