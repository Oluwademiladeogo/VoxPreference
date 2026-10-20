import { FormEvent, useEffect, useRef, useState } from "react";
import { API_CONFIG } from "../config/api";
import ApiService from "../services/api";
import {
  AnalysisOutcome,
  OverrideRow,
  PGUnit,
  PGUnitsResponse,
  RankingItem,
  RecordingItem,
  SettingsForm,
} from "../types/pg";
import {
  DEFAULT_RANKING,
  DEFAULT_SETTINGS,
  PG_TENETS,
  buildSettings,
  formatRanking,
  isAutoTranscript,
  isValidated,
  nextId,
  parseWords,
  rankingItemsFrom,
  rankingStrata,
  validationLabel,
} from "../utils/pg";
import AdvancedSettings from "./pg/AdvancedSettings";
import AnalysisProgress from "./pg/AnalysisProgress";
import AnalysisResults from "./pg/AnalysisResults";
import Icon from "./pg/Icon";
import RankingEditor from "./pg/RankingEditor";
import RecordingsInput from "./pg/RecordingsInput";
import UnitSummary from "./pg/UnitSummary";

interface ErrorState {
  message: string;
  type: "validation" | "analysis" | "cancelled";
}

interface RunState {
  startedAt: number;
  files: number;
  words: string[];
  unscripted: boolean;
}

const unitOptionLabel = (unit: PGUnit) =>
  `${
    unit.label === unit.key
      ? `${unit.key} · /${unit.phoneme}/`
      : `${unit.key} · ${unit.label} /${unit.phoneme}/`
  } · ${validationLabel(unit)}`;

const inputClass =
  "w-full px-4 py-3 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent";
const sectionHeadingClass = "text-xl font-semibold text-gray-900";

const PGAnalysis = () => {
  const [catalog, setCatalog] = useState<PGUnitsResponse | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogRequest, setCatalogRequest] = useState(0);
  const [wordsInput, setWordsInput] = useState("");
  const [unitKey, setUnitKey] = useState("");
  const [ranking, setRanking] = useState<RankingItem[]>(() =>
    rankingItemsFrom(DEFAULT_RANKING, PG_TENETS)
  );
  const [recordings, setRecordings] = useState<RecordingItem[]>([]);
  const [asr, setAsr] = useState(false);
  const [diarize, setDiarize] = useState(true);
  const [numSpeakers, setNumSpeakers] = useState("");
  const [settings, setSettings] = useState<SettingsForm>(DEFAULT_SETTINGS);
  const [overrides, setOverrides] = useState<OverrideRow[]>([]);
  const [error, setError] = useState<ErrorState | null>(null);
  const [run, setRun] = useState<RunState | null>(null);
  const [outcome, setOutcome] = useState<AnalysisOutcome | null>(null);
  const rankingEdited = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);

  const tenets = catalog?.tenets ?? PG_TENETS;
  const defaultRanking = catalog?.default_ranking ?? DEFAULT_RANKING;
  const units = catalog ? Object.values(catalog.units) : [];
  const selectedUnit = unitKey ? catalog?.units[unitKey] : undefined;
  const words = parseWords(wordsInput);
  const unvalidated = !!selectedUnit && !isValidated(selectedUnit);
  // A variant can be any IPA phone, so overrides also suggest those heard in the last run
  const lastRun =
    outcome && (!unitKey || outcome.data.unit.key === unitKey)
      ? outcome.data
      : null;
  const overrideVariants = Array.from(
    new Set([
      ...(selectedUnit?.candidates ?? lastRun?.unit.candidates ?? []),
      ...(lastRun?.tokens.map((token) => token.variant) ?? []),
    ])
  );

  useEffect(() => {
    let ignore = false;
    ApiService.getPGUnits()
      .then((data) => {
        if (ignore) return;
        setCatalog(data);
        setCatalogError(null);
        // Use the server's default ranking unless the user has already edited it
        if (!rankingEdited.current) {
          setRanking(rankingItemsFrom(data.default_ranking, data.tenets));
        }
      })
      .catch((err) => {
        if (!ignore) {
          setCatalogError(
            err instanceof Error ? err.message : "Unknown error occurred"
          );
        }
      });
    return () => {
      ignore = true;
    };
  }, [catalogRequest]);

  // Stop waiting for a running analysis if the view goes away
  useEffect(() => () => abortRef.current?.abort(), []);

  // Bring the new results to the top and move keyboard and screen-reader users there
  useEffect(() => {
    const heading = resultsHeadingRef.current;
    if (!outcome || !heading) return;
    heading.scrollIntoView({ block: "start" });
    heading.focus({ preventScroll: true });
  }, [outcome]);

  const handleRankingChange = (items: RankingItem[]) => {
    rankingEdited.current = true;
    setRanking(items);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!words.length) {
      setError({ message: "Enter at least one target word", type: "validation" });
      return;
    }
    if (!recordings.length) {
      setError({ message: "Add at least one recording", type: "validation" });
      return;
    }
    const strata = rankingStrata(ranking);
    if (!strata.length) {
      setError({
        message: "Keep at least one tenet in the ranking",
        type: "validation",
      });
      return;
    }
    const built = buildSettings(settings, overrides);
    if (built.error !== null) {
      setError({ message: built.error, type: "validation" });
      return;
    }

    const formData = new FormData();
    recordings.forEach((item) => formData.append("files", item.file));
    formData.append("words", words.join(","));
    if (unitKey) formData.append("unit", unitKey);
    formData.append("ranking", formatRanking(strata));
    // Transcripts and speakers are keyed by file name
    const transcripts = Object.fromEntries(
      recordings
        .filter((item) => item.transcript.trim())
        .map((item) => [item.file.name, item.transcript.trim()])
    );
    if (Object.keys(transcripts).length) {
      formData.append("transcripts", JSON.stringify(transcripts));
    }
    const speakers = Object.fromEntries(
      recordings
        .filter((item) => item.speaker.trim())
        .map((item) => [item.file.name, item.speaker.trim()])
    );
    if (Object.keys(speakers).length) {
      formData.append("speakers", JSON.stringify(speakers));
    }
    if (Object.keys(built.settings).length) {
      formData.append("settings", JSON.stringify(built.settings));
    }
    formData.append("asr", asr ? "true" : "false");
    formData.append("diarize", diarize ? "true" : "false");
    const speakerCount = Number.parseInt(numSpeakers, 10);
    if (diarize && speakerCount >= 1 && speakerCount <= 20) {
      formData.append("num_speakers", String(speakerCount));
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setRun({
      startedAt: Date.now(),
      files: recordings.length,
      words,
      unscripted:
        recordings.some((item) => isAutoTranscript(item.transcript)) ||
        (asr && recordings.some((item) => !item.transcript.trim())),
    });

    try {
      const data = await ApiService.analyzePG(formData, controller.signal);
      setOutcome({
        id: nextId("analysis"),
        data,
        files: new Map(recordings.map((item) => [item.file.name, item.file])),
        settings: built.values,
        unlabelledRecordings: recordings.length - Object.keys(speakers).length,
      });
    } catch (err) {
      console.error("Error:", err);
      if (controller.signal.aborted) {
        setError({
          message:
            "Analysis cancelled. The server may still finish the job, but its results will not be shown.",
          type: "cancelled",
        });
      } else if (err instanceof TypeError) {
        setError({
          message:
            "Could not reach the analysis server. Check that the backend is running and try again.",
          type: "analysis",
        });
      } else if (err instanceof Error && err.message.startsWith("Request timed out")) {
        setError({
          message: `The analysis took longer than ${
            API_CONFIG.PG_ANALYZE_TIMEOUT / 60000
          } minutes, so the app stopped waiting. Try fewer recordings at a time.`,
          type: "analysis",
        });
      } else {
        setError({
          message: err instanceof Error ? err.message : "Unknown error occurred",
          type: "analysis",
        });
      }
    } finally {
      abortRef.current = null;
      setRun(null);
    }
  };

  return (
    // relative: absolutely positioned descendants (sr-only text) must scroll and clip
    // inside this container instead of stretching the whole page
    <div className="relative h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto p-4 md:p-8 space-y-6">
        <header className="space-y-3">
          <h2 className="text-2xl md:text-3xl font-bold text-blue-700">
            Preference Grammar analysis
          </h2>
          <p className="text-gray-700 max-w-3xl">
            Preference Grammar (C.U.C. Ugorji) standardises pronunciation in
            New Englishes such as Nigerian English. Recordings of target words
            from many speakers show which variants of a sound people actually
            produce; the variants are then ranked on six tenets to choose the
            preferred pronunciation.
          </p>
          <details className="max-w-3xl text-sm text-gray-700">
            <summary className="cursor-pointer select-none font-semibold text-blue-700 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
              How the analysis works
            </summary>
            <ol className="mt-2 list-decimal pl-5 space-y-1">
              <li>
                The server finds each target word in the recordings and decides
                which variant of the sound each speaker produced, e.g. &lt;th&gt;
                in “think” as <span className="font-ipa">[θ]</span>,{" "}
                <span className="font-ipa">[t]</span> or{" "}
                <span className="font-ipa">[s]</span>.
              </li>
              <li>
                The attested variants become candidates and receive violation
                marks for International acceptance (I-Ac), Contrastiveness
                (ContR), Frequency (FreQ), Disambiguity (DisaM), Phonetic
                simplicity (Pho-S) and Pedagogic convenience (Ped-C).
              </li>
              <li>
                The operability table checks the candidates tenet by tenet in
                your ranking. A candidate drops out at its first fatal mark,
                and the one left standing is the preferred pronunciation.
              </li>
            </ol>
          </details>
        </header>

        <form
          onSubmit={handleSubmit}
          noValidate
          className="bg-white rounded-lg shadow-md p-4 md:p-8 space-y-8"
        >
          <section aria-labelledby="pg-target-heading" className="space-y-4">
            <h3 id="pg-target-heading" className={sectionHeadingClass}>
              1. What to analyse
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label
                  htmlFor="pg-words"
                  className="block font-semibold text-gray-700"
                >
                  Target word(s)
                </label>
                <input
                  id="pg-words"
                  type="text"
                  value={wordsInput}
                  onChange={(e) => setWordsInput(e.target.value)}
                  placeholder="think, three, thank"
                  autoComplete="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  aria-describedby="pg-words-help"
                  className={inputClass}
                />
                <p id="pg-words-help" className="text-sm text-gray-600">
                  Separate words with commas. Every word should contain the
                  sound under study.
                </p>
              </div>
              <div className="space-y-2">
                <label
                  htmlFor="pg-unit"
                  className="block font-semibold text-gray-700"
                >
                  Sound under study
                </label>
                <select
                  id="pg-unit"
                  value={unitKey}
                  onChange={(e) => setUnitKey(e.target.value)}
                  className={inputClass}
                >
                  <option value="">Infer from the words</option>
                  {units.map((unit) => (
                    <option key={unit.key} value={unit.key}>
                      {unitOptionLabel(unit)}
                    </option>
                  ))}
                </select>
                {catalogError && (
                  <div
                    role="alert"
                    className="flex flex-wrap items-center gap-2 text-sm text-red-700"
                  >
                    <span>{`Could not load the units from the server (${catalogError}).`}</span>
                    <button
                      type="button"
                      onClick={() => setCatalogRequest((n) => n + 1)}
                      className="font-semibold underline hover:text-red-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 rounded"
                    >
                      Retry
                    </button>
                  </div>
                )}
              </div>
            </div>
            <UnitSummary unit={selectedUnit} />
          </section>

          <section
            aria-labelledby="pg-recordings-heading"
            className="space-y-4"
          >
            <h3 id="pg-recordings-heading" className={sectionHeadingClass}>
              2. Recordings
            </h3>
            <p className="text-sm text-gray-600">
              Add recordings of the target words from as many speakers as you
              can.{" "}
              {asr
                ? "Files without a transcript are searched for the target words automatically."
                : "A file without a transcript is treated as a recording of a single target word."}
            </p>
            <RecordingsInput
              items={recordings}
              onChange={setRecordings}
              words={words}
              asr={asr}
              onAsrChange={setAsr}
              diarize={diarize}
              onDiarizeChange={setDiarize}
              numSpeakers={numSpeakers}
              onNumSpeakersChange={setNumSpeakers}
            />
          </section>

          <section aria-labelledby="pg-ranking-heading" className="space-y-4">
            <h3 id="pg-ranking-heading" className={sectionHeadingClass}>
              3. Tenet ranking
            </h3>
            <RankingEditor
              items={ranking}
              onChange={handleRankingChange}
              tenets={tenets}
              defaultRanking={defaultRanking}
            />
          </section>

          <AdvancedSettings
            settings={settings}
            onSettingsChange={setSettings}
            overrides={overrides}
            onOverridesChange={setOverrides}
            tenets={tenets}
            variants={overrideVariants}
          />

          {error && (
            <div
              role="alert"
              className={`p-4 rounded-lg border ${
                error.type === "cancelled"
                  ? "bg-gray-50 border-gray-200"
                  : "bg-red-50 border-red-200"
              }`}
            >
              <div className="flex items-start">
                <Icon
                  name="error"
                  className={`w-5 h-5 mr-2 shrink-0 ${
                    error.type === "cancelled" ? "text-gray-600" : "text-red-500"
                  }`}
                />
                <p
                  className={
                    error.type === "cancelled" ? "text-gray-800" : "text-red-700"
                  }
                >
                  {error.message}
                </p>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {unvalidated && (
              <div
                id="pg-unvalidated-caution"
                className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
              >
                <Icon name="warning" className="w-5 h-5 shrink-0" />
                <p>
                  <strong>Not validated.</strong> The classifier's labels for
                  this sound have not passed a human-labelled test. Treat the
                  shares and the preferred form as provisional and check tokens
                  by ear.
                </p>
              </div>
            )}
            <button
              type="submit"
              disabled={!!run}
              aria-describedby={
                unvalidated ? "pg-unvalidated-caution" : undefined
              }
              className={`w-full py-3 rounded-lg font-semibold transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-600 ${
                run
                  ? "bg-gray-300 text-gray-700 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 text-white"
              }`}
            >
              {run ? "Analysing..." : "Run analysis"}
            </button>
            {run && (
              <AnalysisProgress
                startedAt={run.startedAt}
                files={run.files}
                words={run.words}
                unscripted={run.unscripted}
                onCancel={() => abortRef.current?.abort()}
              />
            )}
          </div>
        </form>

        {outcome && (
          <AnalysisResults
            outcome={outcome}
            tenets={tenets}
            headingRef={resultsHeadingRef}
          />
        )}
      </div>
    </div>
  );
};

export default PGAnalysis;
