import { PGClusters, PGToken } from "../../types/pg";

interface ClusterSummaryProps {
  clusters: PGClusters;
  tokens: PGToken[];
}

// One-hue sequential ramp (light to dark) for similarity from 0 to 1
const RAMP = [
  "#cde2fb",
  "#b7d3f6",
  "#9ec5f4",
  "#86b6ef",
  "#6da7ec",
  "#5598e7",
  "#3987e5",
  "#2a78d6",
  "#256abf",
  "#1c5cab",
  "#184f95",
  "#104281",
  "#0d366b",
];
// From this step on white text keeps at least 4.5:1 contrast; below it near-black text does
const FIRST_DARK_STEP = 8;

const rampStep = (value: number) =>
  Math.round(Math.min(Math.max(value, 0), 1) * (RAMP.length - 1));

const ClusterSummary = ({ clusters, tokens }: ClusterSummaryProps) => {
  const { categories, contrast_matrix, separation, subclusters } = clusters;
  const counts = new Map<string, number>();
  tokens.forEach((token) => {
    const category = token.primary || token.variant;
    counts.set(category, (counts.get(category) ?? 0) + 1);
  });

  const subclustersOf = (category: string) =>
    Object.entries(subclusters)
      .filter(
        ([name]) => name === category || name.startsWith(`${category}.`)
      )
      .sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-5">
      <p className="text-sm text-gray-600">
        Tokens are grouped by the variant they realise, then split by acoustic
        similarity into sub-clusters: <span className="font-mono">t.1</span>{" "}
        is the core of [t], higher numbers are sub-variants or outliers.
        Separation is the mean silhouette (−1 to 1); higher means the variant
        sounds more distinct from the others.
      </p>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-gray-300 text-left text-gray-700">
              <th scope="col" className="py-2 pr-4 font-semibold">
                Variant
              </th>
              <th scope="col" className="py-2 pr-4 font-semibold text-right">
                Tokens
              </th>
              <th scope="col" className="py-2 pr-4 font-semibold text-right">
                Separation
              </th>
              <th scope="col" className="py-2 font-semibold">
                Sub-clusters
              </th>
            </tr>
          </thead>
          <tbody>
            {categories.map((category) => {
              const value = separation[category];
              return (
                <tr key={category} className="border-b border-gray-200">
                  <th
                    scope="row"
                    className="py-2 pr-4 text-left font-ipa text-base font-normal text-gray-900"
                  >
                    [{category}]
                  </th>
                  <td className="py-2 pr-4 text-right tabular-nums">
                    {counts.get(category) ?? 0}
                  </td>
                  <td className="py-2 pr-4 text-right tabular-nums">
                    {value === null || value === undefined
                      ? "—"
                      : value.toFixed(2)}
                  </td>
                  <td className="py-2">
                    <ul className="flex flex-wrap gap-1.5">
                      {subclustersOf(category).map(([name, count]) => (
                        <li
                          key={name}
                          className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-800"
                        >
                          <span className="font-ipa">{name}</span> · {count}
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {categories.length > 1 && (
        <div className="space-y-2">
          <h4 className="font-semibold text-gray-800">Contrast matrix</h4>
          <p className="text-sm text-gray-600">
            Cosine similarity between the average sound of each pair of
            variants: 1 means identical, lower values mean the variants are
            acoustically distinct.
          </p>
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-0.5 text-sm">
              <caption className="sr-only">
                Cosine similarity between variant centroids
              </caption>
              <thead>
                <tr>
                  <td />
                  {categories.map((category) => (
                    <th
                      key={category}
                      scope="col"
                      className="px-2 py-1 font-ipa text-base font-normal text-gray-900"
                    >
                      [{category}]
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {categories.map((rowCategory, i) => (
                  <tr key={rowCategory}>
                    <th
                      scope="row"
                      className="px-2 py-1 text-right font-ipa text-base font-normal text-gray-900"
                    >
                      [{rowCategory}]
                    </th>
                    {categories.map((columnCategory, j) => {
                      const value = contrast_matrix[i]?.[j] ?? 0;
                      const label = `[${rowCategory}] and [${columnCategory}]: ${value.toFixed(
                        2
                      )}`;
                      // Self-similarity is always 1, so the diagonal stays neutral
                      if (i === j) {
                        return (
                          <td
                            key={columnCategory}
                            title={label}
                            className="w-14 h-10 rounded text-center tabular-nums bg-gray-100 text-gray-600"
                          >
                            1
                          </td>
                        );
                      }
                      const step = rampStep(value);
                      return (
                        <td
                          key={columnCategory}
                          title={label}
                          style={{ backgroundColor: RAMP[step] }}
                          className={`w-14 h-10 rounded text-center tabular-nums ${
                            step >= FIRST_DARK_STEP ? "text-white" : "text-gray-950"
                          }`}
                        >
                          {value.toFixed(2)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-600" aria-hidden="true">
            <span>0</span>
            <span
              className="h-2 w-32 rounded"
              style={{ background: `linear-gradient(to right, ${RAMP.join(", ")})` }}
            />
            <span>1</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default ClusterSummary;
