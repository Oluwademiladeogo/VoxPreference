import { PGCandidate, PGVariantCount, SettingsValues } from "../../types/pg";
import { formatPercent } from "../../utils/pg";
import TierBadge from "./TierBadge";

interface CandidateSharesProps {
  candidates: PGCandidate[];
  superfluous: PGVariantCount[];
  preferred: string[];
  totalTokens: number;
  settings: SettingsValues;
}

// Emphasis: the preferred form in the accent colour, the other variants in gray
const CandidateShares = ({
  candidates,
  superfluous,
  preferred,
  totalTokens,
  settings,
}: CandidateSharesProps) => {
  const threshold = Math.min(Math.max(settings.freq_threshold, 0), 1) * 100;
  const hasTiers = candidates.some((candidate) => candidate.tier);

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-600">
        {settings.freq_weighting === "speakers"
          ? `Each variant's share of the speakers' usage, with every speaker counting equally (${totalTokens} tokens).`
          : `Share of the ${totalTokens} token${totalTokens === 1 ? "" : "s"} realised with each variant.`}{" "}
        The vertical rule marks the FreQ threshold (
        {formatPercent(settings.freq_threshold)}): variants below it get *No
        FreQ.
      </p>
      <ul className="space-y-3">
        {candidates.map((candidate) => {
          const isPreferred = preferred.includes(candidate.form);
          return (
            <li key={candidate.form}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="min-w-0 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <span className="font-ipa text-base text-gray-900">
                    [{candidate.segment}] {candidate.form}
                  </span>
                  {candidate.tier ? (
                    <TierBadge tier={candidate.tier} />
                  ) : (
                    isPreferred && (
                      <span className="text-xs font-semibold text-blue-800">
                        preferred
                      </span>
                    )
                  )}
                </span>
                <span className="shrink-0 tabular-nums text-gray-700">
                  {formatPercent(candidate.share)} ({candidate.tokens})
                </span>
              </div>
              <div className="relative mt-1 h-3" aria-hidden="true">
                <div className="absolute inset-0 rounded-r bg-gray-100" />
                <div
                  className={`absolute inset-y-0 left-0 rounded-r ${
                    isPreferred ? "bg-blue-600" : "bg-gray-400"
                  }`}
                  style={{
                    width: `${candidate.share * 100}%`,
                    minWidth: candidate.share > 0 ? "2px" : undefined,
                  }}
                />
                <div
                  className="absolute -inset-y-1 w-px bg-gray-700"
                  style={{ left: `${threshold}%` }}
                />
              </div>
            </li>
          );
        })}
      </ul>

      {hasTiers && (
        <p className="text-xs text-gray-600">
          Tiers: the formal standard is the preferred form; an allophone loses
          but meets I-Ac and ContR, so it stays in the formal inventory; other
          variants belong to the outer (informal) norm.
        </p>
      )}

      {superfluous.length > 0 && (
        <div className="border-t border-gray-200 pt-3">
          <h4 className="text-sm font-semibold text-gray-800">
            Also attested (too rare to compete)
          </h4>
          <p className="text-xs text-gray-600">
            A variant needs at least {settings.min_tokens} token
            {settings.min_tokens === 1 ? "" : "s"} from{" "}
            {settings.min_speakers} speaker
            {settings.min_speakers === 1 ? "" : "s"} to compete.
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {superfluous.map((variant) => (
              <li
                key={variant.form}
                className="flex items-baseline justify-between gap-3"
              >
                <span className="font-ipa text-base text-gray-900">
                  [{variant.segment}] {variant.form}
                </span>
                <span className="shrink-0 tabular-nums text-gray-700">
                  {formatPercent(variant.share)} ({variant.tokens})
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default CandidateShares;
