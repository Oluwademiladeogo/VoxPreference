import { useEffect, useState } from "react";
import Header from "../components/Header.jsx";
import Footer from "../components/Footer.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import BackButton from "../components/BackButton.jsx";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

const columns = [
  ["ipa", "IPA"],
  ["count", "Count"],
  ["source_type", "Source"],
  ["reviewer", "Reviewer"],
  ["confidence", "Confidence"],
  ["validated", "Validated"],
  ["international_acceptance", "IA"],
  ["contrastiveness", "CO"],
  ["frequency", "F"],
  ["disambiguity", "DI"],
  ["phonetic_simplicity", "PS"],
  ["pedagogic_convenience", "PC"],
  ["weighted_score", "Weighted"],
];

// Strict ranking (Ugorji): each tenet column holds violation marks ("*", "!" = the fatal one), in ranked order
const STRICT_LABELS = {
  "I-Ac": ["international_acceptance", "IA"],
  ContR: ["contrastiveness", "CO"],
  FreQ: ["frequency", "F"],
  DisaM: ["disambiguity", "DI"],
  "Pho-S": ["phonetic_simplicity", "PS"],
  "Ped-C": ["pedagogic_convenience", "PC"],
};

function columnsFor(results) {
  if (results?.scoring !== "strict") return columns;
  const ranked = Object.keys(results.tenetNames || {}).map((tenet) => STRICT_LABELS[tenet]);
  return [
    ["ipa", "IPA"],
    ["sound", "Sound"],
    ["count", "Count"],
    ["source_type", "Source"],
    ["validated", "Validated"],
    ...ranked,
    ["outcome", "Outcome"],
  ];
}

function formatValue(value) {
  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }
  if (typeof value === "number") {
    return Number.isInteger(value) ? String(value) : value.toFixed(3);
  }
  return value ?? "";
}

export default function ResultsPage() {
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    try {
      const stored = JSON.parse(sessionStorage.getItem("analysisResults"));
      if (!stored?.success) {
        setError("No analysis results found. Please run the PG analysis first.");
        return;
      }
      setResults(stored);
    } catch {
      setError("Could not load analysis results.");
    }
  }, []);

  function exportToPDF() {
    if (!results) return;
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
    doc.setFontSize(18);
    doc.text("Preference Grammar Analysis", 14, 18);
    doc.setFontSize(11);
    doc.text(`Target word: ${results.targetWord}`, 14, 28);
    doc.text(`Recommended pronunciation: ${results.bestTranscription}`, 14, 36);
    doc.text(
      results.scoring === "strict"
        ? `Ranking: ${results.ranking}`
        : `Weighted score: ${formatValue(results.weightedScore)}`,
      14,
      44
    );

    autoTable(doc, {
      startY: 52,
      head: [columnsFor(results).map(([, label]) => label)],
      body: (results.tableRows || []).map((row) =>
        columnsFor(results).map(([key]) => formatValue(row[key]))
      ),
      theme: "grid",
      styles: { fontSize: 9 },
      headStyles: { fillColor: [79, 70, 229] },
    });

    doc.save("preference-grammar-results.pdf");
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col">
        <Header />
        <ProgressBar currentStep={4} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-xl text-red-600">{error}</div>
        </main>
        <Footer />
      </div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen bg-gray-100 flex flex-col">
        <Header />
        <ProgressBar currentStep={4} />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-xl text-gray-700">Loading results...</div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Header />
      <ProgressBar currentStep={4} />
      <main className="flex-1 flex items-center justify-center px-4 pb-10">
        <section className="max-w-6xl w-full bg-white rounded-lg shadow p-8 flex flex-col gap-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <BackButton />
            <button
              type="button"
              className="bg-indigo-600 text-white hover:bg-indigo-700"
              onClick={exportToPDF}
            >
              Export PDF
            </button>
          </div>

          <div>
            <p className="text-sm uppercase tracking-wide text-indigo-700 font-semibold">
              Recommended Pronunciation
            </p>
            <h1 className="text-4xl font-bold text-gray-900 mt-1">
              {results.bestTranscription}
            </h1>
            <p className="text-gray-600 mt-2">
              Target word: <span className="font-semibold">{results.targetWord}</span>
              {results.referenceIpa ? (
                <>
                  {" "}
                  | International reference:{" "}
                  <span className="font-semibold">{results.referenceIpa}</span>
                </>
              ) : null}
            </p>
          </div>

          {results.warnings?.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-4">
              {results.warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {results.scoring === "strict" ? (
              <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-100">
                <p className="text-sm text-indigo-700 font-semibold">Ranking</p>
                <p className="text-base font-semibold text-indigo-900">{results.ranking}</p>
                <p className="text-sm text-indigo-800 mt-1">
                  Sound under study: {results.sound?.label} /{results.sound?.phoneme}/
                </p>
              </div>
            ) : (
              <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-100">
                <p className="text-sm text-indigo-700 font-semibold">Weighted Score</p>
                <p className="text-3xl font-bold text-indigo-900">
                  {formatValue(results.weightedScore)}
                </p>
              </div>
            )}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <p className="text-sm text-gray-600 font-semibold">Scoring Method</p>
              <p className="text-lg font-semibold text-gray-900">{results.method}</p>
            </div>
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
              <p className="text-sm text-gray-600 font-semibold">Variants Evaluated</p>
              <p className="text-3xl font-bold text-gray-900">
                {results.tableRows?.length || 0}
              </p>
            </div>
          </div>

          {results.validationSummary && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600 font-semibold">Validated Variants</p>
                <p className="text-2xl font-bold text-gray-900">
                  {results.validationSummary.validatedCount} /{" "}
                  {results.validationSummary.variantCount}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600 font-semibold">Automatic Variants</p>
                <p className="text-2xl font-bold text-gray-900">
                  {results.validationSummary.automaticCount}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-gray-200">
                <p className="text-sm text-gray-600 font-semibold">Reviewers</p>
                <p className="text-base font-semibold text-gray-900">
                  {results.validationSummary.reviewers?.length
                    ? results.validationSummary.reviewers.join(", ")
                    : "None recorded"}
                </p>
              </div>
            </div>
          )}

          <div className="overflow-x-auto border border-gray-200 rounded-lg">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  {columnsFor(results).map(([, label]) => (
                    <th
                      key={label}
                      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase"
                    >
                      {label}
                    </th>
                  ))}
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                    {results.scoring === "strict" ? "Why marked" : "Unmet Tenets"}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {(results.tableRows || []).map((row, index) => (
                  <tr key={row.ipa} className={index === 0 ? "bg-indigo-50" : ""}>
                    {columnsFor(results).map(([key]) => (
                      <td key={key} className="px-4 py-3 text-sm text-gray-700">
                        {formatValue(row[key])}
                      </td>
                    ))}
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {row.unmet_tenets?.length
                        ? row.unmet_tenets.join(results.scoring === "strict" ? "; " : ", ")
                        : "None"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {results.scoring === "strict" && (
            <p className="text-sm text-gray-600">
              Strict ranking, as in Prof. Ugorji&apos;s Preference Grammar: a form is out as soon as it has
              more marks than a rival on the highest tenet where they differ (! marks the fatal one);
              lower tenets only break ties. The slider order sets the ranking; equal sliders are pooled
              and a slider at 0 leaves the tenet out.
            </p>
          )}

          {results.weights && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h2 className="font-semibold text-gray-900">Weighting</h2>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mt-3">
              {Object.entries(results.weights || {}).map(([key, value]) => (
                <div key={key} className="bg-white rounded border border-gray-200 p-3">
                  <p className="text-xs text-gray-500">{key}</p>
                  <p className="text-lg font-semibold text-gray-900">
                    {Number(value).toFixed(3)}
                  </p>
                </div>
              ))}
            </div>
          </div>
          )}
        </section>
      </main>
      <Footer />
    </div>
  );
}
