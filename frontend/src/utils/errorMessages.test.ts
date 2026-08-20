import { ApiError } from "@/api/types";
import { messageFor } from "@/utils/errorMessages";

describe("messageFor", () => {
  it("gives an actionable message for a timeout", () => {
    const msg = messageFor(new ApiError(0, "TIMEOUT", ""));
    expect(msg.toLowerCase()).toContain("longer than expected");
  });

  it("gives a connectivity message for a network error, distinct from timeout", () => {
    const network = messageFor(new ApiError(0, "NETWORK_ERROR", ""));
    const timeout = messageFor(new ApiError(0, "TIMEOUT", ""));
    expect(network).not.toEqual(timeout);
    expect(network.toLowerCase()).toContain("connect");
  });

  it("prefers the server's message for VALIDATION_ERROR when present", () => {
    const msg = messageFor(new ApiError(400, "VALIDATION_ERROR", "Video exceeds the 100MB limit."));
    expect(msg).toBe("Video exceeds the 100MB limit.");
  });

  it("falls back to generic copy for VALIDATION_ERROR with no server message", () => {
    const msg = messageFor(new ApiError(400, "VALIDATION_ERROR", ""));
    expect(msg).toBe("Please select a valid sports video.");
  });

  it("gives the full-body/lighting guidance for VIDEO_PROCESSING_FAILED with no message", () => {
    const msg = messageFor(new ApiError(422, "VIDEO_PROCESSING_FAILED", ""));
    expect(msg.toLowerCase()).toContain("full body");
  });

  it("prefers the server's specific message for VIDEO_PROCESSING_FAILED when present", () => {
    const msg = messageFor(
      new ApiError(422, "VIDEO_PROCESSING_FAILED", "This clip is too short to analyze.")
    );
    expect(msg).toBe("This clip is too short to analyze.");
  });

  it("never surfaces a raw INTERNAL_ERROR server message to the user", () => {
    // Internal errors intentionally always get the generic retry copy,
    // regardless of what the server put in .message - that field could
    // contain implementation detail that shouldn't reach the UI.
    const msg = messageFor(
      new ApiError(500, "INTERNAL_ERROR", "Traceback: mediapipe.python...")
    );
    expect(msg).not.toContain("Traceback");
    expect(msg).not.toContain("mediapipe");
  });

  it("tells the user to sign in again on UNAUTHORIZED", () => {
    expect(messageFor(new ApiError(401, "UNAUTHORIZED", ""))).toContain("sign in");
  });

  it("flags a malformed response distinctly from a network failure", () => {
    const malformed = messageFor(new ApiError(200, "MALFORMED_RESPONSE", ""));
    const network = messageFor(new ApiError(0, "NETWORK_ERROR", ""));
    expect(malformed).not.toEqual(network);
  });

  it("falls back to the server message for an unrecognized code", () => {
    const msg = messageFor(new ApiError(418, "SOME_FUTURE_CODE" as any, "A teapot happened."));
    expect(msg).toBe("A teapot happened.");
  });

  it("falls back to generic copy for an unrecognized code with no message", () => {
    const msg = messageFor(new ApiError(418, "SOME_FUTURE_CODE" as any, ""));
    expect(msg).toBe("Something went wrong. Please try again.");
  });
});
