import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header.jsx";
import Footer from "../components/Footer.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import BackButton from "../components/BackButton.jsx";
import { postForm } from "../api.js";
import { getEvidenceFiles } from "../evidenceStore.js";

const emptyVariant = {
  ipa: "",
  count: 1,
  label: "",
  source_type: "expert",
  reviewer: "",
  confidence: 1,
  validated: true,
  notes: "",
};

const MAX_VARIANTS = 25;
const MAX_IPA_CHARS = 64;

// Turn the audio analysis (POST /pg/analyze) into rows of the variants table: one row per variant heard,
// with how often and by how many speakers, marked automatic and not yet validated by a person.
function variantsFromAudio(result) {
  const attested = [...(result.candidates || []), ...(result.superfluous || [])];
  const unit = result.unit || {};
  return attested.map((candidate) => {
    const tokens = (result.tokens || []).filter((token) => token.variant === candidate.segment);
    const speakers = new Set(tokens.map((token) => token.speaker)).size;
    const confidence = tokens.length
      ? tokens.reduce((sum, token) => sum + token.posterior, 0) / tokens.length
      : 0;
    return {
      ...emptyVariant,
      ipa: candidate.form,
      count: candidate.tokens,
      label: `${unit.label || ""} as [${candidate.segment}]`.trim(),
      source_type: "auto",
      confidence: Math.round(confidence * 100) / 100,
      validated: false,
      notes: `heard from ${speakers} speaker${speakers === 1 ? "" : "s"}`,
    };
  });
}

function loadInitialInput() {
  try {
    const stored = JSON.parse(sessionStorage.getItem("pgInput"));
    if (stored?.variants?.length) {
      return stored;
    }
  } catch {
    // Ignore malformed session data.
  }

  return {
    target_word: "",
    reference_ipa: "",
    variants: [
      { ...emptyVariant },
      { ...emptyVariant },
    ],
  };
}

export default function TargetWordPage() {
  const [form, setForm] = useState(loadInitialInput);
  const [error, setError] = useState("");
  const [audioEvidence, setAudioEvidence] = useState([]);
  const [audioFiles] = useState(getEvidenceFiles);
  const [longSpeech, setLongSpeech] = useState(false);
  const [separateSpeakers, setSeparateSpeakers] = useState(true);
  const [numSpeakers, setNumSpeakers] = useState("");
  const [audioStatus, setAudioStatus] = useState({ busy: false, summary: "", warnings: [] });
  const [csvImport, setCsvImport] = useState(() => {
    const text = sessionStorage.getItem("pgAnnotationCsv") || "";
    const name = sessionStorage.getItem("pgAnnotationCsvName") || "";
    return { text, name };
  });
  const navigate = useNavigate();

  useEffect(() => {
    try {
      setAudioEvidence(JSON.parse(sessionStorage.getItem("audioEvidence")) || []);
    } catch {
      setAudioEvidence([]);
    }
  }, []);

  function updateVariant(index, key, value) {
    setForm((current) => ({
      ...current,
      variants: current.variants.map((variant, variantIndex) =>
        variantIndex === index ? { ...variant, [key]: value } : variant
      ),
    }));
  }

  function removeVariant(index) {
    setForm((current) => ({
      ...current,
      variants: current.variants.filter((_, variantIndex) => variantIndex !== index),
    }));
  }

  async function findVariantsInAudio() {
    const word = form.target_word.trim();
    if (!word) {
      setError("Enter the target word first, so the tool knows what to listen for.");
      return;
    }
    const data = new FormData();
    audioFiles.forEach((file) => data.append("files", file));
    data.append("words", word);
    data.append("asr", longSpeech ? "true" : "false");
    data.append("diarize", longSpeech && separateSpeakers ? "true" : "false");
    const count = Number.parseInt(numSpeakers, 10);
    if (longSpeech && separateSpeakers && count >= 1 && count <= 20) {
      data.append("num_speakers", String(count));
    }
    setError("");
    setAudioStatus({ busy: true, summary: "", warnings: [] });
    try {
      const result = await postForm("/pg/analyze", data);
      const variants = variantsFromAudio(result);
      if (variants.length === 0) {
        setAudioStatus({ busy: false, summary: "", warnings: result.warnings || [] });
        setError(`No clear instance of "${word}" was found in the audio.`);
        return;
      }
      const speakers = new Set((result.tokens || []).map((token) => token.speaker)).size;
      const unit = result.unit || {};
      const validation = unit.validation || {};
      setForm((current) => ({
        ...current,
        reference_ipa: current.reference_ipa || result.canonical?.[word.toLowerCase()] || "",
        variants: variants.slice(0, MAX_VARIANTS),
      }));
      setAudioStatus({
        busy: false,
        summary:
          `${result.tokens.length} instance${result.tokens.length === 1 ? "" : "s"} of ${unit.label} /${unit.phoneme}/ ` +
          `from ${speakers} speaker${speakers === 1 ? "" : "s"}. ` +
          (validation.status === "validated"
            ? `The tool's judgement of this sound agrees with phoneticians (kappa ${validation.kappa}).`
            : "This sound is not yet validated against phoneticians' labels: listen and correct before relying on it."),
        warnings: result.warnings || [],
      });
    } catch (err) {
      setAudioStatus({ busy: false, summary: "", warnings: [] });
      setError(err.message);
    }
  }

  function handleCsvImport(file) {
    if (!file) return;
    if (file.size > 1024 * 1024) {
      setError("CSV is too large. Keep annotation imports under 1 MB.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || "");
      if (!text.includes("target_word") || !text.includes("ipa")) {
        setError("CSV must include target_word and ipa columns.");
        return;
      }
      sessionStorage.setItem("pgAnnotationCsv", text);
      sessionStorage.setItem("pgAnnotationCsvName", file.name);
      sessionStorage.removeItem("pgInput");
      setCsvImport({ text, name: file.name });
      setError("");
    };
    reader.onerror = () => setError("Could not read the CSV file.");
    reader.readAsText(file);
  }

  function handleNext() {
    if (csvImport.text) {
      navigate("/criteria");
      return;
    }

    const cleanVariants = form.variants
      .map((variant) => ({
        ...variant,
        ipa: String(variant.ipa || "").trim(),
        label: String(variant.label || "").trim(),
        notes: String(variant.notes || "").trim(),
        source_type: variant.source_type || "expert",
        reviewer: String(variant.reviewer || "").trim(),
        confidence: Number.isFinite(Number(variant.confidence))
          ? Number(variant.confidence)
          : 1,
        validated: Boolean(variant.validated),
        count: Number(variant.count) || 0,
      }))
      .filter((variant) => variant.ipa);

    if (!form.target_word.trim()) {
      setError("Enter the lexical item or target word.");
      return;
    }
    if (cleanVariants.length === 0) {
      setError("Add at least one IPA pronunciation variant.");
      return;
    }
    if (cleanVariants.length > MAX_VARIANTS) {
      setError(`Analyze at most ${MAX_VARIANTS} variants at a time.`);
      return;
    }
    if (cleanVariants.some((variant) => variant.ipa.length > MAX_IPA_CHARS)) {
      setError(`Each IPA variant must be ${MAX_IPA_CHARS} characters or fewer.`);
      return;
    }
    if (cleanVariants.some((variant) => variant.count < 0)) {
      setError("Variant counts cannot be negative.");
      return;
    }

    const payload = {
      target_word: form.target_word.trim(),
      reference_ipa: form.reference_ipa.trim(),
      variants: cleanVariants,
      audio_evidence: audioEvidence,
    };
    sessionStorage.setItem("pgInput", JSON.stringify(payload));
    sessionStorage.removeItem("pgAnnotationCsv");
    sessionStorage.removeItem("pgAnnotationCsvName");
    navigate("/criteria");
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      <Header />
      <ProgressBar currentStep={2} />
      <main className="flex-1 flex items-center justify-center px-4 pb-10">
        <section className="max-w-5xl w-full bg-white rounded-lg shadow p-8 flex flex-col gap-6">
          <BackButton />
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              Target Word and Pronunciation Variants
            </h1>
            <p className="text-gray-600 mt-1">
              Preference Grammar needs attested forms. Enter each candidate IPA
              pronunciation and how often it occurred in your data.
            </p>
          </div>

          {audioEvidence.length > 0 && audioFiles.length === 0 && (
            <div className="rounded-lg bg-indigo-50 border border-indigo-100 p-4 text-sm text-indigo-900">
              {audioEvidence.length} audio file{audioEvidence.length === 1 ? "" : "s"} attached as
              evidence. To find the variants automatically, go back and attach the audio again
              (files are not kept when the page reloads).
            </div>
          )}

          {audioFiles.length > 0 && (
            <div className="border border-indigo-200 bg-indigo-50 rounded-lg p-4 flex flex-col gap-3">
              <div>
                <h2 className="font-semibold text-indigo-950">Find Variants in the Audio</h2>
                <p className="text-sm text-indigo-900">
                  {audioFiles.length} file{audioFiles.length === 1 ? "" : "s"} attached. The tool
                  listens for the target word, decides how each speaker pronounced its sound, and
                  fills the table below. Check the rows before continuing; they are marked
                  automatic until a person validates them.
                </p>
              </div>
              <div className="flex flex-col gap-2 text-sm text-gray-800">
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="audio-kind"
                    checked={!longSpeech}
                    onChange={() => setLongSpeech(false)}
                  />
                  Each file is one recording of the target word
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="audio-kind"
                    checked={longSpeech}
                    onChange={() => setLongSpeech(true)}
                  />
                  Longer speech (podcast, interview, voice note): find the word automatically
                </label>
                {longSpeech && (
                  <div className="ml-6 flex flex-wrap items-center gap-4">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={separateSpeakers}
                        onChange={(event) => setSeparateSpeakers(event.target.checked)}
                      />
                      Separate the speakers in each file
                    </label>
                    {separateSpeakers && (
                      <label className="flex items-center gap-2">
                        Number of speakers (if known)
                        <input
                          className="border border-gray-300 rounded-md px-2 py-1 w-20 text-gray-900 bg-white"
                          type="number"
                          min="1"
                          max="20"
                          value={numSpeakers}
                          placeholder="auto"
                          onChange={(event) => setNumSpeakers(event.target.value)}
                        />
                      </label>
                    )}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  className="bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-60"
                  onClick={findVariantsInAudio}
                  disabled={audioStatus.busy}
                >
                  {audioStatus.busy ? "Listening…" : "Find Variants"}
                </button>
                {audioStatus.busy && (
                  <span className="text-sm text-indigo-900">
                    This takes about a minute for short clips, and much longer for long speech.
                  </span>
                )}
              </div>
              {audioStatus.summary && (
                <p className="text-sm text-indigo-950">{audioStatus.summary}</p>
              )}
              {audioStatus.warnings.length > 0 && (
                <ul className="text-sm text-amber-800 list-disc ml-5">
                  {audioStatus.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          <div className="border border-indigo-200 bg-indigo-50 rounded-lg p-4 flex flex-col gap-3">
            <div>
              <h2 className="font-semibold text-indigo-950">Import Expert Annotation CSV</h2>
              <p className="text-sm text-indigo-900">
                Use this when reviewers have already filled the annotation template. The
                CSV must include target_word and ipa columns.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => handleCsvImport(event.target.files?.[0])}
                className="text-sm text-gray-700"
              />
              {csvImport.text && (
                <>
                  <span className="text-sm font-medium text-indigo-950">
                    Loaded: {csvImport.name || "annotation.csv"}
                  </span>
                  <button
                    type="button"
                    className="bg-white text-red-600 border border-red-200 hover:bg-red-50"
                    onClick={() => {
                      sessionStorage.removeItem("pgAnnotationCsv");
                      sessionStorage.removeItem("pgAnnotationCsvName");
                      setCsvImport({ text: "", name: "" });
                    }}
                  >
                    Clear CSV
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-gray-700">Target word</span>
              <input
                className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                value={form.target_word}
                placeholder="e.g. think"
                onChange={(event) =>
                  setForm((current) => ({ ...current, target_word: event.target.value }))
                }
              />
            </label>

            <label className="flex flex-col gap-2">
              <span className="text-sm font-semibold text-gray-700">
                International reference IPA
              </span>
              <input
                className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                value={form.reference_ipa}
                placeholder="Optional, e.g. θɪŋk"
                onChange={(event) =>
                  setForm((current) => ({ ...current, reference_ipa: event.target.value }))
                }
              />
            </label>
          </div>

          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="hidden lg:grid grid-cols-[1fr_0.4fr_0.75fr_0.8fr_0.55fr_0.65fr_0.75fr_1fr_74px] gap-3 px-4 py-3 bg-gray-50 text-xs font-semibold uppercase text-gray-500">
              <span>IPA variant</span>
              <span>Count</span>
              <span>Source</span>
              <span>Reviewer</span>
              <span>Confidence</span>
              <span>Valid</span>
              <span>Label</span>
              <span>Notes</span>
              <span />
            </div>

            {form.variants.map((variant, index) => (
              <div
                key={index}
                className="grid grid-cols-1 lg:grid-cols-[1fr_0.4fr_0.75fr_0.8fr_0.55fr_0.65fr_0.75fr_1fr_74px] gap-3 px-4 py-3 border-t border-gray-200"
              >
                <input
                className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                value={variant.ipa}
                maxLength={MAX_IPA_CHARS}
                placeholder="/tɪŋk/"
                onChange={(event) => updateVariant(index, "ipa", event.target.value)}
              />
                <input
                  className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                  type="number"
                  min="0"
                  step="1"
                  value={variant.count}
                  onChange={(event) => updateVariant(index, "count", event.target.value)}
                />
                <select
                  className="border border-gray-300 rounded-md px-3 py-2 text-gray-900 bg-white"
                  value={variant.source_type}
                  onChange={(event) => updateVariant(index, "source_type", event.target.value)}
                >
                  <option value="expert">Expert</option>
                  <option value="auto">Automatic (from the audio)</option>
                  <option value="human">Human review</option>
                  <option value="allosaurus">Allosaurus</option>
                  <option value="mfa">MFA alignment</option>
                  <option value="phonemizer">Phonemizer</option>
                  <option value="asr">ASR-derived</option>
                  <option value="imported">Imported</option>
                </select>
                <input
                  className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                  value={variant.reviewer}
                  placeholder="Reviewer"
                  onChange={(event) => updateVariant(index, "reviewer", event.target.value)}
                />
                <input
                  className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={variant.confidence}
                  onChange={(event) => updateVariant(index, "confidence", event.target.value)}
                />
                <label className="flex items-center gap-2 text-gray-700">
                  <input
                    type="checkbox"
                    checked={variant.validated}
                    onChange={(event) =>
                      updateVariant(index, "validated", event.target.checked)
                    }
                  />
                  <span className="text-sm">Validated</span>
                </label>
                <input
                  className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                  value={variant.label}
                  placeholder="Label"
                  onChange={(event) => updateVariant(index, "label", event.target.value)}
                />
                <input
                  className="border border-gray-300 rounded-md px-3 py-2 text-gray-900"
                  value={variant.notes}
                  placeholder="speaker group, source, context"
                  onChange={(event) => updateVariant(index, "notes", event.target.value)}
                />
                <button
                  type="button"
                  className="bg-white text-red-600 border border-red-200 hover:bg-red-50"
                  onClick={() => removeVariant(index)}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <button
              type="button"
              className="bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
              onClick={() =>
                setForm((current) => ({
                  ...current,
                  variants:
                    current.variants.length >= MAX_VARIANTS
                      ? current.variants
                      : [...current.variants, { ...emptyVariant }],
                }))
              }
              disabled={form.variants.length >= MAX_VARIANTS}
            >
              Add Variant
            </button>
            <button
              type="button"
              className="bg-indigo-600 text-white hover:bg-indigo-700"
              onClick={handleNext}
            >
              Continue to Ranking
            </button>
          </div>

          {error && <p className="text-sm text-red-600 text-right">{error}</p>}
        </section>
      </main>
      <Footer />
    </div>
  );
}
