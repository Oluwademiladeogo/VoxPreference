import { API_ENDPOINTS, API_CONFIG } from "../config/api";

interface ApiError extends Error {
  status?: number;
  statusText?: string;
}

class ApiService {
  private static async handleResponse(response: Response) {
    if (!response.ok) {
      const error: ApiError = new Error("API request failed");
      error.status = response.status;
      error.statusText = response.statusText;

      try {
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
          const errorData = await response.json();
          error.message = errorData.message || "API request failed";
        } else {
          const text = await response.text();
          if (text.includes("<!DOCTYPE")) {
            error.message =
              "Server error: Please check if the server is running and properly configured";
          } else {
            error.message = `Server error: ${response.status} ${response.statusText}`;
          }
        }
      } catch (parseError) {
        console.error("Error parsing response:", parseError);
        error.message = `Server error: ${response.status} ${response.statusText}`;
      }

      throw error;
    }

    return response.json();
  }

  private static async fetchWithTimeout(url: string, options: RequestInit) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          ...options.headers,
          Accept: "application/json",
        },
      });

      return this.handleResponse(response);
    } catch (error) {
      if (error instanceof Error) {
        if (error.name === "AbortError") {
          throw new Error("Request timed out");
        }
        if (
          error.name === "TypeError" &&
          error.message.includes("Failed to fetch")
        ) {
          throw new Error(
            "Network error: Please check your internet connection"
          );
        }
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  static async uploadAudio(formData: FormData) {
    return this.fetchWithTimeout(API_ENDPOINTS.UPLOAD_AUDIO, {
      method: "POST",
      body: formData,
      headers: {
        // Don't set Content-Type for FormData, let the browser set it with the boundary
      },
    });
  }
}

export default ApiService;
