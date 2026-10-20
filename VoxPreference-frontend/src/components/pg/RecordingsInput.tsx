import {
  ChangeEvent,
  Dispatch,
  DragEvent,
  SetStateAction,
  useRef,
  useState,
} from "react";
import { API_CONFIG } from "../../config/api";
import useAudioRecorder from "../../hooks/useAudioRecorder";
import useClipPlayer from "../../hooks/useClipPlayer";
import { RecordingItem } from "../../types/pg";
import {
  extensionForMimeType,
  fileNameHasWord,
  fileSlug,
  formatDuration,
  formatFileSize,
  isAudioFile,
  isAutoTranscript,
  nextId,
  transcriptHasWord,
  uniqueFileName,
} from "../../utils/pg";
import Icon from "./Icon";

interface RecordingsInputProps {
  items: RecordingItem[];
  onChange: Dispatch<SetStateAction<RecordingItem[]>>;
  words: string[];
  asr: boolean; // files without a transcript are unscripted audio, searched by speech recognition
  onAsrChange: (asr: boolean) => void;
  diarize: boolean; // separate the speakers inside unscripted files that have no speaker id
  onDiarizeChange: (diarize: boolean) => void;
  numSpeakers: string; // how many people talk in each such file; empty = estimate
  onNumSpeakersChange: (value: string) => void;
}

// One compact row per recording: datasets often hold dozens of clips
const ROW_COLUMNS =
  "grid grid-cols-[2rem_minmax(0,1fr)_2rem] md:grid-cols-[2rem_minmax(0,1fr)_minmax(0,1.7fr)_2rem] items-center gap-x-3 gap-y-2";
const FIELD_COLUMNS = "grid gap-2 sm:grid-cols-[9rem_minmax(0,1fr)]";
const fieldClass =
  "w-full px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent";

const RecordingsInput = ({
  items,
  onChange,
  words,
  asr,
  onAsrChange,
  diarize,
  onDiarizeChange,
  numSpeakers,
  onNumSpeakersChange,
}: RecordingsInputProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clipWord, setClipWord] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const player = useClipPlayer();

  // The word a new clip is named after, so the server can tell which word it is
  const recordWord = words.includes(clipWord) ? clipWord : words[0] ?? "";

  const addFiles = (files: File[], origin: RecordingItem["origin"]) => {
    const accepted: File[] = [];
    const problems: string[] = [];
    for (const file of files) {
      if (!isAudioFile(file)) {
        problems.push(`${file.name} is not an audio file`);
      } else if (file.size > API_CONFIG.MAX_FILE_SIZE) {
        problems.push(
          `${file.name} is larger than ${
            API_CONFIG.MAX_FILE_SIZE / (1024 * 1024)
          }MB`
        );
      } else {
        accepted.push(file);
      }
    }
    setError(problems.length ? `${problems.join(". ")}.` : null);

    const entries = accepted.map((file) => ({ id: nextId("audio"), file }));
    onChange((prev) => {
      const taken = new Set(prev.map((item) => item.file.name));
      const added = entries.map(({ id, file }) => {
        const name = uniqueFileName(file.name, taken);
        taken.add(name);
        return {
          id,
          origin,
          speaker: "",
          transcript: "",
          file:
            name === file.name
              ? file
              : new File([file], name, {
                  type: file.type,
                  lastModified: file.lastModified,
                }),
        };
      });
      return [...prev, ...added];
    });
  };

  const recorder = useAudioRecorder((clip) => {
    const name = `${fileSlug(recordWord || "clip")}-1.${extensionForMimeType(
      clip.type
    )}`;
    addFiles([new File([clip], name, { type: clip.type })], "recording");
  });

  const updateItem = (id: string, changes: Partial<RecordingItem>) => {
    onChange((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...changes } : item))
    );
  };

  const removeItem = (id: string) => {
    if (player.playing === id) player.stop();
    onChange((prev) => prev.filter((item) => item.id !== id));
  };

  const removeAll = () => {
    player.stop();
    onChange([]);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files), "upload");
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files), "upload");
    }
    // Allow the same file to be picked again after removing it
    e.target.value = "";
  };

  const buttonClass =
    "inline-flex items-center gap-2 px-4 py-2 rounded-lg font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-blue-600 disabled:opacity-50 disabled:cursor-not-allowed";
  const totalSize = items.reduce((sum, item) => sum + item.file.size, 0);

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors duration-300 ${
          isDragging ? "border-blue-600 bg-blue-50" : "border-gray-300 bg-gray-50"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <p className="font-semibold text-gray-800">
          Drag & drop recordings here
        </p>
        <p className="text-sm text-gray-600 mt-1 mb-4">
          Any common audio format (WAV, MP3, FLAC, OGG, WebM, M4A), up to{" "}
          {API_CONFIG.MAX_FILE_SIZE / (1024 * 1024)}MB each.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className={`${buttonClass} bg-white border border-gray-300 text-gray-800 hover:bg-gray-100`}
          >
            <Icon name="upload" />
            Choose files
          </button>

          {recorder.state === "recording" ? (
            <>
              <button
                type="button"
                onClick={recorder.stop}
                className={`${buttonClass} bg-red-600 text-white hover:bg-red-700`}
              >
                <Icon name="stop" />
                Stop and add
              </button>
              <button
                type="button"
                onClick={recorder.discard}
                className={`${buttonClass} bg-white border border-gray-300 text-gray-800 hover:bg-gray-100`}
              >
                Discard
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={recorder.start}
              disabled={recorder.state === "requesting"}
              className={`${buttonClass} bg-blue-600 text-white hover:bg-blue-700`}
            >
              <Icon name="microphone" />
              {recorder.state === "requesting"
                ? "Waiting for microphone..."
                : "Record a clip"}
            </button>
          )}
        </div>

        {words.length > 1 && (
          <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-sm">
            <label htmlFor="pg-clip-word" className="text-gray-700">
              Word in the next clip
            </label>
            <select
              id="pg-clip-word"
              value={recordWord}
              onChange={(e) => setClipWord(e.target.value)}
              disabled={recorder.state === "recording"}
              className="px-2 py-1 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              {words.map((word) => (
                <option key={word} value={word}>
                  {word}
                </option>
              ))}
            </select>
          </div>
        )}

        {recorder.state === "recording" && (
          <p
            role="status"
            className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-red-700"
          >
            <span
              aria-hidden="true"
              className="w-2.5 h-2.5 rounded-full bg-red-600 motion-safe:animate-pulse"
            />
            Recording {recordWord ? `"${recordWord}"` : "a clip"}
            <span className="font-mono tabular-nums" aria-hidden="true">
              {formatDuration(recorder.elapsed)}
            </span>
          </p>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*,.webm,.m4a,.opus"
          multiple
          onChange={handleFileChange}
          className="hidden"
          tabIndex={-1}
          aria-label="Audio files"
        />
      </div>

      {(error || recorder.error) && (
        <p
          role="alert"
          className="p-3 rounded-lg bg-red-50 border border-red-200 text-sm text-red-700"
        >
          {error ?? recorder.error}
        </p>
      )}

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
        <label className="flex items-start gap-2 text-sm font-semibold text-gray-800">
          <input
            type="checkbox"
            checked={asr}
            onChange={(e) => onAsrChange(e.target.checked)}
            aria-describedby="pg-asr-help"
            className="mt-0.5 h-4 w-4 shrink-0 accent-blue-600"
          />
          Unscripted audio (podcast/interview): find the words automatically
        </label>
        <p id="pg-asr-help" className="mt-1 ml-6 text-sm text-gray-600">
          Files without a transcript are transcribed by speech recognition to
          find the target words. This is slower. To do this for a single file,
          type “auto” as its transcript.
        </p>
        <label className="mt-3 ml-6 flex items-start gap-2 text-sm font-semibold text-gray-800">
          <input
            type="checkbox"
            checked={diarize}
            onChange={(e) => onDiarizeChange(e.target.checked)}
            aria-describedby="pg-diarize-help"
            className="mt-0.5 h-4 w-4 shrink-0 accent-blue-600"
          />
          Separate the speakers in each file
        </label>
        <p id="pg-diarize-help" className="mt-1 ml-12 text-sm text-gray-600">
          A podcast has several voices. Each target word is credited to the
          person who said it, so every speaker counts and the stability check
          works. Applies to unscripted files with no speaker id; a file given a
          speaker id counts as that one person.
        </p>
        {diarize && (
          <label className="mt-2 ml-12 flex flex-wrap items-center gap-2 text-sm text-gray-700">
            Number of speakers per file (if known)
            <input
              type="number"
              min={1}
              max={20}
              inputMode="numeric"
              value={numSpeakers}
              onChange={(e) => onNumSpeakersChange(e.target.value)}
              placeholder="estimate"
              className="w-24 px-2 py-1 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent"
            />
          </label>
        )}
      </div>

      {words.length > 1 && !asr && (
        <p className="text-sm text-gray-600">
          With several target words, name each single-word file after its word
          (e.g. <span className="font-mono">three-s01.wav</span>) or give it a
          transcript, so the server knows which word it is.
        </p>
      )}

      {items.length > 0 && (
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-gray-700">
              {items.length} recording{items.length === 1 ? "" : "s"} ·{" "}
              {formatFileSize(totalSize)}
            </p>
            <button
              type="button"
              onClick={removeAll}
              className="text-sm text-gray-700 underline hover:text-red-700 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
            >
              Remove all
            </button>
          </div>

          <div
            aria-hidden="true"
            className={`hidden md:grid ${ROW_COLUMNS} px-3 text-xs font-semibold text-gray-600`}
          >
            <span />
            <span>Recording</span>
            <span className={FIELD_COLUMNS}>
              <span>Speaker</span>
              <span>Transcript (sentences, or “auto”)</span>
            </span>
            <span />
          </div>

          <ul className="space-y-2" aria-label="Recordings to analyse">
            {items.map((item) => {
              const transcript = item.transcript.trim();
              // Mirror how the server reads each file, to flag the ones it would skip
              const unmatched =
                !asr &&
                words.length > 1 &&
                !transcript &&
                !fileNameHasWord(item.file.name, words);
              const wordMissing =
                words.length > 0 &&
                !!transcript &&
                !isAutoTranscript(transcript) &&
                !transcriptHasWord(transcript, words);
              const isPlaying = player.playing === item.id;

              return (
                <li
                  key={item.id}
                  className="rounded-lg border border-gray-200 bg-white p-3"
                >
                  <div className={ROW_COLUMNS}>
                    <button
                      type="button"
                      onClick={() =>
                        isPlaying ? player.stop() : player.play(item.id, item.file)
                      }
                      aria-label={`${isPlaying ? "Stop" : "Play"} ${item.file.name}`}
                      className="col-start-1 row-start-1 p-1 rounded text-blue-700 hover:bg-blue-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600"
                    >
                      <Icon name={isPlaying ? "stop" : "play"} className="w-6 h-6" />
                    </button>

                    <div className="col-start-2 row-start-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 break-all">
                        {item.file.name}
                      </p>
                      <p className="text-xs text-gray-600">
                        {item.origin === "recording" ? "Recorded here" : "Uploaded"}{" "}
                        · {formatFileSize(item.file.size)}
                      </p>
                    </div>

                    <div
                      className={`col-span-3 row-start-2 md:col-span-1 md:col-start-3 md:row-start-1 ${FIELD_COLUMNS}`}
                    >
                      <div>
                        <label
                          htmlFor={`pg-speaker-${item.id}`}
                          className="block text-xs font-semibold text-gray-700 mb-1 md:sr-only"
                        >
                          Speaker{" "}
                          <span className="font-normal text-gray-600">
                            (optional)
                          </span>
                          <span className="sr-only"> for {item.file.name}</span>
                        </label>
                        <input
                          id={`pg-speaker-${item.id}`}
                          type="text"
                          value={item.speaker}
                          onChange={(e) =>
                            updateItem(item.id, { speaker: e.target.value })
                          }
                          placeholder="e.g. S01"
                          className={fieldClass}
                        />
                      </div>
                      <div>
                        <label
                          htmlFor={`pg-transcript-${item.id}`}
                          className="block text-xs font-semibold text-gray-700 mb-1 md:sr-only"
                        >
                          Transcript{" "}
                          <span className="font-normal text-gray-600">
                            (sentences, or “auto”)
                          </span>
                          <span className="sr-only"> for {item.file.name}</span>
                        </label>
                        <input
                          id={`pg-transcript-${item.id}`}
                          type="text"
                          value={item.transcript}
                          onChange={(e) =>
                            updateItem(item.id, { transcript: e.target.value })
                          }
                          placeholder={
                            asr ? "found automatically" : "e.g. I think it will rain"
                          }
                          aria-describedby={
                            unmatched || wordMissing
                              ? `pg-recording-hint-${item.id}`
                              : undefined
                          }
                          className={fieldClass}
                        />
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => removeItem(item.id)}
                      aria-label={`Remove ${item.file.name}`}
                      className="col-start-3 row-start-1 md:col-start-4 p-1 rounded text-gray-600 hover:text-red-700 hover:bg-red-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
                    >
                      <Icon name="close" />
                    </button>
                  </div>

                  {(unmatched || wordMissing) && (
                    <p
                      id={`pg-recording-hint-${item.id}`}
                      className="mt-2 flex items-start gap-2 text-sm text-amber-800"
                    >
                      <Icon name="warning" className="w-4 h-4 mt-0.5 shrink-0" />
                      {unmatched
                        ? "No target word in the file name: add a transcript, or the server will skip this file."
                        : "The transcript does not contain a target word, so the server will skip this file."}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

export default RecordingsInput;
