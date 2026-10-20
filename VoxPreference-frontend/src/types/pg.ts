// Shapes of the Preference Grammar (PG) endpoints, /pg/units and /pg/analyze

// Result of testing the variant classifier on human-labelled tokens of a unit
export interface PGValidation {
  status: "validated" | "not validated";
  kappa?: number; // Cohen's kappa against the human labels
  accuracy?: number;
  majority_baseline?: number; // accuracy of always guessing the commonest variant
  balanced_accuracy?: number;
  share_error?: number; // mean absolute error of the variant shares
  calibrated?: boolean;
  note: string;
}

export interface PGUnit {
  key: string;
  label: string; // as shown in the operability table, e.g. "<th>"
  phoneme: string; // the reference segment, e.g. "θ"
  candidates: string[]; // realisations tested for in the audio
  international: string[]; // realisations within international norms (I-Ac)
  pedagogic_difficult: string[]; // realisations marked as hard to teach (Ped-C)
  lexical_set: string;
  notes: string;
  sources: string[];
  validation?: PGValidation; // missing from older servers, which counts as not validated
}

export interface PGTenet {
  key: string;
  name: string;
}

export interface PGUnitsResponse {
  units: Record<string, PGUnit>;
  tenets: PGTenet[];
  default_ranking: string;
}

export interface PGToken {
  recording: string;
  speaker: string;
  word: string;
  start: number;
  end: number;
  variant: string;
  posterior: number;
  scores: Record<string, number>;
  realised: string; // best-fitting form of the whole word, in IPA
  heard: string; // free phone decoding of the word
  primary: string;
  secondary: string;
  review: boolean;
}

export interface PGClusters {
  categories: string[];
  contrast_matrix: number[][];
  separation: Record<string, number | null>;
  subclusters: Record<string, number>;
}

export interface PGViolation {
  count: number;
  reason: string;
  source: string;
}

export interface PGCandidate {
  form: string;
  segment: string;
  tokens: number;
  share: number; // of tokens, or averaged over speakers when FreQ counts speakers
  // "preferred (formal standard)" | "allophone (formal inventory)" | "outer (informal) norm"
  tier?: string;
  violations: Record<string, PGViolation>;
}

// A variant attested too rarely to compete (fewer than min_tokens tokens or min_speakers speakers)
export interface PGVariantCount {
  form: string;
  segment: string;
  tokens: number;
  share: number;
}

// How often each variant came out preferred when the speakers and each token's variant
// were resampled (bootstrap)
export interface PGStability {
  resamples: number;
  speakers: number;
  preferred_rate: Record<string, number>; // segment -> share of resamples
}

// Tenet columns are keyed by their heading, e.g. "*No I-Ac", and hold the marks ("*", "*!")
export interface PGTableauRow {
  candidate: string;
  segment: string;
  tokens: number;
  share: number;
  preferred: boolean;
  [column: string]: string | number | boolean;
}

export interface PGTableau {
  ranking: string[][];
  rows: PGTableauRow[];
  markdown: string;
  html: string;
  tie: boolean;
}

export interface PGAnalysisResult {
  success: true;
  words: string[];
  unit: PGUnit;
  canonical: Record<string, string>;
  tokens: PGToken[];
  clusters: PGClusters | null;
  candidates: PGCandidate[];
  superfluous?: PGVariantCount[];
  tableau: PGTableau | null;
  preferred: string[];
  stability?: PGStability | null; // null with fewer than 3 speakers
  warnings: string[];
  files: Record<string, string>;
}

export type FreqWeighting = "tokens" | "speakers";

// "threshold": variants below the FreQ threshold get a mark; "most_frequent": every variant but the commonest does
export type FreqMode = "threshold" | "most_frequent";

export interface PGSettings {
  freq_threshold?: number;
  freq_weighting?: FreqWeighting;
  freq_mode?: FreqMode;
  min_tokens?: number;
  min_speakers?: number;
  disam_min_pairs?: number;
  phos_world_threshold?: number;
  review_below?: number;
  calibrated?: boolean;
  overrides?: Record<string, number>; // "<segment>|<tenet>" -> violation marks
}

// Every setting as used for a run, whether sent or left at its default
export type SettingsValues = Required<Omit<PGSettings, "overrides">>;

// Form state of the PG view

export interface RecordingItem {
  id: string;
  file: File;
  origin: "upload" | "recording";
  speaker: string;
  transcript: string;
}

export interface SettingsForm {
  freq_threshold: string;
  freq_weighting: FreqWeighting;
  freq_mode: FreqMode;
  min_tokens: string;
  min_speakers: string;
  disam_min_pairs: string;
  phos_world_threshold: string;
  review_below: string;
  calibrated: boolean;
}

export interface OverrideRow {
  id: string;
  segment: string;
  tenet: string;
  count: string;
}

export interface RankingItem {
  key: string;
  enabled: boolean;
  tiedWithAbove: boolean; // unranked with the tenet listed above it (same stratum)
}

export interface AnalysisOutcome {
  id: string;
  data: PGAnalysisResult;
  files: Map<string, File>; // the submitted recordings by name, for listening to tokens
  settings: SettingsValues;
  unlabelledRecordings: number; // recordings without a speaker id, which count as speakers of their own
}
