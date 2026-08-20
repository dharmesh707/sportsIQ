/**
 * Tests the fault-handling behaviour of the raw request() function via the
 * public api.* surface, with global fetch mocked. No React Native rendering
 * involved - this is pure client logic.
 */
import { api, configureApiClient } from "@/api/client";
import { ApiError } from "@/api/types";

function mockFetchOnce(impl: () => Promise<Response> | never) {
  (global as any).fetch = jest.fn(impl);
}

function jsonResponse(status: number, body: unknown): Response {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  } as unknown as Response;
}

beforeEach(() => {
  configureApiClient({ getToken: () => null, onUnauthorized: jest.fn() });
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe("api client fault handling", () => {
  it("surfaces the contract error shape as an ApiError", async () => {
    mockFetchOnce(async () =>
      jsonResponse(422, { error: { code: "VIDEO_PROCESSING_FAILED", message: "Too dark." } })
    );
    await expect(api.dashboard()).rejects.toMatchObject({
      status: 422,
      code: "VIDEO_PROCESSING_FAILED",
      message: "Too dark.",
    });
  });

  it("falls back safely when a non-2xx response doesn't match the contract shape", async () => {
    mockFetchOnce(async () => jsonResponse(500, { unexpected: "shape" }));
    await expect(api.dashboard()).rejects.toMatchObject({
      status: 500,
      code: "INTERNAL_ERROR",
    });
  });

  it("converts a fetch rejection into NETWORK_ERROR, not an unhandled rejection", async () => {
    mockFetchOnce(async () => {
      throw new TypeError("Failed to fetch");
    });
    await expect(api.dashboard()).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });

  it("converts an AbortError (timeout) into a distinct TIMEOUT code", async () => {
    mockFetchOnce(async () => {
      const err = new Error("aborted");
      err.name = "AbortError";
      throw err;
    });
    await expect(api.dashboard()).rejects.toMatchObject({ code: "TIMEOUT" });
  });

  it("converts a response body that isn't valid JSON into MALFORMED_RESPONSE", async () => {
    mockFetchOnce(async () => ({
      status: 200,
      ok: true,
      json: async () => {
        throw new SyntaxError("Unexpected token");
      },
    } as unknown as Response));
    await expect(api.dashboard()).rejects.toMatchObject({ code: "MALFORMED_RESPONSE" });
  });

  it("calls onUnauthorized exactly once on a 401 and still throws", async () => {
    const onUnauthorized = jest.fn();
    configureApiClient({ getToken: () => "expired-token", onUnauthorized });
    mockFetchOnce(async () =>
      jsonResponse(401, { error: { code: "UNAUTHORIZED", message: "Session expired." } })
    );
    await expect(api.dashboard()).rejects.toMatchObject({ code: "UNAUTHORIZED" });
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("does not call onUnauthorized on a non-401 error", async () => {
    const onUnauthorized = jest.fn();
    configureApiClient({ getToken: () => "token", onUnauthorized });
    mockFetchOnce(async () =>
      jsonResponse(422, { error: { code: "VIDEO_PROCESSING_FAILED", message: "x" } })
    );
    await expect(api.dashboard()).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).not.toHaveBeenCalled();
  });

  it("resolves normally on a 200 with a valid contract body", async () => {
    mockFetchOnce(async () =>
      jsonResponse(200, { streakDays: 3, sessionsThisWeek: 2, recentAnalyses: [] })
    );
    await expect(api.dashboard()).resolves.toMatchObject({ streakDays: 3 });
  });

  it("sends the Authorization header when a token is configured", async () => {
    configureApiClient({ getToken: () => "abc123", onUnauthorized: jest.fn() });
    let capturedHeaders: Record<string, string> = {};
    mockFetchOnce(async (...args: any[]) => {
      capturedHeaders = args[1]?.headers ?? {};
      return jsonResponse(200, { streakDays: 0, sessionsThisWeek: 0, recentAnalyses: [] });
    });
    await api.dashboard();
    expect(capturedHeaders["Authorization"]).toBe("Bearer abc123");
  });

  it("does not attach a token for skipAuth requests like login", async () => {
    configureApiClient({ getToken: () => "abc123", onUnauthorized: jest.fn() });
    let capturedHeaders: Record<string, string> = {};
    mockFetchOnce(async (...args: any[]) => {
      capturedHeaders = args[1]?.headers ?? {};
      return jsonResponse(200, {
        accessToken: "t",
        tokenType: "bearer",
        user: { id: "1", email: "a@b.com", createdAt: "2024-01-01" },
      });
    });
    await api.login("a@b.com", "pw");
    expect(capturedHeaders["Authorization"]).toBeUndefined();
  });
});
