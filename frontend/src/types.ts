export type SentimentLabel = "Positif" | "Neutre" | "Négatif";

export type AnalysisRun = {
  run_id: number;
  company_id: number;
  company_name: string;
  trustpilot_slug: string;
  source: "trustpilot";
  status: "pending" | "running" | "completed" | "failed";
  pages_per_star: number;
  stars_requested: number[];
  total_reviews: number;
  celery_task_id: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
};

export type AnalysisRunEvent = {
  event_id: number;
  run_id: number;
  level: "info" | "warning" | "error" | string;
  step: string | null;
  message: string;
  created_at: string | null;
};

export type DistributionRow<T extends string | number = string> = {
  label?: T;
  rating?: T;
  topic?: string;
  count: number;
};

export type Review = {
  review_id: number;
  rating: number | null;
  author_name: string | null;
  raw_date: string | null;
  verbatim: string | null;
  company_responded: boolean;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
  topics: string[];
};

export type SummaryReview = {
  review_id: number;
  rating: number | null;
  author_name: string | null;
  verbatim: string | null;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
};

export type RunSummary = {
  run: AnalysisRun;
  kpis: {
    review_count: number;
    average_rating: number | null;
    average_confidence: number | null;
    responded_count: number | null;
    text_count: number | null;
  };
  sentiment_distribution: DistributionRow<SentimentLabel>[];
  rating_distribution: DistributionRow<number>[];
  top_topics: DistributionRow[];
  critical_reviews: SummaryReview[];
  rating_text_mismatches: SummaryReview[];
};

export type ReviewListResponse = {
  run_id: number;
  total: number;
  limit: number;
  offset: number;
  reviews: Review[];
};
