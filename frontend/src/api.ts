import type {
  AnalysisRunEvent,
  AnalysisRun,
  ReviewListResponse,
  RunSummary,
  SentimentLabel
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

type CreateRunPayload = {
  company: string;
  source: "trustpilot";
  stars: number[];
  pages_per_star: number;
  execute_immediately: boolean;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Erreur API ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function listRuns() {
  return request<AnalysisRun[]>("/analysis-runs");
}

export function createRun(payload: CreateRunPayload) {
  return request<AnalysisRun>("/analysis-runs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getSummary(runId: number) {
  return request<RunSummary>(`/analysis-runs/${runId}/summary`);
}

export function getRunEvents(runId: number, limit = 100) {
  const params = new URLSearchParams({ limit: String(limit) });
  return request<AnalysisRunEvent[]>(
    `/analysis-runs/${runId}/events?${params.toString()}`
  );
}

export function getReviews(
  runId: number,
  sentiment: SentimentLabel | "Tous" = "Tous",
  limit = 30
) {
  const params = new URLSearchParams({ limit: String(limit) });
  if (sentiment !== "Tous") {
    params.set("sentiment", sentiment);
  }

  return request<ReviewListResponse>(
    `/analysis-runs/${runId}/reviews?${params.toString()}`
  );
}

export function exportUrl(runId: number) {
  return `${API_BASE_URL}/analysis-runs/${runId}/export`;
}
