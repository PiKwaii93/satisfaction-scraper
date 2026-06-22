export type SentimentLabel = "Positif" | "Neutre" | "Négatif";

export type AnalysisRun = {
  run_id: number;
  company_id: number;
  company_name: string;
  trustpilot_slug: string;
  source: "trustpilot";
  status: "pending" | "running" | "completed" | "failed" | "empty";
  pages_per_star: number;
  stars_requested: number[];
  total_reviews: number;
  celery_task_id: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  execution_duration_seconds: number | null;
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

export type BusinessInsightExample = {
  review_id: number;
  rating: number | null;
  sentiment_label: SentimentLabel;
  sentiment_score: number;
  verbatim: string | null;
};

export type BusinessPriority = {
  rank: number;
  topic: string;
  title: string;
  severity: "moderee" | "elevee" | "critique" | string;
  negative_reviews: number;
  share_of_reviews: number;
  impact: string;
  recommendation: string;
  examples: BusinessInsightExample[];
};

export type BusinessStrength = {
  topic: string;
  title: string;
  positive_reviews: number;
  recommendation: string;
  examples: BusinessInsightExample[];
};

export type BusinessWatchpoint = {
  title: string;
  message: string;
  level: "info" | "warning" | "error" | string;
};

export type BusinessInsights = {
  health_score: number;
  risk_level: "faible" | "modere" | "eleve" | "critique" | string;
  executive_summary: string;
  priorities: BusinessPriority[];
  strengths: BusinessStrength[];
  watchpoints: BusinessWatchpoint[];
  next_actions: string[];
  critical_review_count: number;
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
  business_insights: BusinessInsights;
};

export type ReviewListResponse = {
  run_id: number;
  total: number;
  limit: number;
  offset: number;
  reviews: Review[];
};
