import { useEffect, useRef, useState } from "react";
import { PGTenet, RankingItem } from "../../types/pg";
import {
  formatRanking,
  moveRankingItem,
  rankingItemsFrom,
  rankingStrata,
} from "../../utils/pg";
import Icon from "./Icon";

interface RankingEditorProps {
  items: RankingItem[];
  onChange: (items: RankingItem[]) => void;
  tenets: PGTenet[];
  defaultRanking: string;
}

const RankingEditor = ({
  items,
  onChange,
  tenets,
  defaultRanking,
}: RankingEditorProps) => {
  const [announcement, setAnnouncement] = useState("");
  const buttonRefs = useRef(new Map<string, HTMLButtonElement>());
  const pendingFocus = useRef<string | null>(null);

  // Moving a row re-orders the DOM, so return focus to the button that moved it
  useEffect(() => {
    if (pendingFocus.current) {
      buttonRefs.current.get(pendingFocus.current)?.focus();
      pendingFocus.current = null;
    }
  }, [items]);

  const setButtonRef = (id: string) => (element: HTMLButtonElement | null) => {
    if (element) {
      buttonRefs.current.set(id, element);
    } else {
      buttonRefs.current.delete(id);
    }
  };

  const nameOf = (key: string) =>
    tenets.find((tenet) => tenet.key === key)?.name ?? key;
  const strata = rankingStrata(items);
  const keptCount = items.filter((item) => item.enabled).length;

  // Unranked tenets share their stratum's number
  const rankOf = new Map<string, number>();
  strata.forEach((stratum, i) =>
    stratum.forEach((key) => rankOf.set(key, i + 1))
  );

  const move = (index: number, delta: -1 | 1) => {
    const next = moveRankingItem(items, index, delta);
    if (!next) return;
    const moved = items[index];
    pendingFocus.current = `${moved.key}:${delta < 0 ? "up" : "down"}`;
    onChange(next);
    setAnnouncement(
      `${moved.key} moved to position ${index + delta + 1} of ${items.length}`
    );
  };

  const toggleKept = (index: number) => {
    const item = items[index];
    onChange(
      items.map((other, i) =>
        i === index ? { ...other, enabled: !other.enabled } : other
      )
    );
    setAnnouncement(
      item.enabled
        ? `${item.key} deleted from the ranking`
        : `${item.key} restored to the ranking`
    );
  };

  const toggleTie = (index: number) => {
    onChange(
      items.map((other, i) =>
        i === index ? { ...other, tiedWithAbove: !other.tiedWithAbove } : other
      )
    );
  };

  const reset = () => {
    onChange(rankingItemsFrom(defaultRanking, tenets));
    setAnnouncement("Ranking reset to the default");
  };

  // Buttons at either end use aria-disabled rather than disabled, so they keep focus
  // and a repeated key press does nothing instead of bouncing the tenet back
  const arrowClass =
    "p-1.5 rounded border border-gray-300 text-gray-700 hover:bg-gray-100 aria-disabled:opacity-40 aria-disabled:cursor-not-allowed aria-disabled:hover:bg-transparent focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500";

  return (
    <div className="space-y-3">
      <p id="pg-ranking-help" className="text-sm text-gray-600">
        Higher tenets dominate lower ones: a candidate is out as soon as it has
        more marks than a rival on the highest tenet where they differ. Untick
        a tenet to delete it, or make it unranked with the tenet above to pool
        their marks.
      </p>

      <ol className="space-y-2" aria-describedby="pg-ranking-help">
        {items.map((item, index) => {
          const above = index > 0 ? items[index - 1] : undefined;
          const name = nameOf(item.key);

          return (
            <li
              key={item.key}
              className={`flex items-center gap-3 rounded-lg border p-3 ${
                item.enabled
                  ? "border-gray-300 bg-white"
                  : "border-dashed border-gray-300 bg-gray-50"
              }`}
            >
              <span
                aria-hidden="true"
                className={`w-8 h-8 shrink-0 rounded-full flex items-center justify-center text-sm font-semibold ${
                  item.enabled
                    ? "bg-blue-100 text-blue-800"
                    : "bg-gray-200 text-gray-600"
                }`}
              >
                {rankOf.get(item.key) ?? "–"}
              </span>

              <div className="flex-1 min-w-0">
                <p className="text-gray-900">
                  <span
                    className={`font-semibold ${
                      item.enabled ? "" : "line-through text-gray-600"
                    }`}
                  >
                    {item.key}
                  </span>{" "}
                  <span className="text-sm text-gray-600">{name}</span>
                  {!item.enabled && (
                    <span className="sr-only"> (deleted)</span>
                  )}
                </p>
                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-700">
                  <label className="inline-flex items-center gap-1.5">
                    <input
                      type="checkbox"
                      checked={item.enabled}
                      onChange={() => toggleKept(index)}
                      disabled={item.enabled && keptCount === 1}
                      className="h-4 w-4 accent-blue-600"
                    />
                    Keep<span className="sr-only"> {name} in the ranking</span>
                  </label>
                  {item.enabled && above && (
                    <label className="inline-flex items-center gap-1.5">
                      <input
                        type="checkbox"
                        checked={item.tiedWithAbove}
                        onChange={() => toggleTie(index)}
                        className="h-4 w-4 accent-blue-600"
                      />
                      Unranked with {above.key}
                    </label>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  ref={setButtonRef(`${item.key}:up`)}
                  onClick={() => move(index, -1)}
                  aria-disabled={index === 0}
                  aria-label={`Move ${name} up`}
                  className={arrowClass}
                >
                  <Icon name="chevronUp" className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  ref={setButtonRef(`${item.key}:down`)}
                  onClick={() => move(index, 1)}
                  aria-disabled={index === items.length - 1}
                  aria-label={`Move ${name} down`}
                  className={arrowClass}
                >
                  <Icon name="chevronDown" className="w-4 h-4" />
                </button>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-gray-700 min-w-0">
          Ranking sent:{" "}
          <code className="font-mono text-gray-900 bg-gray-100 rounded px-2 py-1 break-words">
            {formatRanking(strata)}
          </code>
        </p>
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Icon name="reset" className="w-4 h-4" />
          Reset to default
        </button>
      </div>

      <p className="sr-only" aria-live="polite">
        {announcement}
      </p>
    </div>
  );
};

export default RankingEditor;
