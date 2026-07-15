export type SentimentLabel = "Positif" | "Neutre" | "Négatif";

export type AnalysisSource = "trustpilot" | "csv";

export type ReviewSourceStatus = "active" | "not_configured" | "error" | "planned";

export type ReviewSource = {
  source_id: string;
  label: string;
  status: ReviewSourceStatus;
  category: string;
  description: string;
  primary_action: string | null;
  setup_hint: string | null;
  supports_analysis: boolean;
  is_configured: boolean;
  is_enabled: boolean;
  can_configure: boolean;
  last_error: string | null;
  config: Record<string, unknown>;
  updated_at: string | null;
  required_fields: string[];
  optional_fields: string[];
  column_aliases: Record<string, string[]>;
};

export type ReviewSourceUpdate = {
  enabled?: boolean | null;
  config?: Record<string, unknown>;
};

export type Organization = {
  organization_id: number;
  name: string;
};

export type OrganizationSettings = {
  organization_id: number;
  name: string;
  slug: string;
  plan: OrganizationPlan;
  default_source: AnalysisSource;
  default_pages_per_star: number;
  created_at: string | null;
  updated_at: string | null;
};

export type OrganizationSettingsUpdate = {
  name?: string | null;
  default_source?: AnalysisSource | null;
  default_pages_per_star?: number | null;
};

export type OrganizationPlan = "free" | "pro" | "business";

export type OrganizationPlanUpdate = {
  plan: OrganizationPlan;
};

export type UpgradeRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "completed"
  | "cancelled";

export type UpgradeRequest = {
  upgrade_request_id: number;
  organization_id: number;
  organization_name?: string | null;
  organization_slug?: string | null;
  requested_plan: Exclude<OrganizationPlan, "free">;
  current_plan: OrganizationPlan;
  status: UpgradeRequestStatus;
  source: string | null;
  note: string | null;
  metadata: Record<string, unknown>;
  requested_by_email: string | null;
  created_at: string | null;
  updated_at: string | null;
  handled_at: string | null;
};

export type UpgradeRequestCreate = {
  requested_plan: Exclude<OrganizationPlan, "free">;
  source?: string | null;
  note?: string | null;
  metadata?: Record<string, unknown>;
};

export type OrganizationUsage = {
  plan: OrganizationPlan;
  plan_label: string;
  period_start: string | null;
  limits: {
    monthly_runs: number | null;
    monthly_reviews: number | null;
    csv_reviews_per_import: number | null;
    members: number | null;
  };
  usage: {
    monthly_runs: number;
    monthly_reviews: number;
    members: number;
  };
  features: {
    benchmark: boolean;
    model_training: boolean;
  };
};

export type OrganizationAuditEvent = {
  audit_event_id: number;
  event_type: string;
  actor_email: string | null;
  summary: string;
  entity_type: string | null;
  entity_id: number | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
};

export type ActionCenterSeverity = "critical" | "warning" | "info" | "success";

export type ActionCenterCounts = {
  open_alerts: number;
  critical_alerts: number;
  failed_runs: number;
  active_runs: number;
  pending_invitations: number;
  pending_upgrade_requests: number;
  training_ready_corrections: number;
  recent_completed_runs: number;
};

export type ActionCenterItem = {
  item_id: string;
  item_type: string;
  severity: ActionCenterSeverity;
  title: string;
  message: string;
  action_label: string | null;
  action_target: Record<string, unknown>;
  requires_admin: boolean;
  created_at: string | null;
};

export type ActionCenter = {
  counts: ActionCenterCounts;
  items: ActionCenterItem[];
};

export type CurrentUser = {
  user_id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  organization: Organization;
};

export type UserRole = "admin" | "member" | "platform_admin";
export type OrganizationMemberRole = "admin" | "member";
export type UserAccountStatus = "active" | "pending" | "inactive";

export type OrganizationUser = {
  user_id: number;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  account_status: UserAccountStatus;
  created_at: string | null;
  invited_at: string | null;
  activated_at: string | null;
  invitation_expires_at: string | null;
  invitation_accept_url: string | null;
};

export type OrganizationUserCreate = {
  email: string;
  password: string;
  full_name?: string | null;
  role: OrganizationMemberRole;
};

export type OrganizationInvitationCreate = {
  email: string;
  full_name?: string | null;
  role: OrganizationMemberRole;
};

export type OrganizationInvitationAccept = {
  token: string;
  password: string;
  full_name?: string | null;
};

export type AuthToken = {
  access_token: string;
  token_type: "bearer" | string;
  user: CurrentUser;
};

export type PlatformOrganization = {
  organization_id: number;
  name: string;
  slug: string;
  plan: OrganizationPlan;
  active_users: number;
  analysis_runs: number;
  total_reviews: number;
  open_upgrade_requests: number;
  created_at: string | null;
  updated_at: string | null;
};

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

export type TrendMetricChange = {
  metric: string;
  label: string;
  previous_value: number | null;
  current_value: number | null;
  delta: number | null;
  direction: "up" | "down" | "flat" | "unknown";
  unit: string | null;
};

export type TrendSentimentChange = {
  label: SentimentLabel | string;
  previous_count: number;
  current_count: number;
  previous_rate: number;
  current_rate: number;
  delta_count: number;
  delta_rate: number;
  direction: "up" | "down" | "flat";
};

export type TrendTopicChange = {
  topic: string;
  previous_count: number;
  current_count: number;
  delta_count: number;
  direction: "up" | "down" | "flat" | "new" | "resolved";
};

export type AnalysisRunTrend = {
  current_run: AnalysisRun;
  previous_run: AnalysisRun | null;
  has_previous: boolean;
  executive_summary: string;
  metrics: TrendMetricChange[];
  sentiment: TrendSentimentChange[];
  rising_topics: TrendTopicChange[];
  falling_topics: TrendTopicChange[];
  new_topics: TrendTopicChange[];
  resolved_topics: TrendTopicChange[];
};

export type BusinessAlertStatus = "open" | "acknowledged" | "resolved";
export type BusinessAlertSeverity = "info" | "warning" | "critical";

export type BusinessAlert = {
  alert_id: number;
  organization_id: number;
  run_id: number | null;
  company_id: number | null;
  company_name: string | null;
  alert_type: string;
  severity: BusinessAlertSeverity;
  title: string;
  message: string;
  status: BusinessAlertStatus;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
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
