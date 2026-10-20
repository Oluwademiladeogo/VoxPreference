const DEFAULT_TIMEOUT_MS = 25000;

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchJson(path, options = {}) {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      ...options,
      signal: controller.signal,
    });
    const text = await response.text();
    let data = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error("The server returned an unreadable response. Please try again.");
      }
    }

    if (!response.ok) {
      throw new Error(
        data?.detail ||
          data?.errors?.join(" ") ||
          data?.error ||
          `Request failed with status ${response.status}.`
      );
    }

    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("The request timed out. Check your connection and try again.");
    }
    if (error instanceof TypeError) {
      throw new Error("Could not reach the server. Check your connection and try again.");
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}
