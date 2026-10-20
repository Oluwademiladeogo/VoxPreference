import { PGUnit } from "../../types/pg";
import { isValidated, validationLabel } from "../../utils/pg";

// Whether the classifier's labels for the unit passed a human-labelled test; the label,
// not the colour, carries the meaning
const ValidationBadge = ({ unit }: { unit: PGUnit }) => {
  const validated = isValidated(unit);
  return (
    <span
      title={unit.validation?.note || undefined}
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
        validated
          ? "bg-green-100 text-green-900"
          : "bg-amber-100 text-amber-900 ring-1 ring-inset ring-amber-300"
      }`}
    >
      <span className="sr-only">Classifier: </span>
      {validationLabel(unit)}
    </span>
  );
};

export default ValidationBadge;
