import { tierLabel } from "../../utils/pg";

// From most to least formal; the label, not the colour, carries the meaning
const TIER_STYLES: Record<string, string> = {
  "preferred (formal standard)": "bg-blue-100 text-blue-900",
  "allophone (formal inventory)": "bg-gray-100 text-gray-800",
  "outer (informal) norm": "bg-white text-gray-700 ring-1 ring-inset ring-gray-300",
};

const TierBadge = ({ tier }: { tier?: string }) => {
  if (!tier) return null;
  return (
    <span
      title={tier}
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ${
        TIER_STYLES[tier] ?? "bg-gray-100 text-gray-800"
      }`}
    >
      <span aria-hidden="true">{tierLabel(tier)}</span>
      <span className="sr-only">Tier: {tier}</span>
    </span>
  );
};

export default TierBadge;
