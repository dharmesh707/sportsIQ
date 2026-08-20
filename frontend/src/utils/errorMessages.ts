import { ApiError } from "@/api/types";

/**
 * Maps every failure the backend/client can surface into copy a person can
 * act on. Extracted from AnalyzeScreen so it can be unit tested without
 * pulling in React Native rendering - this function has no UI dependency.
 *
 * This is the ONE place that turns an ApiError into a message; screens
 * should not invent their own ad-hoc error strings.
 */
export function messageFor(error: ApiError): string {
  switch (error.code) {
    case "TIMEOUT":
      return "The analysis is taking longer than expected. Please try again.";
    case "NETWORK_ERROR":
      return "Unable to connect to the analysis server. Check your connection and try again.";
    case "MALFORMED_RESPONSE":
      return "The server sent back something we didn't expect. Please try again.";
    case "VALIDATION_ERROR":
      return error.message || "Please select a valid sports video.";
    case "VIDEO_PROCESSING_FAILED":
      return (
        error.message ||
        "We couldn't detect the athlete clearly enough. Try recording with the full body visible and better lighting."
      );
    case "INTERNAL_ERROR":
      return "The analysis service encountered a problem. Please try again.";
    case "UNAUTHORIZED":
      return "Your session expired. Please sign in again.";
    default:
      return error.message || "Something went wrong. Please try again.";
  }
}
