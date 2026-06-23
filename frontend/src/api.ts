import type {
  AnalysisRunEvent,
  AnalysisRun,
  CsvImportPreview,
  FeedbackQuality,
  ModelTrainingOverview,
  ModelTrainingRun,
  ReviewFeedback,
  ReviewListResponse,
  RunsComparison,
  RunSummary,
  SentimentLabel
} from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";
const API_KEY = import.meta.env.VITE_API_KEY ?? "dev-satisfaction-key";

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
      "X-API-Key": API_KEY,
      ...init?.headers
    },
    ...init
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiError(detail, response.status));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function parseApiError(detail: string, status: number) {
  try {
    const payload = JSON.parse(detail) as { detail?: string };
    if (payload.detail) {
      return payload.detail;
    }
  } catch {
    // The response body is not JSON, keep the raw server message.
  }

  return detail || `Erreur API ${status}`;
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

export async function uploadCsvRun(company: string, file: File) {
  const formData = new FormData();
  formData.append("company", company);
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/analysis-runs/import-csv`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY
    },
    body: formData
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiError(detail, response.status));
  }

  return response.json() as Promise<AnalysisRun>;
}

export async function previewCsvFile(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/analysis-runs/preview-csv`, {
    method: "POST",
    headers: {
      "X-API-Key": API_KEY
    },
    body: formData
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiError(detail, response.status));
  }

  return response.json() as Promise<CsvImportPreview>;
}

export function executeRun(runId: number, skipScrape = false) {
  const params = new URLSearchParams({ skip_scrape: String(skipScrape) });
  return request<AnalysisRun>(
    `/analysis-runs/${runId}/execute?${params.toString()}`,
    {
      method: "POST"
    }
  );
}

export function getSummary(runId: number) {
  return request<RunSummary>(`/analysis-runs/${runId}/summary`);
}

export function compareRuns(runIds: number[]) {
  const params = new URLSearchParams({ run_ids: runIds.join(",") });
  return request<RunsComparison>(
    `/analysis-runs/compare?${params.toString()}`
  );
}

export function getFeedbackQuality(recentLimit = 8) {
  const params = new URLSearchParams({ recent_limit: String(recentLimit) });
  return request<FeedbackQuality>(
    `/analysis-runs/feedback/quality?${params.toString()}`
  );
}

export function getModelTrainingOverview(limit = 6) {
  const params = new URLSearchParams({ limit: String(limit) });
  return request<ModelTrainingOverview>(
    `/model-training/overview?${params.toString()}`
  );
}

export function createModelTrainingRun(feedbackSampleWeight?: number) {
  return request<ModelTrainingRun>("/model-training/runs", {
    method: "POST",
    body: JSON.stringify({
      feedback_sample_weight: feedbackSampleWeight ?? null,
      execute_immediately: true
    })
  });
}

async function requestFile(path: string): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "X-API-Key": API_KEY
    }
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(parseApiError(detail, response.status));
  }

  return response.blob();
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
  limit = 30,
  offset = 0
) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset)
  });
  if (sentiment !== "Tous") {
    params.set("sentiment", sentiment);
  }

  return request<ReviewListResponse>(
    `/analysis-runs/${runId}/reviews?${params.toString()}`
  );
}

export function exportReviews(runId: number) {
  return requestFile(`/analysis-runs/${runId}/export`);
}

export function saveReviewFeedback(
  runId: number,
  reviewId: number,
  correctedLabel: SentimentLabel,
  comment?: string
) {
  return request<ReviewFeedback>(
    `/analysis-runs/${runId}/reviews/${reviewId}/feedback`,
    {
      method: "POST",
      body: JSON.stringify({
        corrected_label: correctedLabel,
        comment: comment?.trim() || null
      })
    }
  );
}

export function deleteReviewFeedback(runId: number, reviewId: number) {
  return request<void>(
    `/analysis-runs/${runId}/reviews/${reviewId}/feedback`,
    {
      method: "DELETE"
    }
  );
}

export function exportFeedback(runId: number) {
  return requestFile(`/analysis-runs/${runId}/feedback/export`);
}
