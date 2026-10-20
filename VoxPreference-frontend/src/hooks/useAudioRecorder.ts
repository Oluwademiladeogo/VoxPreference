import { useCallback, useEffect, useRef, useState } from "react";

type RecorderState = "idle" | "requesting" | "recording";

// Containers in order of preference; Safari only records audio/mp4
const MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

export const isRecordingSupported = () =>
  typeof window !== "undefined" &&
  typeof MediaRecorder !== "undefined" &&
  !!navigator.mediaDevices?.getUserMedia;

const useAudioRecorder = (onRecorded: (clip: Blob) => void) => {
  const [state, setState] = useState<RecorderState>("idle");
  const [elapsed, setElapsed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const keepRef = useRef(true);
  const mountedRef = useRef(false);
  const onRecordedRef = useRef(onRecorded);

  // Always call the latest callback, which sees the latest form state
  useEffect(() => {
    onRecordedRef.current = onRecorded;
  });

  const start = useCallback(async () => {
    setError(null);
    if (!isRecordingSupported()) {
      setError(
        "Recording is not available in this browser. It needs microphone support and a secure (https or localhost) connection."
      );
      return;
    }

    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // The permission prompt can outlive the component
      if (!mountedRef.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const mimeType = MIME_TYPES.find((type) =>
        MediaRecorder.isTypeSupported(type)
      );
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined
      );
      const chunks: Blob[] = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunks.push(event.data);
      };
      recorder.onstop = () => {
        // Release the microphone so the browser stops showing it as in use
        stream.getTracks().forEach((track) => track.stop());
        recorderRef.current = null;
        setState("idle");
        if (keepRef.current && chunks.length) {
          onRecordedRef.current(
            new Blob(chunks, {
              type: recorder.mimeType || mimeType || "audio/webm",
            })
          );
        }
      };

      keepRef.current = true;
      recorderRef.current = recorder;
      recorder.start();
      setElapsed(0);
      setState("recording");
    } catch (err) {
      setState("idle");
      setError(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Microphone access was blocked. Allow it in your browser's site settings and try again."
          : `Could not start recording: ${
              err instanceof Error ? err.message : "unknown error"
            }`
      );
    }
  }, []);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
  }, []);

  const discard = useCallback(() => {
    keepRef.current = false;
    recorderRef.current?.stop();
  }, []);

  useEffect(() => {
    if (state !== "recording") return;
    const startedAt = Date.now();
    const timer = window.setInterval(
      () => setElapsed((Date.now() - startedAt) / 1000),
      250
    );
    return () => window.clearInterval(timer);
  }, [state]);

  // Stop an unfinished recording if the component goes away
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      keepRef.current = false;
      if (recorderRef.current?.state === "recording") {
        recorderRef.current.stop();
      }
    };
  }, []);

  return { state, elapsed, error, start, stop, discard };
};

export default useAudioRecorder;
