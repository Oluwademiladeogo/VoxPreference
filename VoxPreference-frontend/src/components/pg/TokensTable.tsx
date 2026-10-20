import { useState } from "react";
import useClipPlayer from "../../hooks/useClipPlayer";
import { PGToken } from "../../types/pg";
import Icon from "./Icon";

interface TokensTableProps {
  tokens: PGToken[];
  files: Map<string, File>;
  reviewBelow: number;
}

const otherVariants = (token: PGToken) =>
  Object.entries(token.scores)
    .filter(([variant]) => variant !== token.variant)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 2);

const headerClass =
  "sticky top-0 z-10 bg-gray-50 border-b border-gray-300 px-3 py-2 text-left font-semibold text-gray-700 whitespace-nowrap";
const cellClass = "border-b border-gray-200 px-3 py-2";

const TokensTable = ({ tokens, files, reviewBelow }: TokensTableProps) => {
  const [onlyReview, setOnlyReview] = useState(false);
  const player = useClipPlayer();

  // Play just the stretch of the recording the token was found in
  const play = (index: number, token: PGToken) => {
    const file = files.get(token.recording);
    if (file) player.play(String(index), file, token.start, token.end);
  };

  const reviewCount = tokens.filter((token) => token.review).length;
  const rows = tokens
    .map((token, index) => ({ token, index }))
    .filter(({ token }) => !onlyReview || token.review);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-xl font-semibold text-gray-900">Tokens</h3>
        <label className="inline-flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={onlyReview}
            onChange={(e) => setOnlyReview(e.target.checked)}
            disabled={reviewCount === 0}
            className="h-4 w-4 accent-blue-600"
          />
          Only tokens to check by ear ({reviewCount})
        </label>
      </div>
      <p className="text-sm text-gray-600">
        Each row is one occurrence of the sound. Rows marked “check by ear”
        have a posterior below {reviewBelow}: the model was unsure which
        variant it heard, so listen and correct the data if needed.
      </p>

      <div className="max-h-[32rem] overflow-auto rounded-lg border border-gray-200">
        <table className="min-w-full border-separate border-spacing-0 text-sm">
          <caption className="sr-only">
            Tokens of the sound under study, one per row
          </caption>
          <thead>
            <tr>
              <th scope="col" className={headerClass}>
                <span className="sr-only">Listen</span>
              </th>
              <th scope="col" className={headerClass}>
                Recording
              </th>
              <th scope="col" className={headerClass}>
                Variant
              </th>
              <th scope="col" className={`${headerClass} text-right`}>
                Posterior
              </th>
              <th scope="col" className={headerClass}>
                Check
              </th>
              <th scope="col" className={headerClass}>
                Next best
              </th>
              <th scope="col" className={headerClass}>
                Word
              </th>
              <th scope="col" className={headerClass}>
                Speaker
              </th>
              <th scope="col" className={headerClass}>
                Time (s)
              </th>
              <th scope="col" className={headerClass}>
                Realised
              </th>
              <th scope="col" className={headerClass}>
                Heard
              </th>
              <th scope="col" className={headerClass}>
                Sub-cluster
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ token, index }) => {
              const isPlaying = player.playing === String(index);
              const span = `${token.start.toFixed(2)}–${token.end.toFixed(2)}`;
              return (
                <tr
                  key={index}
                  className={token.review ? "bg-amber-50" : "bg-white"}
                >
                  <td className={cellClass}>
                    <button
                      type="button"
                      onClick={() =>
                        isPlaying ? player.stop() : play(index, token)
                      }
                      disabled={!files.has(token.recording)}
                      aria-label={
                        isPlaying
                          ? "Stop playback"
                          : `Play "${token.word}" in ${token.recording}, ${span} seconds`
                      }
                      className="p-1 rounded text-blue-700 hover:bg-blue-100 disabled:opacity-40 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                    >
                      <Icon name={isPlaying ? "stop" : "play"} />
                    </button>
                  </td>
                  <td
                    className={`${cellClass} max-w-[14rem] truncate text-gray-900`}
                    title={token.recording}
                  >
                    {token.recording}
                  </td>
                  <td className={`${cellClass} font-ipa text-base text-gray-900`}>
                    [{token.variant}]
                  </td>
                  <td
                    className={`${cellClass} text-right tabular-nums text-gray-900`}
                  >
                    {token.posterior.toFixed(2)}
                  </td>
                  <td className={`${cellClass} whitespace-nowrap`}>
                    {token.review ? (
                      <span className="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900">
                        <Icon name="ear" className="w-3.5 h-3.5" />
                        Check by ear
                      </span>
                    ) : (
                      <span className="text-xs text-gray-600">Confident</span>
                    )}
                  </td>
                  <td
                    className={`${cellClass} whitespace-nowrap text-xs text-gray-700`}
                  >
                    {otherVariants(token).map(([variant, score], i) => (
                      <span key={variant}>
                        {i > 0 && " · "}
                        <span className="font-ipa text-sm">[{variant}]</span>{" "}
                        <span className="tabular-nums">{score.toFixed(2)}</span>
                      </span>
                    ))}
                  </td>
                  <td className={`${cellClass} text-gray-800`}>{token.word}</td>
                  <td className={`${cellClass} text-gray-800`}>
                    {token.speaker}
                  </td>
                  <td
                    className={`${cellClass} tabular-nums whitespace-nowrap text-gray-800`}
                  >
                    {span}
                  </td>
                  <td
                    className={`${cellClass} whitespace-nowrap font-ipa text-base text-gray-900`}
                  >
                    {token.realised}
                  </td>
                  <td
                    className={`${cellClass} whitespace-nowrap font-ipa text-base text-gray-700`}
                  >
                    {token.heard}
                  </td>
                  <td className={`${cellClass} font-ipa text-gray-800`}>
                    {token.secondary}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TokensTable;
