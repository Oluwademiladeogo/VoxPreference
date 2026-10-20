import {
  FreqMode,
  FreqWeighting,
  OverrideRow,
  PGTenet,
  SettingsForm,
} from "../../types/pg";
import { DEFAULT_SETTINGS, SETTING_LABELS, nextId } from "../../utils/pg";
import Icon from "./Icon";

interface AdvancedSettingsProps {
  settings: SettingsForm;
  onSettingsChange: (settings: SettingsForm) => void;
  overrides: OverrideRow[];
  onOverridesChange: (overrides: OverrideRow[]) => void;
  tenets: PGTenet[];
  variants: string[]; // suggested for overrides: the unit's candidates and variants heard last run
}

interface NumberField {
  key: keyof typeof SETTING_LABELS;
  help: string;
  fraction?: boolean; // 0-1, otherwise a whole number
}

const FREQ_FIELD: NumberField = {
  key: "freq_threshold",
  help: "*No FreQ when a variant's share is below this (0–1).",
  fraction: true,
};

const OTHER_FIELDS: NumberField[] = [
  {
    key: "min_tokens",
    help: "A variant needs at least this many tokens to compete; rarer variants are listed as too rare to compete.",
  },
  {
    key: "min_speakers",
    help: "A variant also needs tokens from at least this many speakers to compete.",
  },
  {
    key: "disam_min_pairs",
    help: "DisaM when using the variant would make at least this many common word pairs sound alike.",
  },
  {
    key: "phos_world_threshold",
    help: "*Pho-S when fewer than this share of the world's languages have the variant (0–1). Variants absent from most substrate languages are marked regardless.",
    fraction: true,
  },
  {
    key: "review_below",
    help: "Tokens whose variant posterior is below this are flagged to check by ear (0–1).",
    fraction: true,
  },
];

const inputClass =
  "w-full px-3 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent";

const AdvancedSettings = ({
  settings,
  onSettingsChange,
  overrides,
  onOverridesChange,
  tenets,
  variants,
}: AdvancedSettingsProps) => {
  const updateOverride = (id: string, changes: Partial<OverrideRow>) => {
    onOverridesChange(
      overrides.map((row) => (row.id === id ? { ...row, ...changes } : row))
    );
  };

  const addOverride = () => {
    onOverridesChange([
      ...overrides,
      {
        id: nextId("override"),
        segment: "",
        tenet: tenets[0]?.key ?? "",
        count: "1",
      },
    ]);
  };

  const numberField = (field: NumberField) => (
    <div key={field.key} className="space-y-1">
      <label
        htmlFor={`pg-setting-${field.key}`}
        className="block text-sm font-semibold text-gray-700"
      >
        {SETTING_LABELS[field.key]}
      </label>
      <input
        id={`pg-setting-${field.key}`}
        type="number"
        inputMode={field.fraction ? "decimal" : "numeric"}
        min="0"
        max={field.fraction ? "1" : undefined}
        step={field.fraction ? "0.05" : "1"}
        value={settings[field.key]}
        onChange={(e) =>
          onSettingsChange({ ...settings, [field.key]: e.target.value })
        }
        aria-describedby={`pg-setting-${field.key}-help`}
        className={inputClass}
      />
      <p id={`pg-setting-${field.key}-help`} className="text-xs text-gray-600">
        {field.help} Default {DEFAULT_SETTINGS[field.key]}.
      </p>
    </div>
  );

  return (
    <details className="rounded-lg border border-gray-200">
      <summary className="cursor-pointer select-none px-4 py-3 font-semibold text-gray-800 rounded-lg hover:bg-gray-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
        Advanced settings
        <span className="ml-2 font-normal text-sm text-gray-600">
          thresholds and expert overrides
        </span>
      </summary>

      <div className="px-4 pb-4 pt-2 space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {numberField(FREQ_FIELD)}
          <div className="space-y-1">
            <label
              htmlFor="pg-setting-freq_weighting"
              className="block text-sm font-semibold text-gray-700"
            >
              FreQ counts
            </label>
            <select
              id="pg-setting-freq_weighting"
              value={settings.freq_weighting}
              onChange={(e) =>
                onSettingsChange({
                  ...settings,
                  freq_weighting: e.target.value as FreqWeighting,
                })
              }
              aria-describedby="pg-setting-freq_weighting-help"
              className={inputClass}
            >
              <option value="tokens">Count every token</option>
              <option value="speakers">Count every speaker equally</option>
            </select>
            <p
              id="pg-setting-freq_weighting-help"
              className="text-xs text-gray-600"
            >
              How variant shares are worked out for FreQ and Ped-C. Counting
              speakers equally stops a few talkative speakers from deciding
              the result. Default: count every token.
            </p>
          </div>
          <div className="space-y-1">
            <label
              htmlFor="pg-setting-freq_mode"
              className="block text-sm font-semibold text-gray-700"
            >
              What FreQ rewards
            </label>
            <select
              id="pg-setting-freq_mode"
              value={settings.freq_mode}
              onChange={(e) =>
                onSettingsChange({
                  ...settings,
                  freq_mode: e.target.value as FreqMode,
                })
              }
              aria-describedby="pg-setting-freq_mode-help"
              className={inputClass}
            >
              <option value="threshold">
                Any variant above the threshold (as in Ugorji's tables)
              </option>
              <option value="most_frequent">
                Only the most frequent variant
              </option>
            </select>
            <p id="pg-setting-freq_mode-help" className="text-xs text-gray-600">
              With “only the most frequent variant”, ranking FreQ first makes
              the commonest pronunciation the preferred one. The threshold
              reading is the one that reproduces Ugorji's published “think”
              table.
            </p>
          </div>
          {OTHER_FIELDS.map(numberField)}
        </div>

        <div className="space-y-1">
          <label className="inline-flex items-center gap-2 text-sm font-semibold text-gray-700">
            <input
              type="checkbox"
              checked={settings.calibrated}
              onChange={(e) =>
                onSettingsChange({ ...settings, calibrated: e.target.checked })
              }
              aria-describedby="pg-setting-calibrated-help"
              className="h-4 w-4 accent-blue-600"
            />
            Use calibration
          </label>
          <p id="pg-setting-calibrated-help" className="text-xs text-gray-600">
            Corrects the classifier's known biases with offsets fitted on
            human-labelled tokens. Untick to see the uncorrected labels.
            Default: on.
          </p>
        </div>

        <button
          type="button"
          onClick={() => onSettingsChange(DEFAULT_SETTINGS)}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          <Icon name="reset" className="w-4 h-4" />
          Restore default settings
        </button>

        <fieldset className="space-y-3">
          <legend className="text-sm font-semibold text-gray-700">
            Expert overrides
          </legend>
          <p className="text-sm text-gray-600">
            Set how many violation marks a variant gets on a tenet. Overrides
            replace the computed marks.
          </p>

          <datalist id="pg-override-variants">
            {variants.map((variant) => (
              <option key={variant} value={variant} />
            ))}
          </datalist>

          {overrides.map((row) => (
            <div
              key={row.id}
              className="grid grid-cols-2 sm:grid-cols-[1fr_1fr_6rem_auto] items-end gap-3"
            >
              <div className="space-y-1">
                <label
                  htmlFor={`pg-override-segment-${row.id}`}
                  className="block text-xs font-semibold text-gray-700"
                >
                  Variant
                </label>
                <input
                  id={`pg-override-segment-${row.id}`}
                  type="text"
                  list="pg-override-variants"
                  value={row.segment}
                  onChange={(e) =>
                    updateOverride(row.id, { segment: e.target.value })
                  }
                  placeholder="e.g. t"
                  className={`${inputClass} font-ipa`}
                />
              </div>
              <div className="space-y-1">
                <label
                  htmlFor={`pg-override-tenet-${row.id}`}
                  className="block text-xs font-semibold text-gray-700"
                >
                  Tenet
                </label>
                <select
                  id={`pg-override-tenet-${row.id}`}
                  value={row.tenet}
                  onChange={(e) =>
                    updateOverride(row.id, { tenet: e.target.value })
                  }
                  className={inputClass}
                >
                  {tenets.map((tenet) => (
                    <option key={tenet.key} value={tenet.key}>
                      {tenet.key} ({tenet.name})
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label
                  htmlFor={`pg-override-count-${row.id}`}
                  className="block text-xs font-semibold text-gray-700"
                >
                  Marks
                </label>
                <input
                  id={`pg-override-count-${row.id}`}
                  type="number"
                  inputMode="numeric"
                  min="0"
                  step="1"
                  value={row.count}
                  onChange={(e) =>
                    updateOverride(row.id, { count: e.target.value })
                  }
                  className={inputClass}
                />
              </div>
              <button
                type="button"
                onClick={() =>
                  onOverridesChange(overrides.filter((o) => o.id !== row.id))
                }
                aria-label={`Remove override${
                  row.segment ? ` for [${row.segment}]` : ""
                }`}
                className="justify-self-start p-2 rounded text-gray-600 hover:text-red-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
              >
                <Icon name="close" />
              </button>
            </div>
          ))}

          <button
            type="button"
            onClick={addOverride}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <Icon name="plus" className="w-4 h-4" />
            Add override
          </button>
        </fieldset>
      </div>
    </details>
  );
};

export default AdvancedSettings;
