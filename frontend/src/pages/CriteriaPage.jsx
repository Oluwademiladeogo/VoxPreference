import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";
import Footer from "../components/Footer.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import BackButton from "../components/BackButton.jsx";
import { fetchJson } from "../api.js";

const criteriaList = [
  {
    key: "IA",
    title: "International Acceptance",
    desc: "Closeness to a wider lingua-franca or international reference form.",
  },
  {
    key: "CO",
    title: "Contrastiveness",
    desc: "How strongly the form remains phonologically distinct from competing forms.",
  },
  {
    key: "F",
    title: "Frequency",
    desc: "How often this form occurs in the attested data.",
  },
  {
    key: "DI",
    title: "Disambiguity",
    desc: "How much the form reduces ambiguity or miscommunication.",
  },
  {
    key: "PS",
    title: "Phonetic Simplicity",
    desc: "Physiological plausibility and ease of articulation.",
  },
  {
    key: "PC",
    title: "Pedagogic Convenience",
    desc: "Ease of teaching, learning, explaining, and representing the form.",
  },
];

export default function CriteriaPage() {
  const [sliders, setSliders] = useState({
    IA: 6,
    CO: 5,
    F: 4,
    DI: 3,
    PS: 2,
    PC: 1,
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  function handleSlider(key, value) {
    setSliders((current) => ({ ...current, [key]: value }));
  }

  async function handleNext() {
    setIsLoading(true);
    setError(null);

    try {
      const csvText = sessionStorage.getItem("pgAnnotationCsv");
      const csvName = sessionStorage.getItem("pgAnnotationCsvName") || "annotations.csv";
      if (csvText) {
        const formData = new FormData();
        formData.append(
          "annotationFile",
          new File([csvText], csvName, { type: "text/csv" })
        );
        formData.append("sliders_json", JSON.stringify(sliders));
        const data = await fetchJson("/preference/analyze-csv", {
          method: "POST",
          body: formData,
        });
        sessionStorage.setItem("analysisResults", JSON.stringify(data));
        navigate("/results");
        return;
      }

      const stored = JSON.parse(sessionStorage.getItem("pgInput"));
      if (!stored?.target_word || !stored?.variants?.length) {
        throw new Error("No target word and variants found. Please enter the PG data first.");
      }

      const data = await fetchJson("/preference/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ ...stored, sliders }),
      });

      sessionStorage.setItem("analysisResults", JSON.stringify(data));
      navigate("/results");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Header />
      <ProgressBar currentStep={3} />
      <main className="flex-1 flex items-center justify-center px-4 pb-10">
        <section className="max-w-3xl w-full bg-white rounded-lg shadow p-8 flex flex-col gap-6">
          <BackButton />
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              Rank Preference Grammar Tenets
            </h1>
            <p className="text-gray-600 mt-1">
              Default order follows the presentation: IA, Contrastiveness, Frequency,
              Disambiguity, Phonetic Simplicity, then Pedagogic Convenience. Move sliders
              to model a different policy or classroom priority. Only the order matters:
              a higher tenet always outranks a lower one, equal sliders are ranked together,
              and 0 leaves a tenet out.
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div className="flex flex-col gap-4">
            {criteriaList.map((criterion) => (
              <label
                key={criterion.key}
                className="border border-gray-200 rounded-lg p-4 bg-gray-50"
              >
                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold">
                    {criterion.key}
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between gap-4">
                      <span className="font-semibold text-gray-900">{criterion.title}</span>
                      <span className="text-indigo-700 font-semibold">
                        {sliders[criterion.key]}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{criterion.desc}</p>
                  </div>
                </div>
                <input
                  type="range"
                  min={0}
                  max={6}
                  value={sliders[criterion.key]}
                  onChange={(event) =>
                    handleSlider(criterion.key, Number(event.target.value))
                  }
                  className="w-full accent-indigo-600 mt-4"
                  disabled={isLoading}
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0 - ignore</span>
                  <span>6 - strongest</span>
                </div>
              </label>
            ))}
          </div>

          <button
            type="button"
            className="self-end bg-indigo-600 text-white hover:bg-indigo-700"
            onClick={handleNext}
            disabled={isLoading}
          >
            {isLoading ? "Processing..." : "Generate Operability Table"}
          </button>
        </section>
      </main>
      <Footer />
    </div>
  );
}
