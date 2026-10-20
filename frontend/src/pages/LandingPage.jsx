import { useNavigate } from "react-router-dom";

const tenets = [
  "International Acceptance",
  "Contrastiveness",
  "Frequency",
  "Disambiguity",
  "Phonetic Simplicity",
  "Pedagogic Convenience",
];

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <main className="min-h-screen bg-gray-100 flex items-center justify-center px-4 py-10">
      <section className="max-w-5xl w-full bg-white rounded-lg shadow p-8 md:p-12">
        <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-10 items-center">
          <div>
            <p className="text-sm uppercase tracking-wide text-indigo-700 font-semibold">
              Preference Grammar System
            </p>
            <h1 className="text-4xl md:text-5xl font-bold text-gray-950 mt-3">
              Select a preferred pronunciation from attested IPA variants.
            </h1>
            <p className="text-lg text-gray-600 mt-5">
              This rebuild follows the professor's PG presentation: collect the forms
              that occur in speech, score them against ranked tenets, then produce an
              operability table and a preferred pronunciation.
            </p>
            <button
              type="button"
              onClick={() => navigate("/upload")}
              className="mt-8 bg-indigo-600 text-white hover:bg-indigo-700"
            >
              Start Analysis
            </button>
          </div>

          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="bg-indigo-600 text-white px-5 py-4 font-semibold">
              PG Tenets
            </div>
            <div className="divide-y divide-gray-200">
              {tenets.map((tenet, index) => (
                <div key={tenet} className="flex items-center gap-4 px-5 py-4">
                  <div className="w-8 h-8 rounded-full bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold">
                    {index + 1}
                  </div>
                  <span className="text-gray-900 font-medium">{tenet}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
