import { useState } from "react";
import { PGCandidate, PGTableau, PGTableauRow, PGTenet } from "../../types/pg";
import {
  TableauColumn,
  candidateLetter,
  describeMarks,
  eliminatedAt,
  formatPercent,
  formatRanking,
  tableauCell,
  tableauColumns,
} from "../../utils/pg";
import TierBadge from "./TierBadge";

interface OperabilityTableProps {
  tableau: PGTableau;
  candidates: PGCandidate[];
  unitLabel: string;
  tenets: PGTenet[];
  // Optimality Theory style: fatal marks, shading after elimination and ☞. Otherwise the
  // table follows Ugorji's published PG tables: every mark, no "!", no shading, ⇒
  otStyle: boolean;
}

// "*!" is the fatal mark; it is drawn in red, the other marks in ink
const Marks = ({ cell }: { cell: string }) => {
  const bang = cell.indexOf("!");
  if (bang < 0) return <span aria-hidden="true">{cell}</span>;
  const fatalStart = Math.max(0, bang - 1);
  return (
    <span aria-hidden="true">
      {cell.slice(0, fatalStart)}
      <span className="font-bold text-red-700">
        {cell.slice(fatalStart, bang + 1)}
      </span>
      {cell.slice(bang + 1)}
    </span>
  );
};

// Solid rules between ranked tenets, dashed between unranked ones.
// Cells draw only their own top and left edges (separated borders), because in the
// collapsed model a neighbour's solid border would win over a dashed one.
// The sticky candidate column draws the rule before the first tenet.
const stratumBorder = (column: TableauColumn) =>
  column.startsStratum
    ? column.stratum > 0
      ? "border-l-2 border-l-gray-500"
      : ""
    : "[border-left-width:1px] [border-left-style:dashed] border-l-gray-500";

const OperabilityTable = ({
  tableau,
  candidates,
  unitLabel,
  tenets,
  otStyle,
}: OperabilityTableProps) => {
  const [selected, setSelected] = useState<{
    row: number;
    column: number;
  } | null>(null);
  const columns = tableauColumns(tableau, tenets);
  const winnerMark = otStyle ? "☞" : "⇒";

  const candidateFor = (row: PGTableauRow, index: number) =>
    candidates.find((candidate) => candidate.form === row.candidate) ??
    candidates[index];

  const evidence = (row: PGTableauRow, index: number, column: TableauColumn) =>
    candidateFor(row, index)?.violations[column.key];

  // The marks as shown: PG style drops the fatal "!"
  const cellText = (row: PGTableauRow, column: TableauColumn) => {
    const cell = tableauCell(row, column);
    return otStyle ? cell : cell.replace(/!/g, "");
  };

  const selectedRow = selected ? tableau.rows[selected.row] : undefined;
  const selectedColumn = selected ? columns[selected.column] : undefined;
  const selectedEvidence =
    selected && selectedRow && selectedColumn
      ? evidence(selectedRow, selected.row, selectedColumn)
      : undefined;

  return (
    <div className="space-y-3">
      <div className="overflow-x-auto rounded-lg border border-gray-300">
        <table className="min-w-full border-separate border-spacing-0 text-sm">
          <caption className="sr-only">
            Operability table for {unitLabel}: candidates in rows, tenets in
            ranking order in columns
          </caption>
          <thead>
            <tr className="bg-gray-50">
              <th
                scope="col"
                className="sticky left-0 z-10 bg-gray-50 border-r-2 border-r-gray-500 px-3 py-2 text-left font-ipa text-base"
              >
                {unitLabel}
              </th>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={`px-3 py-2 text-center align-bottom ${stratumBorder(
                    column
                  )}`}
                >
                  <span className="block font-mono whitespace-nowrap">
                    {column.label}
                  </span>
                  <span className="block text-xs font-normal text-gray-600">
                    {column.name}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableau.rows.map((row, r) => {
              const out = otStyle ? eliminatedAt(row, columns) : null;
              const letter = candidateLetter(r);
              const tier = candidateFor(row, r)?.tier;
              return (
                <tr
                  key={`${row.candidate}-${r}`}
                  className={row.preferred ? "bg-blue-50" : "bg-white"}
                >
                  <th
                    scope="row"
                    className={`sticky left-0 z-10 border-t border-t-gray-300 border-r-2 border-r-gray-500 px-3 py-2 text-left font-normal whitespace-nowrap ${
                      row.preferred ? "bg-blue-50" : "bg-white"
                    }`}
                  >
                    <span
                      className={`font-ipa text-base text-gray-900 ${
                        row.preferred ? "font-bold" : ""
                      }`}
                    >
                      {letter}.{" "}
                      {row.preferred && (
                        <span aria-hidden="true" className="text-blue-700">
                          {winnerMark}{" "}
                        </span>
                      )}
                      {row.candidate}
                    </span>
                    {row.preferred && (
                      <span className="sr-only"> (preferred)</span>
                    )}
                    <span className="block text-xs text-gray-600">
                      <span className="font-ipa">[{row.segment}]</span> ·{" "}
                      {formatPercent(row.share)} · {row.tokens} token
                      {row.tokens === 1 ? "" : "s"}
                    </span>
                    {tier && (
                      <span className="mt-1 block">
                        <TierBadge tier={tier} />
                      </span>
                    )}
                  </th>
                  {columns.map((column, c) => {
                    const cell = cellText(row, column);
                    const shaded = out !== null && column.stratum > out;
                    const violation = evidence(row, r, column);
                    const isSelected =
                      selected?.row === r && selected?.column === c;
                    return (
                      <td
                        key={column.key}
                        className={`border-t border-t-gray-300 p-0 ${stratumBorder(
                          column
                        )} ${shaded ? "bg-gray-200" : ""}`}
                      >
                        <button
                          type="button"
                          onClick={() =>
                            setSelected(isSelected ? null : { row: r, column: c })
                          }
                          aria-pressed={isSelected}
                          aria-label={`${letter}. ${row.candidate}, ${
                            column.label
                          } (${column.name}): ${describeMarks(cell)}${
                            shaded ? ", already eliminated" : ""
                          }. Show evidence`}
                          title={
                            violation?.reason
                              ? `${violation.reason} [${violation.source}]`
                              : undefined
                          }
                          className={`w-full min-w-16 min-h-11 px-3 py-2 font-mono text-base text-center focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-600 hover:bg-blue-100/60 ${
                            shaded ? "text-gray-600" : "text-gray-900"
                          } ${isSelected ? "ring-2 ring-inset ring-blue-600" : ""}`}
                        >
                          <Marks cell={cell} />
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-600">
        <span className="font-mono">*</span> violation ·{" "}
        {otStyle && (
          <>
            <span className="font-mono font-bold text-red-700">*!</span> fatal
            violation ·{" "}
            <span className="inline-block w-3 h-3 align-middle bg-gray-200 border border-gray-300" />{" "}
            shaded: no longer decides anything ·{" "}
          </>
        )}
        <span aria-hidden="true">{winnerMark}</span> preferred. Ranking:{" "}
        <span className="font-mono">{formatRanking(tableau.ranking)}</span>
      </p>

      <div
        aria-live="polite"
        className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm"
      >
        {selected && selectedRow && selectedColumn ? (
          <div className="space-y-1">
            <p className="font-semibold text-gray-900">
              <span className="font-ipa">
                {candidateLetter(selected.row)}. {selectedRow.candidate}
              </span>{" "}
              · {selectedColumn.label} ({selectedColumn.name}) ·{" "}
              {describeMarks(cellText(selectedRow, selectedColumn))}
            </p>
            <p className="text-gray-800">
              {selectedEvidence?.reason || "No reason was recorded for this cell."}
            </p>
            {selectedEvidence?.source && (
              <p className="text-xs text-gray-600">
                Source: {selectedEvidence.source}
              </p>
            )}
          </div>
        ) : (
          <p className="text-gray-600">
            Select a cell to see the evidence behind its marks.
          </p>
        )}
      </div>

      <details className="rounded-lg border border-gray-200">
        <summary className="cursor-pointer select-none px-3 py-2 text-sm font-semibold text-blue-700 rounded-lg hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
          Evidence for every cell
        </summary>
        <div className="px-3 pb-3 space-y-4">
          {tableau.rows.map((row, r) => (
            <div key={`${row.candidate}-${r}`}>
              <p className="font-semibold text-gray-900">
                <span className="font-ipa">
                  {candidateLetter(r)}. {row.candidate}
                </span>{" "}
                <span className="font-normal text-gray-600">
                  (<span className="font-ipa">[{row.segment}]</span>)
                </span>
              </p>
              <ul className="mt-1 space-y-1 text-sm">
                {columns.map((column) => {
                  const violation = evidence(row, r, column);
                  return (
                    <li key={column.key} className="text-gray-800">
                      <span className="font-mono">{column.label}</span> ·{" "}
                      {describeMarks(cellText(row, column))}
                      {violation?.reason && <> · {violation.reason}</>}
                      {violation?.source && (
                        <span className="text-gray-600">
                          {" "}
                          ({violation.source})
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </details>
    </div>
  );
};

export default OperabilityTable;
