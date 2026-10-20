import { PGUnit } from "../../types/pg";
import { formatPercent } from "../../utils/pg";
import ValidationBadge from "./ValidationBadge";

interface UnitSummaryProps {
  unit?: PGUnit;
}

const UnitSummary = ({ unit }: UnitSummaryProps) => {
  if (!unit) {
    return (
      <p className="text-sm text-gray-600">
        The server will use the first unit whose reference sound occurs in
        every target word.
      </p>
    );
  }

  const validation = unit.validation;
  // The figures of the human-labelled test, where the server reports them
  const figures = [
    typeof validation?.accuracy === "number" &&
      `accuracy ${formatPercent(validation.accuracy)}${
        typeof validation.majority_baseline === "number"
          ? ` (always guessing the commonest variant: ${formatPercent(
              validation.majority_baseline
            )})`
          : ""
      }`,
    typeof validation?.balanced_accuracy === "number" &&
      `balanced accuracy ${formatPercent(validation.balanced_accuracy)}`,
    typeof validation?.share_error === "number" &&
      `shares off by ${Math.round(
        validation.share_error * 100
      )} percentage points on average`,
  ].filter(Boolean);

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm space-y-3">
      <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 items-baseline">
        <dt className="text-gray-600">Reference sound</dt>
        <dd className="font-ipa text-lg text-gray-900">/{unit.phoneme}/</dd>
        <dt className="text-gray-600">Table label</dt>
        <dd className="text-gray-900">{unit.label}</dd>
        {unit.lexical_set && (
          <>
            <dt className="text-gray-600">Lexical set</dt>
            <dd className="text-gray-900">{unit.lexical_set}</dd>
          </>
        )}
        <dt className="text-gray-600">Classifier</dt>
        <dd className="space-y-1 text-gray-900">
          <ValidationBadge unit={unit} />
          <p className="text-xs text-gray-700">
            {validation?.note ||
              "The server did not report a human-labelled test for this sound."}
          </p>
          {figures.length > 0 && (
            <p className="text-xs text-gray-600">
              Human-labelled test: {figures.join(" · ")}
              {validation?.calibrated ? ", with calibration" : ""}.
            </p>
          )}
        </dd>
      </dl>

      <div>
        <p className="font-semibold text-gray-700">
          Variants listened for in the audio
        </p>
        <ul className="mt-2 flex flex-wrap gap-2">
          {unit.candidates.map((variant) => (
            <li
              key={variant}
              className="inline-flex items-baseline gap-2 rounded-full border border-gray-300 bg-white px-3 py-1"
            >
              <span className="font-ipa text-base text-gray-900">
                [{variant}]
              </span>
              {unit.international.includes(variant) && (
                <span className="text-xs text-green-800">
                  internationally accepted
                </span>
              )}
              {unit.pedagogic_difficult.includes(variant) && (
                <span className="text-xs text-amber-800">hard to teach</span>
              )}
            </li>
          ))}
        </ul>
        <p className="mt-2 text-xs text-gray-600">
          Each token is assigned to whichever of these variants fits it best.
        </p>
      </div>

      {unit.notes && <p className="text-gray-700">{unit.notes}</p>}
      {unit.sources.length > 0 && (
        <p className="text-xs text-gray-600">
          Sources: {unit.sources.join("; ")}
        </p>
      )}
    </div>
  );
};

export default UnitSummary;
