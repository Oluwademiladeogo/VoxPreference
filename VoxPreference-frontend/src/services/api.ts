import { API_ENDPOINTS, API_CONFIG } from "../config/api";
import { PGAnalysisResult, PGUnitsResponse } from "../types/pg";

interface ApiError extends Error {
  status?: number;
  statusText?: string;
  data?: unknown;
  isTimeout?: boolean;
}

class ApiService {
  // Default timeout of 5 minutes if not specified in API_CONFIG
  private static readonly DEFAULT_TIMEOUT = 5 * 60 * 1000;

  private static async handleResponse(response: Response) {
    if (!response.ok) {
      const error: ApiError = new Error("API request failed");
      error.status = response.status;
      error.statusText = response.statusText;

      try {
        const contentType = response.headers.get("content-type");
        if (contentType?.includes("application/json")) {
          const errorData = await response.json();
          error.data = errorData;
          error.message =
            errorData.message || errorData.error || "API request failed";
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

  private static async fetchWithTimeout(
    url: string,
    options: RequestInit,
    requestTimeout: number = API_CONFIG.TIMEOUT
  ) {
    const controller = new AbortController();
    let timeoutId: number | undefined;

    // Use default timeout if the requested timeout is not set or is unreasonable
    const timeout =
      typeof requestTimeout === "number" &&
      requestTimeout > 0 &&
      requestTimeout < 3600000
        ? requestTimeout
        : this.DEFAULT_TIMEOUT;

    // Let a caller's signal (e.g. a cancel button) abort the request as well
    const callerSignal = options.signal;
    const abortFromCaller = () => controller.abort();
    if (callerSignal?.aborted) {
      controller.abort();
    } else {
      callerSignal?.addEventListener("abort", abortFromCaller);
    }

    // Create a promise that rejects after the timeout
    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutId = window.setTimeout(() => {
        const timeoutError: ApiError = new Error(
          `Request timed out after ${timeout}ms`
        );
        timeoutError.isTimeout = true;
        reject(timeoutError);
        controller.abort();
      }, timeout);
    });

    try {
      console.log(`Starting request to ${url} with timeout ${timeout}ms`);

      // Race between the fetch and the timeout
      const response = await Promise.race([
        fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            ...options.headers,
            Accept: "application/json",
          },
        }),
        timeoutPromise,
      ]);

      console.log(`Received response from ${url}`);
      return this.handleResponse(response);
    } catch (error) {
      console.error("Request failed:", {
        url,
        timeout,
        error:
          error instanceof Error
            ? {
                name: error.name,
                message: error.message,
                isTimeout: (error as ApiError).isTimeout,
                isAbortError:
                  error instanceof DOMException && error.name === "AbortError",
              }
            : "Unknown error",
      });

      if (error instanceof DOMException && error.name === "AbortError") {
        if ((error as ApiError).isTimeout) {
          throw new Error(`Request timed out after ${timeout}ms`);
        }
        throw new Error("Request was aborted");
      }

      if (error instanceof Error) {
        throw error;
      }

      throw new Error("An unknown error occurred during the request");
    } finally {
      if (timeoutId !== undefined) {
        window.clearTimeout(timeoutId);
      }
      callerSignal?.removeEventListener("abort", abortFromCaller);
    }
  }

  static async uploadAudio(formData: FormData) {
    const formDataFiles = formData.getAll("audioFile");

    if (!formDataFiles.length) {
      throw new Error("No audio files provided in FormData");
    }

    // Validate that all items are actually files and cast them
    const files = formDataFiles.filter(
      (file): file is File => file instanceof File
    );
    if (files.length !== formDataFiles.length) {
      throw new Error("Invalid file data provided - all entries must be files");
    }

    console.log("Starting audio upload...", {
      fileCount: files.length,
      fileNames: files.map((f: File) => f.name),
      totalSize: files.reduce((acc: number, f: File) => acc + f.size, 0),
      timeout:
        typeof API_CONFIG.TIMEOUT === "number"
          ? API_CONFIG.TIMEOUT
          : this.DEFAULT_TIMEOUT,
    });

    try {
      const response = await this.fetchWithTimeout(API_ENDPOINTS.UPLOAD_AUDIO, {
        method: "POST",
        body: formData,
        // Intentionally omitting Content-Type to let browser set it with boundary
      });
      console.log("Audio upload completed successfully");
      return response;
    } catch (error) {
      console.error("Audio upload failed:", error);
      throw error;
    }
  }

  static async getPGUnits(): Promise<PGUnitsResponse> {
    return this.fetchWithTimeout(API_ENDPOINTS.PG_UNITS, { method: "GET" });
  }

  static async analyzePG(
    formData: FormData,
    signal?: AbortSignal
  ): Promise<PGAnalysisResult> {
    const files = formData.getAll("files");

    if (!files.length) {
      throw new Error("No audio files provided in FormData");
    }
    if (!files.every((file) => file instanceof File)) {
      throw new Error("Invalid file data provided - all entries must be files");
    }

    console.log("Starting PG analysis...", {
      fileCount: files.length,
      words: formData.get("words"),
      unit: formData.get("unit"),
      ranking: formData.get("ranking"),
      timeout: API_CONFIG.PG_ANALYZE_TIMEOUT,
    });

    try {
      const response = await this.fetchWithTimeout(
        API_ENDPOINTS.PG_ANALYZE,
        {
          method: "POST",
          body: formData,
          signal,
          // Intentionally omitting Content-Type to let browser set it with boundary
        },
        API_CONFIG.PG_ANALYZE_TIMEOUT
      );
      if (!response.success) {
        throw new Error(response.error || "PG analysis failed");
      }
      console.log("PG analysis completed successfully");
      return response;
    } catch (error) {
      console.error("PG analysis failed:", error);
      throw error;
    }
  }
}

export default ApiService;
