const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:3000";

export const API_ENDPOINTS = {
  UPLOAD_AUDIO: `${API_BASE_URL}/transcribe`,
};

export const API_CONFIG = {
  MAX_FILE_SIZE: 50 * 1024 * 1024, // 50MB
  SUPPORTED_FILE_TYPES: [
    "audio/wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/flac",
  ],
  TIMEOUT: 5 * 60 * 1000, // 5 minutes in milliseconds
};
