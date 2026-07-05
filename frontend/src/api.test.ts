import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it } from "vitest";
import {
  clearAuthToken,
  hasAuthToken,
  listRuns,
  setAuthToken
} from "./api";
import { server } from "./test/server";

describe("API authentication", () => {
  beforeEach(() => clearAuthToken());

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
});
