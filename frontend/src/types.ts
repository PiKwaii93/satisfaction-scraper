export type SentimentLabel = "Positif" | "Neutre" | "Négatif";

export type AnalysisSource = "trustpilot" | "csv";

export type AnalysisRun = {
  run_id: number;
  company_id: number;
  company_name: string;
  trustpilot_slug: string;
  source: AnalysisSource;
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
  corrected_label: SentimentLabel | null;
  feedback_comment: string | null;
  feedback_updated_at: string | null;
  topics: string[];
};

export type CsvPreviewReview = {
  row_number: number;
  rating: number;
  author: string;
  date: string;
  company_responded: boolean;
  verbatim: string;
};

export type CsvColumnMapping = {
  verbatim?: string;
  rating?: string;
  author?: string;
  date?: string;
  company_responded?: string;
};

export type CsvImportPreview = {
  review_count: number;
  skipped_rows: number;
  detected_columns: Record<string, string>;
  available_columns: string[];
  preview_reviews: CsvPreviewReview[];
  error_message: string | null;
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
    feedback_count: number | null;
  };
  sentiment_distribution: DistributionRow<SentimentLabel>[];
  rating_distribution: DistributionRow<number>[];
  top_topics: DistributionRow[];
  critical_reviews: SummaryReview[];
  rating_text_mismatches: SummaryReview[];
  business_insights: BusinessInsights;
};

export type BenchmarkTopicCount = {
  topic: string;
  count: number;
};

export type BenchmarkCompanyTopic = {
  run_id: number;
  company_name: string;
  count: number;
};

export type BenchmarkCommonTopic = {
  topic: string;
  total_count: number;
  run_count: number;
  companies: BenchmarkCompanyTopic[];
};

export type BenchmarkCompany = {
  run_id: number;
  company_name: string;
  review_count: number;
  text_count: number;
  average_rating: number | null;
  average_confidence: number | null;
  health_score: number;
  risk_level: "faible" | "modere" | "eleve" | "critique" | string;
  negative_count: number;
  neutral_count: number;
  positive_count: number;
  negative_rate: number;
  top_topics: BenchmarkTopicCount[];
  unique_topics: BenchmarkTopicCount[];
};

export type BenchmarkHighlights = {
  best_health: BenchmarkCompany | null;
  highest_negative_rate: BenchmarkCompany | null;
  most_reviews: BenchmarkCompany | null;
  shared_priority: BenchmarkCommonTopic | null;
};

export type RunsComparison = {
  run_ids: number[];
  companies: BenchmarkCompany[];
  common_topics: BenchmarkCommonTopic[];
  highlights: BenchmarkHighlights;
};

export type ReviewListResponse = {
  run_id: number;
  total: number;
  limit: number;
  offset: number;
  reviews: Review[];
};

export type ReviewFeedback = {
  feedback_id: number;
  review_id: number;
  run_id: number;
  predicted_label: SentimentLabel;
  corrected_label: SentimentLabel;
  comment: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type FeedbackCompanySummary = {
  company_id: number;
  company_name: string;
  correction_count: number;
  changed_label_count: number;
  run_count: number;
  latest_feedback_at: string | null;
};

export type FeedbackLabelDistribution = {
  label: SentimentLabel;
  count: number;
};

export type FeedbackTransition = {
  predicted_label: SentimentLabel;
  corrected_label: SentimentLabel;
  count: number;
};

export type FeedbackRecentCorrection = {
  feedback_id: number;
  review_id: number;
  run_id: number;
  company_name: string;
  rating: number | null;
  predicted_label: SentimentLabel;
  corrected_label: SentimentLabel;
  feedback_comment: string | null;
  feedback_updated_at: string | null;
  verbatim: string | null;
};

export type FeedbackQuality = {
  total_corrections: number;
  changed_label_count: number;
  confirmed_label_count: number;
  apparent_error_rate: number;
  training_ready_count: number;
  corrected_company_count: number;
  corrected_run_count: number;
  latest_feedback_at: string | null;
  by_company: FeedbackCompanySummary[];
  corrected_label_distribution: FeedbackLabelDistribution[];
  transitions: FeedbackTransition[];
  recent_corrections: FeedbackRecentCorrection[];
};

export type ProductionModelInfo = {
  name: string;
  alias: string;
  version: string;
  run_id: string | null;
  source: string | null;
  model_uri: string;
};

export type ModelTrainingRun = {
  training_run_id: number;
  status: "pending" | "running" | "completed" | "failed";
  celery_task_id: string | null;
  trigger_source: string;
  feedback_sample_weight: number | null;
  training_rows: number;
  training_manual_rows: number;
  training_feedback_rows: number;
  training_effective_rows: number | null;
  accuracy: number | null;
  macro_f1: number | null;
  weighted_f1: number | null;
  model_version: string | null;
  mlflow_run_id: string | null;
  model_uri: string | null;
  error_message: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  execution_duration_seconds: number | null;
};

export type ModelTrainingOverview = {
  production_model: ProductionModelInfo | null;
  latest_run: ModelTrainingRun | null;
  active_run: ModelTrainingRun | null;
  runs: ModelTrainingRun[];
};
