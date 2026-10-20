import {
  OverrideRow,
  PGSettings,
  PGTableau,
  PGTableauRow,
  PGTenet,
  PGUnit,
  RankingItem,
  SettingsForm,
  SettingsValues,
} from "../types/pg";

// The six PG tenets in their default order; /pg/units sends the same list
export const PG_TENETS: PGTenet[] = [
  { key: "I-Ac", name: "International acceptance" },
  { key: "ContR", name: "Contrastiveness" },
  { key: "FreQ", name: "Frequency" },
  { key: "DisaM", name: "Disambiguity" },
  { key: "Pho-S", name: "Phonetic simplicity" },
  { key: "Ped-C", name: "Pedagogic convenience" },
];

export const DEFAULT_RANKING =
  "I-Ac >> ContR >> FreQ >> DisaM >> Pho-S >> Ped-C";

// Operability table headings, which are also the column keys of tableau.rows
export const TENET_COLUMN_LABELS: Record<string, string> = {
  "I-Ac": "*No I-Ac",
  ContR: "*No ContR",
  FreQ: "*No FreQ",
  DisaM: "DisaM",
  "Pho-S": "*Pho-S",
  "Ped-C": "*Ped-C",
};

// The server's defaults (pg/tenets.py Settings)
export const DEFAULT_SETTINGS: SettingsForm = {
  freq_threshold: "0.2",
  freq_weighting: "tokens",
  freq_mode: "threshold",
  min_tokens: "3",
  min_speakers: "2",
  disam_min_pairs: "1",
  phos_world_threshold: "0.15",
  review_below: "0.75",
  calibrated: true,
};

// Short names for the output tiers, from most to least formal
const TIER_LABELS: Record<string, string> = {
  "preferred (formal standard)": "Formal standard",
  "allophone (formal inventory)": "Allophone",
  "outer (informal) norm": "Informal norm",
};

export const tierLabel = (tier: string) => TIER_LABELS[tier] ?? tier;

// Classifier validation: a unit without a validation result (older servers) is not validated
export const isValidated = (unit: PGUnit) =>
  unit.validation?.status === "validated";

export const validationLabel = (unit: PGUnit) => {
  if (!isValidated(unit)) return "Not validated";
  const kappa = unit.validation?.kappa;
  return typeof kappa === "number"
    ? `Validated (κ ${kappa.toFixed(2)})`
    : "Validated";
};

let lastId = 0;
// crypto.randomUUID needs a secure context, so a counter keeps ids working over plain http
export const nextId = (prefix: string) => `${prefix}-${++lastId}`;

// Ranking: "A >> B, C" ranks A above the stratum {B, C}, whose tenets are unranked

export const parseRanking = (ranking: string): string[][] =>
  ranking
    .split(">>")
    .map((stratum) =>
      stratum
        .split(",")
        .map((tenet) => tenet.trim())
        .filter(Boolean)
    )
    .filter((stratum) => stratum.length > 0);

export const rankingItemsFrom = (
  ranking: string,
  tenets: PGTenet[]
): RankingItem[] => {
  const known = new Set(tenets.map((tenet) => tenet.key));
  const items: RankingItem[] = [];
  for (const stratum of parseRanking(ranking)) {
    stratum
      .filter((key) => known.has(key) && !items.some((item) => item.key === key))
      .forEach((key, i) =>
        items.push({ key, enabled: true, tiedWithAbove: i > 0 })
      );
  }
  // Tenets the ranking leaves out are deleted, but stay listed so they can be restored
  for (const { key } of tenets) {
    if (!items.some((item) => item.key === key)) {
      items.push({ key, enabled: false, tiedWithAbove: false });
    }
  }
  return items;
};

// Strata are worked out over the whole list, deleted tenets included, so deleting a
// tenet never merges the strata around it and restoring it is an exact undo
export const rankingStrata = (items: RankingItem[]): string[][] => {
  const strata: RankingItem[][] = [];
  items.forEach((item, i) => {
    if (item.tiedWithAbove && i > 0) {
      strata[strata.length - 1].push(item);
    } else {
      strata.push([item]);
    }
  });
  return strata
    .map((stratum) =>
      stratum.filter((item) => item.enabled).map((item) => item.key)
    )
    .filter((stratum) => stratum.length > 0);
};

// Swap a tenet with its neighbour. Every tenet whose neighbour above changes is ranked
// strictly again, so a move never silently pulls a tenet into another stratum
export const moveRankingItem = (
  items: RankingItem[],
  index: number,
  delta: -1 | 1
): RankingItem[] | null => {
  const target = index + delta;
  if (target < 0 || target >= items.length) return null;
  const next = [...items];
  next[index] = items[target];
  next[target] = items[index];
  const below = Math.max(index, target) + 1;
  return next.map((item, i) =>
    i === index || i === target || i === below
      ? { ...item, tiedWithAbove: false }
      : item
  );
};

export const formatRanking = (strata: string[][]): string =>
  strata.map((stratum) => stratum.join(", ")).join(" >> ");

// Operability table

export interface TableauColumn {
  key: string; // tenet key, e.g. "I-Ac"
  label: string; // heading and row key, e.g. "*No I-Ac"
  name: string;
  stratum: number;
  startsStratum: boolean;
}

export const tableauColumns = (
  tableau: PGTableau,
  tenets: PGTenet[]
): TableauColumn[] =>
  tableau.ranking.flatMap((stratum, s) =>
    stratum.map((key, i) => ({
      key,
      label: TENET_COLUMN_LABELS[key] ?? key,
      name: tenets.find((tenet) => tenet.key === key)?.name ?? key,
      stratum: s,
      startsStratum: i === 0,
    }))
  );

export const tableauCell = (row: PGTableauRow, column: TableauColumn) =>
  String(row[column.label] ?? "");

// The stratum holding a candidate's fatal mark ("!"); cells in later strata are shaded
export const eliminatedAt = (
  row: PGTableauRow,
  columns: TableauColumn[]
): number | null => {
  const fatal = columns.find((column) =>
    tableauCell(row, column).includes("!")
  );
  return fatal ? fatal.stratum : null;
};

export const describeMarks = (cell: string) => {
  const count = (cell.match(/\*/g) ?? []).length;
  const marks =
    count === 0
      ? "no violations"
      : count === 1
      ? "1 violation"
      : `${count} violations`;
  return cell.includes("!") ? `${marks}, fatal` : marks;
};

// Candidates are lettered a., b., c. as in PG operability tables
export const candidateLetter = (index: number) =>
  String.fromCharCode(97 + index);

// Settings: only values that differ from the defaults are sent, so the server's own
// defaults apply otherwise and a renamed setting cannot break a request nobody customised

// Labels of the numeric settings, shared by the form and its error messages
export const SETTING_LABELS = {
  freq_threshold: "FreQ threshold",
  min_tokens: "Minimum tokens",
  min_speakers: "Minimum speakers",
  disam_min_pairs: "DisaM minimum pairs",
  phos_world_threshold: "Pho-S: rare in the world's languages below",
  review_below: "Review threshold",
} as const;

const NUMBER_SETTINGS = [
  ["freq_threshold", "fraction"],
  ["min_tokens", "count"],
  ["min_speakers", "count"],
  ["disam_min_pairs", "count"],
  ["phos_world_threshold", "fraction"],
  ["review_below", "fraction"],
] as const;

export const buildSettings = (
  form: SettingsForm,
  overrides: OverrideRow[]
):
  | { settings: PGSettings; values: SettingsValues; error: null }
  | { settings: null; values: null; error: string } => {
  const settings: PGSettings = {};
  const values: Partial<SettingsValues> = {
    freq_weighting: form.freq_weighting,
    freq_mode: form.freq_mode,
    calibrated: form.calibrated,
  };
  for (const [field, kind] of NUMBER_SETTINGS) {
    const label = `“${SETTING_LABELS[field]}”`;
    const text = form[field].trim();
    const value = Number(text);
    const valid =
      kind === "fraction"
        ? Number.isFinite(value) && value >= 0 && value <= 1
        : Number.isInteger(value) && value >= 0;
    if (!text || !valid) {
      return {
        settings: null,
        values: null,
        error:
          kind === "fraction"
            ? `${label} must be a number from 0 to 1`
            : `${label} must be a whole number (0 or more)`,
      };
    }
    values[field] = value;
    if (value !== Number(DEFAULT_SETTINGS[field])) settings[field] = value;
  }
  if (form.freq_weighting !== DEFAULT_SETTINGS.freq_weighting) {
    settings.freq_weighting = form.freq_weighting;
  }
  if (form.freq_mode !== DEFAULT_SETTINGS.freq_mode) {
    settings.freq_mode = form.freq_mode;
  }
  if (form.calibrated !== DEFAULT_SETTINGS.calibrated) {
    settings.calibrated = form.calibrated;
  }

  const used = overrides.filter((row) => row.segment.trim());
  for (const row of used) {
    const count = Number(row.count);
    if (!row.count.trim() || !Number.isInteger(count) || count < 0) {
      return {
        settings: null,
        values: null,
        error: `The override for [${row.segment.trim()}] needs a whole number of marks (0 or more)`,
      };
    }
  }
  if (used.length) {
    settings.overrides = Object.fromEntries(
      used.map((row) => [`${row.segment.trim()}|${row.tenet}`, Number(row.count)])
    );
  }
  return { settings, values: values as SettingsValues, error: null };
};

// Words and recordings

// Commas or spaces separate words; the server lower-cases them too
export const parseWords = (input: string): string[] =>
  Array.from(
    new Set(
      input
        .split(/[\s,]+/)
        .map((word) => word.trim().toLowerCase())
        .filter(Boolean)
    )
  );

// With several target words the server matches a single-word recording to its word by file name
export const fileNameHasWord = (fileName: string, words: string[]) =>
  words.some((word) => fileName.toLowerCase().includes(word));

// A transcript of "auto" asks the server to find the words by speech recognition
export const isAutoTranscript = (transcript: string) =>
  transcript.trim().toLowerCase() === "auto";

// Mirrors the server's aligner, which keeps only letters a-z and apostrophes
export const transcriptHasWord = (transcript: string, words: string[]) => {
  const spoken = transcript
    .toLowerCase()
    .replace(/’/g, "'")
    .replace(/[^a-z' ]+/g, " ")
    .split(" ");
  return words.some((word) => spoken.includes(word));
};

const AUDIO_EXTENSIONS = /\.(wav|mp3|flac|ogg|oga|opus|webm|m4a|mp4|aac|aiff?)$/i;

export const isAudioFile = (file: File) =>
  file.type.startsWith("audio/") || AUDIO_EXTENSIONS.test(file.name);

// Transcripts and speakers are keyed by file name on the server, so names must be unique
export const uniqueFileName = (name: string, taken: Set<string>) => {
  if (!taken.has(name)) return name;
  const dot = name.lastIndexOf(".");
  const stem = dot > 0 ? name.slice(0, dot) : name;
  const extension = dot > 0 ? name.slice(dot) : "";
  const numbered = stem.match(/^(.*)-(\d+)$/);
  const base = numbered ? numbered[1] : stem;
  let n = numbered ? Number(numbered[2]) + 1 : 2;
  while (taken.has(`${base}-${n}${extension}`)) n++;
  return `${base}-${n}${extension}`;
};

export const extensionForMimeType = (type: string) => {
  if (type.includes("ogg")) return "ogg";
  if (type.includes("mp4") || type.includes("aac")) return "m4a";
  if (type.includes("wav")) return "wav";
  return "webm";
};

// Formatting

export const formatPercent = (share: number) => `${Math.round(share * 100)}%`;

export const formatDuration = (seconds: number) => {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
};

export const formatFileSize = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;

export const fileSlug = (text: string) =>
  text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "") || "analysis";

// Downloads

const BYTE_ORDER_MARK = String.fromCharCode(0xfeff);

const DOWNLOAD_TYPES: Record<string, string> = {
  csv: "text/csv;charset=utf-8",
  html: "text/html;charset=utf-8",
  json: "application/json;charset=utf-8",
};

export const downloadText = (fileName: string, content: string) => {
  const extension = fileName.split(".").pop() ?? "";
  // A byte-order mark makes spreadsheet apps read the IPA in CSV files as UTF-8
  const body = extension === "csv" ? `${BYTE_ORDER_MARK}${content}` : content;
  const url = URL.createObjectURL(
    new Blob([body], {
      type: DOWNLOAD_TYPES[extension] ?? "text/plain;charset=utf-8",
    })
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Give the browser a moment to start the download before releasing the blob
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};
