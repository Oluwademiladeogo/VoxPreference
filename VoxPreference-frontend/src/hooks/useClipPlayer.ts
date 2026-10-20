import { useCallback, useEffect, useRef, useState } from "react";

// Plays one local clip at a time, optionally only the stretch from start to end (seconds)
const useClipPlayer = () => {
  const [playing, setPlaying] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);

  const stop = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = null;
    setPlaying(null);
  }, []);

  // Release the audio when the component goes away
  useEffect(() => stop, [stop]);

  const play = useCallback(
    (id: string, file: File, start = 0, end = Infinity) => {
      stop();
      const url = URL.createObjectURL(file);
      const audio = new Audio(url);
      urlRef.current = url;
      audioRef.current = audio;

      const finish = () => {
        if (audioRef.current === audio) stop();
      };
      if (start > 0) {
        // Before metadata loads this sets the start position; re-apply it once it has
        audio.currentTime = start;
        audio.addEventListener(
          "loadedmetadata",
          () => {
            if (Math.abs(audio.currentTime - start) > 0.05) {
              audio.currentTime = start;
            }
          },
          { once: true }
        );
      }
      if (Number.isFinite(end)) {
        audio.addEventListener("timeupdate", () => {
          if (audio.currentTime >= end) finish();
        });
      }
      audio.addEventListener("ended", finish);
      audio.addEventListener("error", finish);
      audio.play().catch(finish);
      setPlaying(id);
    },
    [stop]
  );

  return { playing, play, stop };
};

export default useClipPlayer;
