// in a production build the backend serves this app, so the API is on the same address
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? "" : "http://localhost:3000");

export const API_ENDPOINTS = {
  UPLOAD_AUDIO: `${API_BASE_URL}/transcribe`,
  PG_UNITS: `${API_BASE_URL}/pg/units`,
  PG_ANALYZE: `${API_BASE_URL}/pg/analyze`,
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
  PG_ANALYZE_TIMEOUT: 30 * 60 * 1000, // 30 minutes: the phone model runs over every recording on CPU
};
