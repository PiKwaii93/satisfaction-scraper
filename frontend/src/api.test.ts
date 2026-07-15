import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearAuthToken,
  hasAuthToken,
  listRuns,
  setAuthToken
} from "./api";
import { server } from "./test/server";

describe("API authentication", () => {
  beforeEach(() => {
    clearAuthToken();
    vi.restoreAllMocks();
  });

  it("clears the local session when the API returns 401", async () => {
    server.use(
      http.get("http://localhost:8000/analysis-runs", () =>
        HttpResponse.json({ detail: "Session expiree" }, { status: 401 })
      )
    );
    setAuthToken("expired-token");

    await expect(listRuns()).rejects.toThrow("Session expiree");

    expect(hasAuthToken()).toBe(false);
    expect(
      window.localStorage.getItem("satisfaction_client_access_token")
    ).toBeNull();
  });

  it("explains backend connectivity failures", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
      new TypeError("Failed to fetch")
    );

    await expect(listRuns()).rejects.toThrow(
      "API indisponible. Verifie que le service backend est lance sur http://localhost:8000."
    );
  });

  it("formats FastAPI validation errors", async () => {
    server.use(
      http.get("http://localhost:8000/analysis-runs", () =>
        HttpResponse.json(
          { detail: [{ msg: "Field required" }, { msg: "Input should be valid" }] },
          { status: 422 }
        )
      )
    );

    await expect(listRuns()).rejects.toThrow(
      "Field required, Input should be valid"
    );
  });
});
