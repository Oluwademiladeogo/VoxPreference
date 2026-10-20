import { Fragment, Ref, useState } from "react";
import { AnalysisOutcome, PGTenet } from "../../types/pg";
import { downloadText, fileSlug, formatPercent } from "../../utils/pg";
import CandidateShares from "./CandidateShares";
import ClusterSummary from "./ClusterSummary";
import Icon from "./Icon";
import OperabilityTable from "./OperabilityTable";
import TokensTable from "./TokensTable";
import ValidationBadge from "./ValidationBadge";

interface AnalysisResultsProps {
  outcome: AnalysisOutcome;
  tenets: PGTenet[];
  headingRef: Ref<HTMLHeadingElement>;
}

const cardClass = "bg-white rounded-lg shadow-md p-4 md:p-6";
const headingClass = "text-xl font-semibold text-gray-900";

const AnalysisResults = ({
  outcome,
  tenets,
  headingRef,
}: AnalysisResultsProps) => {
  // Kept here rather than in the table so the choice survives new runs
  const [otStyle, setOtStyle] = useState(false);
  const { data, files, settings, unlabelledRecordings } = outcome;
  const { unit, tableau, stability } = data;
  const recordingCount = new Set(data.tokens.map((token) => token.recording))
    .size;
  const reviewCount = data.tokens.filter((token) => token.review).length;
  const prefix = `pg-${fileSlug(data.words.join("-"))}-`;
  const shareBasis =
    settings.freq_weighting === "speakers" ? "of speakers' usage" : "of tokens";

  // How often each variant won when the speakers and each token's variant were resampled
  const rates = stability ? Object.entries(stability.preferred_rate) : [];
  const topRate = rates.length
    ? Math.max(...rates.map(([, rate]) => rate))
    : null;

  return (
    <section aria-labelledby="pg-results-heading" className="space-y-6">
      <div className="space-y-1">
        <h2
          id="pg-results-heading"
          ref={headingRef}
          tabIndex={-1}
          className="scroll-mt-6 text-2xl font-bold text-gray-900 focus:outline-none"
        >
          Results
        </h2>
        <p className="text-gray-700">
          <span className="font-ipa">{unit.label}</span>{" "}
          <span className="font-ipa">/{unit.phoneme}/</span> in{" "}
          {data.words.map((word, i) => (
            <Fragment key={word}>
              {i > 0 && ", "}“{word}”
              {data.canonical[word] && (
                <span className="font-ipa"> /{data.canonical[word]}/</span>
              )}
            </Fragment>
          ))}{" "}
          <ValidationBadge unit={unit} />
        </p>
        <p className="text-sm text-gray-600">
          {data.tokens.length} token{data.tokens.length === 1 ? "" : "s"} from{" "}
          {recordingCount} recording{recordingCount === 1 ? "" : "s"} ·{" "}
          {reviewCount} to check by ear
        </p>
      </div>

      <div className={cardClass}>
        <h3 className={headingClass}>
          Preferred pronunciation{data.preferred.length > 1 ? "s" : ""}
        </h3>
        {data.preferred.length > 0 ? (
          <ul className="mt-3 flex flex-wrap gap-x-12 gap-y-4">
            {data.preferred.map((form) => {
              const candidate = data.candidates.find((c) => c.form === form);
              return (
                <li key={form}>
                  <p className="font-ipa text-5xl md:text-6xl leading-tight text-blue-800">
                    {form}
                  </p>
                  {candidate && (
                    <p className="mt-1 text-sm text-gray-700">
                      <span className="font-ipa">{unit.label}</span> as{" "}
                      <span className="font-ipa">[{candidate.segment}]</span> ·{" "}
                      {formatPercent(candidate.share)} {shareBasis}
                    </p>
                  )}
                  {candidate && stability && (
                    <p className="mt-1 text-sm font-semibold text-gray-900">
                      Preferred in{" "}
                      {formatPercent(
                        stability.preferred_rate[candidate.segment] ?? 0
                      )}{" "}
                      of resamples of the {stability.speakers} speakers
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-2 text-gray-700">
            No preferred form: no tokens of{" "}
            <span className="font-ipa">{unit.label}</span> were found in the
            recordings. See the warnings below.
          </p>
        )}

        {stability && rates.length > 0 && (
          <div className="mt-2 space-y-0.5 text-xs text-gray-600">
            <p>
              Resamples the speakers and the classifier's uncertainty about
              each token.
            </p>
            <p>
              Won in {stability.resamples.toLocaleString("en")} bootstrap
              resamples:{" "}
              {rates.map(([segment, rate], i) => (
                <Fragment key={segment}>
                  {i > 0 && " · "}
                  <span className="font-ipa">[{segment}]</span>{" "}
                  {formatPercent(rate)}
                </Fragment>
              ))}
            </p>
          </div>
        )}
        {stability && unlabelledRecordings > 0 && (
          <p className="mt-1 text-xs text-gray-600">
            {unlabelledRecordings === files.size
              ? "No speaker ids were given, so each recording counts as a separate speaker."
              : `${unlabelledRecordings} recording${
                  unlabelledRecordings === 1 ? "" : "s"
                } without a speaker id count${
                  unlabelledRecordings === 1 ? "s" : ""
                } as separate speakers.`}
          </p>
        )}
        {stability === null && data.tokens.length > 0 && (
          <p className="mt-2 text-xs text-gray-600">
            Stability is not shown: it needs recordings from at least 3
            speakers.
          </p>
        )}

        {topRate !== null && topRate < 0.8 && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <Icon name="warning" className="w-5 h-5 shrink-0" />
            <p>
              <strong>Not stable:</strong> the preferred form depends on which
              speakers are included — collect more speakers or check the
              low-confidence tokens.
            </p>
          </div>
        )}

        {tableau?.tie && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <Icon name="warning" className="w-5 h-5 shrink-0" />
            <p>
              <strong>Tie.</strong> {data.preferred.length} candidates survive
              every tenet in this ranking. Restore or re-rank a tenet that
              separates them, or add an expert override, then run the analysis
              again.
            </p>
          </div>
        )}
      </div>

      {data.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
          <h3 className="flex items-center gap-2 font-semibold text-amber-900">
            <Icon name="warning" />
            Warnings
          </h3>
          <ul className="mt-2 list-disc pl-6 space-y-1 text-sm text-amber-900">
            {data.warnings.map((warning, i) => (
              <li key={i}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {tableau && (
        <div className={`${cardClass} space-y-3`}>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h3 className={headingClass}>Operability table</h3>
            <label className="inline-flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={otStyle}
                onChange={(e) => setOtStyle(e.target.checked)}
                className="h-4 w-4 accent-blue-600"
              />
              Optimality Theory style
            </label>
          </div>
          <p className="text-sm text-gray-600">
            {otStyle
              ? "Each candidate is checked against the tenets from left to right in your ranking. It drops out at its first fatal mark (!), its later cells are shaded, and ☞ marks the candidate left standing."
              : "Every violation mark of each candidate, with the tenets in your ranking from left to right, as in Ugorji's published PG tables. ⇒ marks the preferred form."}{" "}
            Select a cell to see the evidence behind its marks.
          </p>
          <OperabilityTable
            key={outcome.id}
            tableau={tableau}
            candidates={data.candidates}
            unitLabel={unit.label}
            tenets={tenets}
            otStyle={otStyle}
          />
        </div>
      )}

      {data.candidates.length > 0 && (
        <div className={`${cardClass} space-y-3`}>
          <h3 className={headingClass}>Attested variants</h3>
          <CandidateShares
            candidates={data.candidates}
            superfluous={data.superfluous ?? []}
            preferred={data.preferred}
            totalTokens={data.tokens.length}
            settings={settings}
          />
        </div>
      )}

      {data.tokens.length > 0 && (
        <div className={cardClass}>
          <TokensTable
            key={outcome.id}
            tokens={data.tokens}
            files={files}
            reviewBelow={settings.review_below}
          />
        </div>
      )}

      {data.clusters && (
        // Collapsed by default: the clusters are exploratory, not evidence for the result
        <details className={cardClass}>
          <summary className="cursor-pointer select-none rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
            <h3 className={`${headingClass} inline`}>
              Acoustic clusters (exploratory)
            </h3>
            <span className="mt-1 block text-sm text-gray-600">
              These groupings barely separate the variants; they are shown for
              exploration, not as evidence.
            </span>
          </summary>
          <div className="mt-4">
            <ClusterSummary clusters={data.clusters} tokens={data.tokens} />
          </div>
        </details>
      )}

      <div className={`${cardClass} space-y-3`}>
        <h3 className={headingClass}>Downloads</h3>
        <p className="text-sm text-gray-600">
          Tables as CSV, the report as HTML, and the whole analysis as JSON.
        </p>
        <ul className="flex flex-wrap gap-2">
          {Object.entries(data.files).map(([name, content]) => (
            <li key={name}>
              <button
                type="button"
                onClick={() => downloadText(`${prefix}${name}`, content)}
                disabled={!content}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-800 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
              >
                <Icon name="download" className="w-4 h-4" />
                {name}
                {!content && <span className="text-gray-600">(empty)</span>}
              </button>
            </li>
          ))}
          <li>
            <button
              type="button"
              onClick={() =>
                downloadText(
                  `${prefix}analysis.json`,
                  // the files above are downloads of their own
                  JSON.stringify({ ...data, files: undefined }, null, 2)
                )
              }
              className="inline-flex items-center gap-2 px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-800 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
            >
              <Icon name="download" className="w-4 h-4" />
              analysis.json
            </button>
          </li>
        </ul>
      </div>
    </section>
  );
};

export default AnalysisResults;
