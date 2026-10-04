import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type {
  ActionCenter,
  AnalysisRun,
  AuthToken,
  BusinessAlert,
  CurrentUser,
  CustomerAction,
  CustomerActionComment,
  CustomerActionImpact,
  CustomerActionTimelineItem,
  FeedbackQuality,
  ModelTrainingOverview,
  OrganizationSettings,
  OrganizationUsage,
  Review,
  ReviewSource,
  RunSummary
} from "./types";

const apiMocks = vi.hoisted(() => ({
  acceptOrganizationInvitation: vi.fn(),
  clearAuthToken: vi.fn(),
  compareRuns: vi.fn(),
  createModelTrainingRun: vi.fn(),
  createCustomerAction: vi.fn(),
  createCustomerActionComment: vi.fn(),
  createRun: vi.fn(),
  createUpgradeRequest: vi.fn(),
  deleteReviewFeedback: vi.fn(),
  executeRun: vi.fn(),
  exportFeedback: vi.fn(),
  exportReviews: vi.fn(),
  getCurrentUser: vi.fn(),
  getFeedbackQuality: vi.fn(),
  getModelTrainingOverview: vi.fn(),
  getOrganizationActionCenter: vi.fn(),
  getOrganizationSettings: vi.fn(),
  getOrganizationUsage: vi.fn(),
  getReviews: vi.fn(),
  getRunEvents: vi.fn(),
  getRunTrend: vi.fn(),
  getSummary: vi.fn(),
  hasAuthToken: vi.fn(),
  inviteOrganizationUser: vi.fn(),
  listBusinessAlerts: vi.fn(),
  listCustomerActions: vi.fn(),
  listCustomerActionComments: vi.fn(),
  listCustomerActionTimeline: vi.fn(),
  listOrganizationAuditEvents: vi.fn(),
  listOrganizationUsers: vi.fn(),
  listPlatformOrganizations: vi.fn(),
  listPlatformUpgradeRequests: vi.fn(),
  listReviewSources: vi.fn(),
  listRuns: vi.fn(),
  listUpgradeRequests: vi.fn(),
  login: vi.fn(),
  previewCsvFile: vi.fn(),
  refreshRunBusinessAlerts: vi.fn(),
  saveReviewFeedback: vi.fn(),
  updateBusinessAlertStatus: vi.fn(),
  updateCustomerAction: vi.fn(),
  updateOrganizationSettings: vi.fn(),
  updatePlatformOrganizationPlan: vi.fn(),
  updatePlatformUpgradeRequestStatus: vi.fn(),
  updateReviewSource: vi.fn(),
  uploadCsvRun: vi.fn()
}));

vi.mock("./api", () => apiMocks);

const adminUser: CurrentUser = {
  user_id: 1,
  email: "admin@example.test",
  full_name: "Admin Test",
  role: "admin",
  organization: {
    organization_id: 7,
    name: "Organisation Test"
  }
};

const memberUser: CurrentUser = {
  ...adminUser,
  user_id: 2,
  email: "member@example.test",
  full_name: "Member Test",
  role: "member"
};

const actionCenter: ActionCenter = {
  counts: {
    open_alerts: 0,
    critical_alerts: 0,
    failed_runs: 0,
    active_runs: 0,
    pending_invitations: 0,
    pending_upgrade_requests: 0,
    open_customer_actions: 0,
    training_ready_corrections: 0,
    recent_completed_runs: 0
  },
  items: []
};

const feedbackQuality: FeedbackQuality = {
  total_corrections: 0,
  changed_label_count: 0,
  confirmed_label_count: 0,
  apparent_error_rate: 0,
  training_ready_count: 0,
  corrected_company_count: 0,
  corrected_run_count: 0,
  latest_feedback_at: null,
  by_company: [],
  corrected_label_distribution: [],
  transitions: [],
  recent_corrections: []
};

const customerAction: CustomerAction = {
  action_id: 4,
  organization_id: 7,
  alert_id: 9,
  run_id: 21,
  company_name: "example.com",
  alert_type: "negative_share_high",
  alert_title: "Part d'avis negatifs a surveiller",
  title: "Traiter les avis negatifs",
  description: "Verifier les avis critiques.",
  priority: "high",
  status: "open",
  owner_name: null,
  due_date: null,
  notes: null,
  created_by_email: "admin@example.test",
  updated_by_email: null,
  created_at: null,
  updated_at: null,
  resolved_at: null,
  impact: null
};

const businessAlert: BusinessAlert = {
  alert_id: 9,
  organization_id: 7,
  run_id: 21,
  company_id: 3,
  company_name: "example.com",
  alert_type: "negative_share_high",
  severity: "warning",
  title: "Part d'avis negatifs a surveiller",
  message: "42% des avis sont negatifs.",
  status: "open",
  metadata: {},
  created_at: null,
  updated_at: null,
  acknowledged_at: null,
  resolved_at: null
};

const notMeasurableImpact: CustomerActionImpact = {
  status: "not_measurable",
  label: "A mesurer",
  summary: "Relance une analyse de la meme entreprise pour mesurer l'impact.",
  metric_label: "Part d'avis negatifs",
  unit: "pts",
  baseline_run_id: 21,
  comparison_run_id: null,
  baseline_value: null,
  comparison_value: null,
  delta: null
};

const measuredImpact: CustomerActionImpact = {
  status: "improved",
  label: "Amelioration",
  summary: "Part d'avis negatifs s'ameliore entre le run d'origine et le run suivant.",
  metric_label: "Part d'avis negatifs",
  unit: "pts",
  baseline_run_id: 21,
  comparison_run_id: 24,
  baseline_value: 42,
  comparison_value: 31,
  delta: -11
};

const customerActionComment: CustomerActionComment = {
  comment_id: 8,
  action_id: 4,
  organization_id: 7,
  author_user_id: 2,
  author_name: "Member Test",
  body: "Transporteur contacte ce matin.",
  created_at: null
};

const customerActionTimeline: CustomerActionTimelineItem[] = [
  {
    item_id: "audit-21",
    item_type: "audit_event",
    action_id: 4,
    organization_id: 7,
    audit_event_id: 21,
    comment_id: null,
    event_type: "customer_action.created",
    actor_email: "admin@example.test",
    author_user_id: null,
    author_name: "admin@example.test",
    summary: "Action client creee: Traiter les avis negatifs.",
    body: null,
    metadata: {},
    created_at: "2026-08-27T08:00:00Z"
  },
  {
    item_id: "comment-8",
    item_type: "comment",
    action_id: 4,
    organization_id: 7,
    audit_event_id: null,
    comment_id: 8,
    event_type: "customer_action.comment",
    actor_email: "member@example.test",
    author_user_id: 2,
    author_name: "Member Test",
    summary: "Note de suivi ajoutee.",
    body: "Transporteur contacte ce matin.",
    metadata: {},
    created_at: "2026-08-27T09:00:00Z"
  },
  {
    item_id: "audit-22",
    item_type: "audit_event",
    action_id: 4,
    organization_id: 7,
    audit_event_id: 22,
    comment_id: null,
    event_type: "customer_action.updated",
    actor_email: "admin@example.test",
    author_user_id: null,
    author_name: "admin@example.test",
    summary: "Action client mise a jour: Traiter les avis negatifs.",
    body: null,
    metadata: {
      status: "resolved",
      priority: "critical"
    },
    created_at: "2026-08-27T10:00:00Z"
  }
];

const trainingOverview: ModelTrainingOverview = {
  production_model: null,
  latest_run: null,
  active_run: null,
  runs: []
};

const organizationSettings: OrganizationSettings = {
  organization_id: 7,
  name: "Organisation Test",
  slug: "organisation-test",
  plan: "business",
  default_source: "trustpilot",
  default_pages_per_star: 1,
  created_at: null,
  updated_at: null
};

const organizationUsage: OrganizationUsage = {
  plan: "business",
  plan_label: "Business",
  period_start: null,
  limits: {
    monthly_runs: null,
    monthly_reviews: 100000,
    csv_reviews_per_import: 10000,
    members: 25
  },
  usage: {
    monthly_runs: 0,
    monthly_reviews: 0,
    members: 1
  },
  features: {
    benchmark: true,
    model_training: true
  }
};

const freeLimitUsage: OrganizationUsage = {
  ...organizationUsage,
  plan: "free",
  plan_label: "Free",
  limits: {
    monthly_runs: 3,
    monthly_reviews: 300,
    csv_reviews_per_import: 100,
    members: 1
  },
  usage: {
    monthly_runs: 3,
    monthly_reviews: 120,
    members: 1
  },
  features: {
    benchmark: false,
    model_training: false
  }
};

const proUsage: OrganizationUsage = {
  ...organizationUsage,
  plan: "pro",
  plan_label: "Pro",
  limits: {
    monthly_runs: 50,
    monthly_reviews: 10000,
    csv_reviews_per_import: 2000,
    members: 5
  },
  features: {
    benchmark: true,
    model_training: false
  }
};

const reviewSources: ReviewSource[] = [
  {
    source_id: "trustpilot",
    label: "Trustpilot",
    status: "active",
    category: "web public",
    description: "Avis publics Trustpilot.",
    primary_action: "Coller une URL",
    setup_hint: null,
    supports_analysis: true,
    is_configured: true,
    is_enabled: true,
    can_configure: true,
    last_error: null,
    config: {},
    updated_at: null,
    required_fields: [],
    optional_fields: [],
    column_aliases: {}
  },
  {
    source_id: "csv",
    label: "CSV",
    status: "active",
    category: "import fichier",
    description: "Import CSV",
    primary_action: "Importer un fichier CSV",
    setup_hint: null,
    supports_analysis: true,
    is_configured: true,
    is_enabled: true,
    can_configure: true,
    last_error: null,
    config: {},
    updated_at: null,
    required_fields: ["verbatim"],
    optional_fields: ["rating", "author", "date", "company_responded"],
    column_aliases: {}
  }
];

function makeAnalysisRun(overrides: Partial<AnalysisRun> = {}): AnalysisRun {
  const source = overrides.source ?? "trustpilot";
  return {
    run_id: 21,
    company_id: 4,
    company_name: source === "csv" ? "Client CSV" : "example.com",
    trustpilot_slug: source === "csv" ? "client-csv" : "example.com",
    source,
    status: "pending",
    collection_mode: "representative",
    max_pages: 25,
    pages_per_star: 1,
    stars_requested: [1, 2, 3, 4, 5],
    pages_requested: 25,
    pages_processed: 5,
    pages_succeeded: 5,
    pages_failed: 0,
    reviews_extracted: 12,
    unique_reviews: 12,
    stop_reason: "natural_end",
    is_representative_for_business_kpis: true,
    business_kpi_warning: null,
    total_reviews: 0,
    celery_task_id: null,
    created_at: null,
    started_at: null,
    finished_at: null,
    execution_duration_seconds: null,
    error_message: null,
    ...overrides
  };
}

function makeSummaryReview(
  overrides: Partial<RunSummary["critical_reviews"][number]> = {}
): RunSummary["critical_reviews"][number] {
  return {
    review_id: 301,
    rating: 1,
    author_name: "Client presse",
    verbatim: "La livraison est arrivee trop tard et sans information claire.",
    sentiment_label: "Négatif",
    sentiment_score: -0.82,
    ...overrides
  };
}

function makeBusinessInsights(
  overrides: Partial<RunSummary["business_insights"]> = {}
): RunSummary["business_insights"] {
  return {
    health_score: 58,
    risk_level: "modere",
    executive_summary:
      "Les avis exploitables montrent un risque concentre sur les delais de livraison.",
    priorities: [
      {
        rank: 1,
        topic: "livraison",
        title: "Retards de livraison",
        severity: "elevee",
        negative_reviews: 4,
        share_of_reviews: 33.3,
        impact: "Les retards concentrent les avis negatifs les plus recents.",
        recommendation: "Prioriser le suivi transporteur sur les commandes en retard.",
        examples: [
          {
            review_id: 301,
            rating: 1,
            sentiment_label: "Négatif",
            sentiment_score: -0.82,
            verbatim: "La livraison est arrivee trop tard."
          }
        ]
      }
    ],
    strengths: [
      {
        topic: "produit",
        title: "Produit conforme",
        positive_reviews: 3,
        recommendation: "Conserver la qualite percue du produit.",
        examples: []
      }
    ],
    watchpoints: [
      {
        title: "Reponses clients",
        message: "Peu de reponses entreprise sur les avis negatifs.",
        level: "warning"
      }
    ],
    next_actions: ["Contacter le transporteur sur les commandes en retard"],
    critical_review_count: 2,
    ...overrides
  };
}

function makeRunSummary(overrides: Partial<RunSummary> = {}): RunSummary {
  const run =
    overrides.run ??
    makeAnalysisRun({
      status: "completed",
      total_reviews: 12,
      execution_duration_seconds: 96
    });
  return {
    run,
    kpis: {
      review_count: 12,
      average_rating: 3.4,
      average_confidence: 0.88,
      responded_count: 2,
      text_count: 10,
      feedback_count: 0
    },
    sentiment_distribution: [
      { label: "Négatif", count: 4 },
      { label: "Neutre", count: 3 },
      { label: "Positif", count: 5 }
    ],
    rating_distribution: [
      { rating: 1, count: 1 },
      { rating: 2, count: 3 },
      { rating: 3, count: 3 },
      { rating: 4, count: 2 },
      { rating: 5, count: 3 }
    ],
    top_topics: [{ topic: "livraison", count: 4 }],
    critical_reviews: [makeSummaryReview()],
    rating_text_mismatches: [
      makeSummaryReview({
        review_id: 302,
        rating: 5,
        verbatim: "La note est haute mais le texte critique la livraison."
      })
    ],
    business_insights: makeBusinessInsights(),
    ...overrides
  };
}

function makeReview(overrides: Partial<Review> = {}): Review {
  return {
    review_id: 301,
    rating: 1,
    author_name: "Client presse",
    raw_date: "2026-08-27",
    verbatim: "La livraison est arrivee trop tard et sans information claire.",
    company_responded: false,
    sentiment_label: "Négatif",
    sentiment_score: -0.82,
    corrected_label: null,
    feedback_comment: null,
    feedback_updated_at: null,
    topics: ["livraison"],
    ...overrides
  };
}

function configureAuthenticatedSession(user: CurrentUser) {
  apiMocks.hasAuthToken.mockReturnValue(true);
  apiMocks.getCurrentUser.mockResolvedValue(user);
  apiMocks.listOrganizationUsers.mockResolvedValue([
    {
      user_id: user.user_id,
      email: user.email,
      full_name: user.full_name,
      role: user.role,
      is_active: true,
      account_status: "active",
      created_at: null,
      invited_at: null,
      activated_at: null,
      invitation_expires_at: null,
      invitation_accept_url: null
    }
  ]);
}

beforeEach(() => {
  vi.clearAllMocks();
  Element.prototype.scrollIntoView = vi.fn();
  apiMocks.hasAuthToken.mockReturnValue(false);
  apiMocks.listRuns.mockResolvedValue([]);
  apiMocks.getRunEvents.mockResolvedValue([]);
  apiMocks.getFeedbackQuality.mockResolvedValue(feedbackQuality);
  apiMocks.getModelTrainingOverview.mockResolvedValue(trainingOverview);
  apiMocks.listBusinessAlerts.mockResolvedValue([]);
  apiMocks.listCustomerActions.mockResolvedValue([]);
  apiMocks.listCustomerActionComments.mockResolvedValue([customerActionComment]);
  apiMocks.listCustomerActionTimeline.mockResolvedValue(customerActionTimeline);
  apiMocks.createCustomerAction.mockResolvedValue(customerAction);
  apiMocks.createCustomerActionComment.mockResolvedValue({
    ...customerActionComment,
    comment_id: 9,
    body: "Verifier le suivi livraison."
  });
  apiMocks.updateCustomerAction.mockResolvedValue({
    ...customerAction,
    status: "resolved"
  });
  apiMocks.getOrganizationActionCenter.mockResolvedValue(actionCenter);
  apiMocks.listOrganizationUsers.mockResolvedValue([]);
  apiMocks.getOrganizationSettings.mockResolvedValue(organizationSettings);
  apiMocks.getOrganizationUsage.mockResolvedValue(organizationUsage);
  apiMocks.listOrganizationAuditEvents.mockResolvedValue([]);
  apiMocks.listPlatformOrganizations.mockResolvedValue([]);
  apiMocks.listPlatformUpgradeRequests.mockResolvedValue([]);
  apiMocks.listReviewSources.mockResolvedValue(reviewSources);
  apiMocks.listUpgradeRequests.mockResolvedValue([]);
});

describe("App authentication and permissions", () => {
  it("shows the login screen when no session exists", async () => {
    render(<App />);

    expect(
      await screen.findByRole("heading", {
        name: "Accéder à ton espace entreprise"
      })
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toHaveValue(
      "demo@satisfaction.local"
    );
    expect(screen.getByRole("button", { name: "Se connecter" })).toBeEnabled();
  });

  it("opens an authenticated session after a successful login", async () => {
    const user = userEvent.setup();
    const token: AuthToken = {
      access_token: "valid-token",
      token_type: "bearer",
      user: adminUser
    };
    apiMocks.login.mockResolvedValue(token);

    render(<App />);
    await user.click(await screen.findByRole("button", { name: "Se connecter" }));

    expect(apiMocks.login).toHaveBeenCalledWith(
      "demo@satisfaction.local",
      "demo-password"
    );
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    expect(screen.getByText("Organisation Test")).toBeInTheDocument();
  });

  it("keeps analysis creation read-only for a member", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(memberUser);

    render(<App />);
    expect(await screen.findByText(memberUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(
      screen.getByText(/Mode lecture seule : demande à un administrateur/)
    ).toBeInTheDocument();
    const heading = await screen.findByRole("heading", {
      name: "Aucune analyse lancée"
    });
    const emptyState = heading.closest(".first-run-empty-state");
    expect(emptyState).not.toBeNull();
    expect(
      within(emptyState as HTMLElement).getByRole("button", { name: /Trustpilot/ })
    ).toBeDisabled();
    expect(
      within(emptyState as HTMLElement).getByRole("button", { name: /CSV/ })
    ).toBeDisabled();
    expect(screen.getByLabelText("Entreprise ou URL Trustpilot")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Lancer l'analyse" })).toBeDisabled();
  });

  it("shows a clear empty state and source choice for a first analysis", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    const heading = await screen.findByRole("heading", {
      name: "Aucune analyse lancée"
    });
    const emptyState = heading.closest(".first-run-empty-state");
    expect(emptyState).not.toBeNull();
    const withinEmptyState = within(emptyState as HTMLElement);

    expect(
      withinEmptyState.getByText(/Lance une première analyse pour générer les KPI/)
    ).toBeInTheDocument();
    const trustpilotOption = withinEmptyState.getByRole("button", {
      name: /Trustpilot/
    });
    const csvOption = withinEmptyState.getByRole("button", { name: /CSV/ });
    expect(trustpilotOption).toBeEnabled();
    expect(csvOption).toBeEnabled();
    expect(
      within(trustpilotOption).getByText(
        "Analyse les avis provenant d'une entreprise ou d'une page Trustpilot."
      )
    ).toBeInTheDocument();
    expect(
      within(csvOption).getByText(
        "Importe tes propres avis ou données client depuis un fichier."
      )
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Analyse les avis publics d'une entreprise ou d'une page Trustpilot."
      ).length
    ).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Importe tes propres avis depuis un fichier CSV.")
        .length
    ).toBeGreaterThan(0);
  });

  it("keeps only legitimate Trustpilot user input when switching to CSV", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);

    function firstRunEmptyState() {
      const heading = screen.getByRole("heading", {
        name: "Aucune analyse lancée"
      });
      const emptyState = heading.closest(".first-run-empty-state");
      expect(emptyState).not.toBeNull();
      return within(emptyState as HTMLElement);
    }

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await screen.findByRole("heading", { name: "Aucune analyse lancée" });

    await user.click(firstRunEmptyState().getByRole("button", { name: /CSV/ }));
    expect(screen.getByLabelText("Entreprise à analyser")).toHaveValue("");

    await user.click(firstRunEmptyState().getByRole("button", { name: /Trustpilot/ }));
    const trustpilotInput = screen.getByLabelText("Entreprise ou URL Trustpilot");
    await user.type(
      trustpilotInput,
      "https://fr.trustpilot.com/review/acme.example"
    );

    await user.click(firstRunEmptyState().getByRole("button", { name: /CSV/ }));
    expect(screen.getByLabelText("Entreprise à analyser")).toHaveValue(
      "https://fr.trustpilot.com/review/acme.example"
    );
  });

  it("sends the onboarding first-analysis CTA to the analyses form", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();

    const onboardingPanel = screen
      .getByText("Parcours de configuration")
      .closest(".onboarding-panel");
    expect(onboardingPanel).not.toBeNull();
    await user.click(
      within(onboardingPanel as HTMLElement).getByRole("button", {
        name: "Nouvelle analyse"
      })
    );

    const analysisInput = screen.getByLabelText("Entreprise ou URL Trustpilot");
    expect(analysisInput).toBeInTheDocument();
    expect(document.getElementById("new_analysis")).toContainElement(
      analysisInput
    );
    expect(
      await screen.findByRole("heading", { name: "Aucune analyse lancée" })
    ).toBeInTheDocument();
  });

  it("keeps every onboarding step visible while configuration is incomplete", async () => {
    configureAuthenticatedSession(adminUser);

    render(<App />);
    const panel = (await screen.findByText("Parcours de configuration")).closest(
      ".onboarding-panel"
    );
    expect(panel).not.toBeNull();
    expect(within(panel as HTMLElement).getAllByRole("article")).toHaveLength(5);
    expect(within(panel as HTMLElement).queryByRole("button", { name: "Voir le détail" })).not.toBeInTheDocument();
  });

  it("shows completed onboarding compactly, then opens and closes its actions", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([makeAnalysisRun({ status: "completed" })]);
    apiMocks.getSummary.mockResolvedValue(makeRunSummary());
    apiMocks.getReviews.mockResolvedValue({ reviews: [], total: 0 });
    apiMocks.getRunTrend.mockResolvedValue(null);
    apiMocks.getFeedbackQuality.mockResolvedValue({
      ...feedbackQuality,
      total_corrections: 1
    });
    apiMocks.listOrganizationUsers.mockResolvedValue([
      { user_id: adminUser.user_id },
      { user_id: 2 }
    ]);

    render(<App />);
    const panel = (await screen.findByText("Configuration terminée")).closest(
      ".onboarding-panel"
    );
    expect(panel).not.toBeNull();
    const completedPanel = within(panel as HTMLElement);
    expect(completedPanel.getByText("5/5 étapes complétées")).toBeInTheDocument();
    expect(completedPanel.queryByRole("article")).not.toBeInTheDocument();
    const toggle = completedPanel.getByRole("button", { name: "Voir le détail" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(completedPanel.getByRole("button", { name: "Masquer le détail" })).toHaveAttribute(
      "aria-expanded", "true"
    );
    expect(completedPanel.getAllByRole("article")).toHaveLength(5);
    expect(completedPanel.getByRole("button", { name: "Voir les sources" })).toBeEnabled();
    await user.click(completedPanel.getByRole("button", { name: "Masquer le détail" }));
    expect(completedPanel.queryByRole("article")).not.toBeInTheDocument();
    expect(completedPanel.getByRole("button", { name: "Voir le détail" })).toHaveAttribute(
      "aria-expanded", "false"
    );
    expect(screen.getByRole("heading", { name: "Priorités opérationnelles" })).toBeInTheDocument();
    await user.keyboard("{Enter}");
    expect(completedPanel.getAllByRole("article")).toHaveLength(5);
    await user.click(completedPanel.getByRole("button", { name: "Voir les sources" }));
    expect(screen.getByRole("heading", { name: "Analyses" })).toBeInTheDocument();
    expect(document.getElementById("review_sources")).toBeInTheDocument();
  });

  it("keeps sidebar navigation and contextual controls available", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([makeAnalysisRun()]);

    render(<App />);
    await screen.findByText(adminUser.email);
    const navigation = screen.getByRole("navigation", { name: "Espaces produit" });
    expect(within(navigation).getAllByRole("button")).toHaveLength(6);
    expect(within(navigation).queryByText("Priorités et alertes")).not.toBeInTheDocument();
    await user.click(within(navigation).getByRole("button", { name: /Analyses/ }));
    expect(await screen.findByRole("heading", { name: "Historique" })).toBeInTheDocument();
    expect(screen.getByLabelText("Entreprise ou URL Trustpilot")).toBeInTheDocument();
    await user.click(within(navigation).getByRole("button", { name: /Benchmark/ }));
    expect(screen.getByRole("button", { name: "Effacer la sélection" })).toBeInTheDocument();
    await user.click(within(navigation).getByRole("button", { name: /Accueil/ }));
    expect(screen.getByRole("heading", { name: "Priorités opérationnelles" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Se déconnecter" })).toBeInTheDocument();
  });

  it("lets an admin launch a Trustpilot analysis", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.createRun.mockResolvedValue(makeAnalysisRun());

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    const companyInput = screen.getByLabelText("Entreprise ou URL Trustpilot");
    await user.clear(companyInput);
    await user.type(companyInput, "https://fr.trustpilot.com/review/example.com");
    await user.click(screen.getByRole("button", { name: "Lancer l'analyse" }));

    await waitFor(() =>
      expect(apiMocks.createRun).toHaveBeenCalledWith({
        company: "https://fr.trustpilot.com/review/example.com",
        source: "trustpilot",
        stars: [1, 2, 3, 4, 5],
        pages_per_star: 1,
        execute_immediately: true
      })
    );
    expect(
      await screen.findByRole("button", { name: /example\.com.*Analyse nº 21/i })
    ).toBeInTheDocument();
  });

  it("keeps a created Trustpilot run visible when run refresh fails", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("Historique indisponible"));
    apiMocks.createRun.mockResolvedValue(makeAnalysisRun());

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await screen.findByRole("heading", { name: "Aucune analyse lancée" });
    const companyInput = screen.getByLabelText("Entreprise ou URL Trustpilot");
    await user.clear(companyInput);
    await user.type(companyInput, "https://fr.trustpilot.com/review/example.com");
    await user.click(screen.getByRole("button", { name: "Lancer l'analyse" }));

    expect(
      await screen.findByText(
        "Analyse lancée, mais l'actualisation des données a échoué : Historique indisponible"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /example\.com.*Analyse nº 21/i })
    ).toBeInTheDocument();
  });

  it("does not duplicate a created run after a successful refresh", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const createdRun = makeAnalysisRun();
    apiMocks.listRuns.mockResolvedValueOnce([]).mockResolvedValueOnce([createdRun]);
    apiMocks.createRun.mockResolvedValue(createdRun);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await screen.findByRole("heading", { name: "Aucune analyse lancée" });
    const companyInput = screen.getByLabelText("Entreprise ou URL Trustpilot");
    await user.clear(companyInput);
    await user.type(companyInput, "https://fr.trustpilot.com/review/example.com");
    await user.click(screen.getByRole("button", { name: "Lancer l'analyse" }));

    await screen.findByRole("button", { name: /example\.com.*Analyse nº 21/i });
    await waitFor(() => expect(apiMocks.listRuns).toHaveBeenCalledTimes(2));
    const historyPanel = screen.getByText("Historique").closest(".run-panel");
    expect(historyPanel).not.toBeNull();
    await waitFor(() =>
      expect(
        within(historyPanel as HTMLElement).getAllByRole("button", {
          name: /Analyse nº 21/i
        })
      ).toHaveLength(1)
    );
  });

  it("keeps polling a newly created active run", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const pendingRun = makeAnalysisRun({ status: "pending" });
    const runningRun = makeAnalysisRun({ status: "running", total_reviews: 3 });
    apiMocks.listRuns
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValue([runningRun]);
    apiMocks.createRun.mockResolvedValue(pendingRun);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await screen.findByRole("heading", { name: "Aucune analyse lancée" });
    const companyInput = screen.getByLabelText("Entreprise ou URL Trustpilot");
    await user.clear(companyInput);
    await user.type(companyInput, "https://fr.trustpilot.com/review/example.com");
    await user.click(screen.getByRole("button", { name: "Lancer l'analyse" }));

    expect(
      await screen.findByRole("button", { name: /example\.com.*Analyse nº 21/i })
    ).toBeInTheDocument();
    expect(screen.getAllByText("En attente").length).toBeGreaterThan(0);
    await waitFor(
      () => expect(apiMocks.listRuns.mock.calls.length).toBeGreaterThanOrEqual(3),
      { timeout: 4500 }
    );
    expect(screen.getAllByText("En cours").length).toBeGreaterThan(0);
  });

  it("lets an admin save the Trustpilot source defaults", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    const defaultCompanyInput = await screen.findByPlaceholderText(
      "https://fr.trustpilot.com/review/www.darty.com"
    );
    await user.clear(defaultCompanyInput);
    await user.type(
      defaultCompanyInput,
      "https://fr.trustpilot.com/review/example.com"
    );
    await user.click(screen.getByRole("button", { name: "Enregistrer" }));

    await waitFor(() =>
      expect(apiMocks.updateReviewSource).toHaveBeenCalledWith("trustpilot", {
        enabled: true,
        config: {
          default_company: "https://fr.trustpilot.com/review/example.com",
          pages_per_star: 1
        }
      })
    );
  });

  it("keeps configured Sources compact and restores the saved Trustpilot values on cancel", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listReviewSources.mockResolvedValue([
      { ...reviewSources[0], config: { default_company: "example.com", pages_per_star: 3 } },
      { ...reviewSources[1], config: { column_mapping: { verbatim: "commentaire", rating: "note" } } },
      { ...reviewSources[0], source_id: "google", label: "Google Reviews", status: "planned", supports_analysis: false, can_configure: false }
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Sources/ }));
    const workspace = screen.getByRole("heading", { name: "Catalogue des connecteurs" }).closest(".sources-workspace") as HTMLElement;

    expect(within(workspace).getByText("example.com")).toBeInTheDocument();
    expect(within(workspace).getByText("3 pages par note")).toBeInTheDocument();
    expect(within(workspace).getByText(/Texte : commentaire/)).toBeInTheDocument();
    expect(within(workspace).getByText("Google Reviews")).toBeInTheDocument();
    expect(within(workspace).getByText("Bientôt")).toBeInTheDocument();
    expect(within(workspace).queryByLabelText("Entreprise par défaut")).not.toBeInTheDocument();
    expect(within(workspace).getAllByRole("button", { name: "Utiliser pour une analyse" })).toHaveLength(2);

    const trustpilotCard = within(workspace).getByText("example.com").closest(".connector-card") as HTMLElement;
    const editButton = within(trustpilotCard).getByRole("button", { name: "Modifier" });
    expect(editButton).toHaveAttribute("aria-expanded", "false");
    await user.click(editButton);
    expect(within(trustpilotCard).getByRole("button", { name: "Masquer la configuration" })).toHaveAttribute("aria-expanded", "true");
    const companyInput = within(trustpilotCard).getByLabelText("Entreprise par défaut");
    expect(companyInput).toHaveValue("example.com");
    await user.clear(companyInput);
    await user.type(companyInput, "changed.example");
    await user.click(within(trustpilotCard).getByRole("button", { name: "Annuler" }));
    expect(within(trustpilotCard).queryByLabelText("Entreprise par défaut")).not.toBeInTheDocument();
    await user.click(within(trustpilotCard).getByRole("button", { name: "Modifier" }));
    expect(within(trustpilotCard).getByLabelText("Entreprise par défaut")).toHaveValue("example.com");
    expect(apiMocks.updateReviewSource).not.toHaveBeenCalled();

    const details = within(workspace).getByRole("button", { name: "Voir les détails" });
    expect(details).toHaveAttribute("aria-expanded", "false");
    await user.click(details);
    expect(within(workspace).getByRole("button", { name: "Masquer les détails" })).toHaveAttribute("aria-expanded", "true");
    expect(within(workspace).getByText("Champs et format CSV")).toBeInTheDocument();
    expect(within(workspace).getAllByText(/Champs requis :/)).toHaveLength(2);
    await user.click(within(workspace).getByRole("button", { name: "Masquer les détails" }));
    expect(within(workspace).getByRole("button", { name: "Voir les détails" })).toHaveAttribute("aria-expanded", "false");
  });

  it("saves Sources edits through the existing source API and keeps a failed editor open", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listReviewSources.mockResolvedValue([
      { ...reviewSources[0], config: { default_company: "example.com", pages_per_star: 2 } },
      { ...reviewSources[1], config: { column_mapping: { verbatim: "commentaire" } } }
    ]);
    apiMocks.updateReviewSource.mockResolvedValue(reviewSources[0]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Sources/ }));
    const workspace = screen.getByRole("heading", { name: "Catalogue des connecteurs" }).closest(".sources-workspace") as HTMLElement;
    const trustpilotCard = within(workspace).getByText("example.com").closest(".connector-card") as HTMLElement;
    await user.click(within(trustpilotCard).getByRole("button", { name: "Modifier" }));
    await user.click(within(trustpilotCard).getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(apiMocks.updateReviewSource).toHaveBeenCalledWith("trustpilot", {
      enabled: true,
      config: { default_company: "example.com", pages_per_star: 2 }
    }));
    await waitFor(() => expect(within(trustpilotCard).queryByLabelText("Entreprise par défaut")).not.toBeInTheDocument());

    const csvCard = within(workspace).getByText(/Texte : commentaire/).closest(".connector-card") as HTMLElement;
    await user.click(within(csvCard).getByRole("button", { name: "Modifier" }));
    expect(within(csvCard).getByLabelText("Texte *")).toHaveValue("commentaire");
    await user.click(within(csvCard).getByRole("button", { name: "Enregistrer" }));
    await waitFor(() => expect(apiMocks.updateReviewSource).toHaveBeenCalledWith("csv", {
      enabled: true,
      config: { column_mapping: { verbatim: "commentaire" } }
    }));
    await waitFor(() => expect(within(csvCard).queryByLabelText("Texte *")).not.toBeInTheDocument());
    apiMocks.updateReviewSource.mockRejectedValueOnce(new Error("Sauvegarde indisponible"));
    await user.click(within(csvCard).getByRole("button", { name: "Modifier" }));
    await user.click(within(csvCard).getByRole("button", { name: "Enregistrer" }));
    expect(await within(workspace).findByText("Sauvegarde indisponible")).toBeInTheDocument();
    expect(within(csvCard).getByLabelText("Texte *")).toHaveValue("commentaire");
  });

  it("shows Trustpilot configuration immediately when the connector is not configured", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listReviewSources.mockResolvedValue([
      { ...reviewSources[0], status: "not_configured", is_configured: false, config: {} },
      reviewSources[1]
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Sources/ }));
    const workspace = screen.getByRole("heading", { name: "Catalogue des connecteurs" }).closest(".sources-workspace") as HTMLElement;
    expect(within(workspace).getByLabelText("Entreprise par défaut")).toBeInTheDocument();
    expect(within(workspace).getByRole("button", { name: "Configurer le mapping" })).toBeInTheDocument();
  });

  it("lets an admin save a reusable CSV mapping profile", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.previewCsvFile.mockResolvedValue({
      review_count: 1,
      skipped_rows: 0,
      detected_columns: {
        verbatim: "commentaire",
        rating: "note"
      },
      available_columns: ["commentaire", "note", "client"],
      preview_reviews: [
        {
          row_number: 1,
          rating: 5,
          author: "",
          date: "",
          company_responded: false,
          verbatim: "Produit conforme"
        }
      ],
      error_message: null
    });
    apiMocks.updateReviewSource.mockResolvedValue({
      ...reviewSources[1],
      config: {
        column_mapping: {
          verbatim: "commentaire",
          rating: "note"
        }
      }
    });

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await user.click(screen.getAllByRole("button", { name: /CSV/ })[0]);

    const file = new File(["commentaire,note\nProduit conforme,5\n"], "avis.csv", {
      type: "text/csv"
    });
    await user.upload(screen.getByLabelText("Fichier CSV d'avis"), file);
    await screen.findByText("Contrôle avant import");
    expect(
      screen.getByText("Mapping prêt à être réutilisé par l'organisation.")
    ).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Texte *"), "");
    await waitFor(() =>
      expect(
        screen.getByText("Sélectionne la colonne Texte pour obtenir un mapping prêt.")
      ).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: "Enregistrer ce mapping" })).toBeDisabled();
    await user.selectOptions(screen.getByLabelText("Texte *"), "commentaire");
    await waitFor(() =>
      expect(
        screen.getByText("Mapping prêt à être réutilisé par l'organisation.")
      ).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: "Enregistrer ce mapping" }));

    await waitFor(() =>
      expect(apiMocks.updateReviewSource).toHaveBeenCalledWith("csv", {
        enabled: true,
        config: {
          column_mapping: {
            verbatim: "commentaire",
            rating: "note"
          }
        }
      })
    );
  });

  it("keeps an imported CSV run visible when run refresh fails", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const createdRun = makeAnalysisRun({
      run_id: 31,
      company_name: "Client CSV",
      source: "csv",
      trustpilot_slug: "client-csv"
    });
    apiMocks.listRuns
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("Historique CSV indisponible"));
    apiMocks.previewCsvFile.mockResolvedValue({
      review_count: 1,
      skipped_rows: 0,
      detected_columns: {
        verbatim: "commentaire",
        rating: "note"
      },
      available_columns: ["commentaire", "note", "client"],
      preview_reviews: [
        {
          row_number: 1,
          rating: 5,
          author: "",
          date: "",
          company_responded: false,
          verbatim: "Produit conforme"
        }
      ],
      error_message: null
    });
    apiMocks.uploadCsvRun.mockResolvedValue(createdRun);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    const heading = await screen.findByRole("heading", {
      name: "Aucune analyse lancée"
    });
    const emptyState = heading.closest(".first-run-empty-state");
    expect(emptyState).not.toBeNull();
    await user.click(within(emptyState as HTMLElement).getByRole("button", { name: /CSV/ }));
    expect(screen.getByLabelText("Entreprise à analyser")).toHaveValue("");

    await user.type(screen.getByLabelText("Entreprise à analyser"), "Client CSV");
    const file = new File(["commentaire,note\nProduit conforme,5\n"], "avis.csv", {
      type: "text/csv"
    });
    await user.upload(screen.getByLabelText("Fichier CSV d'avis"), file);
    await screen.findByText("Contrôle avant import");
    await user.click(screen.getByRole("button", { name: "Importer le CSV" }));

    await waitFor(() =>
      expect(apiMocks.uploadCsvRun).toHaveBeenCalledWith(
        "Client CSV",
        file,
        expect.objectContaining({ verbatim: "commentaire" })
      )
    );
    expect(
      await screen.findByText(
        "Analyse lancée, mais l'actualisation des données a échoué : Historique CSV indisponible"
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Client CSV.*Analyse nº 31/i })
    ).toBeInTheDocument();
  });

  it("clarifies an empty Trustpilot run without presenting it as failed", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([
      makeAnalysisRun({
        status: "empty",
        error_message: null
      })
    ]);
    apiMocks.getRunEvents.mockResolvedValue([
      {
        event_id: 1,
        run_id: 21,
        level: "warning",
        step: "scrape_complete",
        message: "Aucun avis recupere pour cette URL.",
        created_at: "2026-08-27T08:00:00Z"
      }
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(
      await screen.findByText("Analyse terminée, aucun avis exploitable")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Trustpilot a été interrogé, mais aucun avis exploitable n'a été récupéré pour cette analyse."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Cette analyse n'est pas en échec technique, mais elle ne contient pas assez de données exploitables pour afficher les KPI et irritants."
      )
    ).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Exécution" }));
    expect(screen.getByText("1 événement")).toBeInTheDocument();
    expect(screen.getByText("1 avertissement")).toBeInTheDocument();
    expect(screen.getByText(/Dernière étape : Scraping/)).toBeInTheDocument();
    expect(screen.queryByText("Analyse échouée")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Relancer l'analyse" })
    ).not.toBeInTheDocument();
  });

  it("clarifies an empty CSV import with CSV-specific guidance", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([
      makeAnalysisRun({
        source: "csv",
        status: "empty",
        company_name: "Client CSV",
        trustpilot_slug: "client-csv",
        error_message: null
      })
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(
      await screen.findByText("Import terminé, aucun avis exploitable")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Le fichier CSV a bien été traité, mais aucune ligne n'a permis de produire un rapport exploitable."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Vérifie que la colonne Texte est bien mappée sur les verbatims.")
    ).toBeInTheDocument();
    expect(
      screen.queryByText(
        "Trustpilot a été interrogé, mais aucun avis exploitable n'a été récupéré pour cette analyse."
      )
    ).not.toBeInTheDocument();
  });

  it("shows a non-misleading empty journal state", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([
      makeAnalysisRun({
        status: "empty",
        error_message: null
      })
    ]);
    apiMocks.getRunEvents.mockResolvedValue([]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(
      await screen.findByText("Analyse terminée, aucun avis exploitable")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Exécution" }));
    expect(
      screen.getByText(
        "Aucun événement journalisé pour cette analyse. Le message affiché au-dessus reste la référence."
      )
    ).toBeInTheDocument();
    expect(screen.queryByText("0 événement")).not.toBeInTheDocument();
    expect(screen.queryByText("0 erreur")).not.toBeInTheDocument();
    expect(screen.queryByText("0 avertissement")).not.toBeInTheDocument();
    expect(screen.queryByText(/Dernière étape/)).not.toBeInTheDocument();
  });

  it("keeps the backend message alongside empty run guidance", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([
      makeAnalysisRun({
        status: "empty",
        error_message: "Aucun verbatim exploitable apres import."
      })
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(
      await screen.findByText("Analyse terminée, aucun avis exploitable")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Aucun verbatim exploitable apres import.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Trustpilot a été interrogé, mais aucun avis exploitable n'a été récupéré pour cette analyse."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Cette analyse n'est pas en échec technique, mais elle ne contient pas assez de données exploitables pour afficher les KPI et irritants."
      )
    ).toBeInTheDocument();
  });

  it("surfaces the Première lecture priority and linked alert path for a completed report", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const completedRun = makeAnalysisRun({
      status: "completed",
      total_reviews: 12,
      execution_duration_seconds: 96
    });
    const rankOnePriority = makeBusinessInsights().priorities[0];
    const rankTwoPriority = {
      ...rankOnePriority,
      rank: 2,
      topic: "support",
      title: "Support de second rang",
      impact: "Le support apparait apres la livraison dans le classement API.",
      recommendation: "Relire les avis support apres le sujet livraison."
    };
    apiMocks.listRuns.mockResolvedValue([completedRun]);
    apiMocks.getSummary.mockResolvedValue(
      makeRunSummary({
        run: completedRun,
        business_insights: makeBusinessInsights({
          priorities: [rankTwoPriority, rankOnePriority]
        })
      })
    );
    apiMocks.getReviews.mockResolvedValue({
      run_id: completedRun.run_id,
      total: 1,
      limit: 30,
      offset: 0,
      reviews: [makeReview()]
    });
    apiMocks.getRunTrend.mockRejectedValue(new Error("Aucun run precedent"));
    apiMocks.listBusinessAlerts.mockResolvedValue([
      {
        ...businessAlert,
        run_id: completedRun.run_id,
        title: "Retards livraison critiques",
        severity: "critical"
      },
      {
        ...businessAlert,
        alert_id: 10,
        run_id: 999,
        title: "Alerte d'un autre run"
      }
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    const readoutHeading = await screen.findByRole("heading", {
      name: "Ce rapport est exploitable"
    });
    const readout = readoutHeading.closest(".completed-report-readout");
    expect(readout).not.toBeNull();
    const withinReadout = within(readout as HTMLElement);

    expect(withinReadout.getByText("Signal principal")).toBeInTheDocument();
    expect(withinReadout.getByText("Retards de livraison")).toBeInTheDocument();
    expect(
      withinReadout.getByText("Contacter le transporteur sur les commandes en retard")
    ).toBeInTheDocument();
    expect(
      withinReadout.getByText("Retards livraison critiques")
    ).toBeInTheDocument();
    expect(
      withinReadout.queryByText("Support de second rang")
    ).not.toBeInTheDocument();
    expect(
      withinReadout.queryByText("Alerte d'un autre run")
    ).not.toBeInTheDocument();
    expect(
      withinReadout.getByText("Alertes rattachées à cette analyse dans le cockpit : 1 alerte ouverte.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Avis analysés").length).toBeGreaterThan(0);
    expect(screen.getByText("10 verbatims")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Insights" }));
    expect(screen.getByText("Priorités recommandées")).toBeInTheDocument();
    expect(screen.queryByText("Portée limitée des KPI métier")).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Vue d’ensemble" }));
    await user.click(
      screen.getByRole("button", { name: "Ouvrir le cockpit" })
    );
    expect(
      await screen.findByRole("heading", { name: "Priorités opérationnelles" })
    ).toBeInTheDocument();
  });

  it("scopes sampled run KPIs to the collected corpus while keeping text analysis visible", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const warning =
      "Échantillon analytique équilibré par étoiles : les KPI de note et de distribution décrivent uniquement les avis collectés.";
    const completedRun = makeAnalysisRun({
      status: "completed",
      collection_mode: "sampled",
      stop_reason: "user_limit",
      total_reviews: 12,
      is_representative_for_business_kpis: false,
      business_kpi_warning: warning
    });
    apiMocks.listRuns.mockResolvedValue([completedRun]);
    apiMocks.getSummary.mockResolvedValue(
      makeRunSummary({ run: completedRun })
    );
    apiMocks.getReviews.mockResolvedValue({
      run_id: completedRun.run_id,
      total: 1,
      limit: 30,
      offset: 0,
      reviews: [makeReview()]
    });
    apiMocks.getRunTrend.mockRejectedValue(new Error("Aucun run precedent"));

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(await screen.findByText("Portée limitée des KPI métier")).toBeInTheDocument();
    expect(screen.getByText(warning)).toBeInTheDocument();
    expect(screen.getByText("Note moyenne du corpus")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Insights" }));
    expect(screen.getByText("Portée limitée des KPI métier")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Sentiment du corpus" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Irritants détectés" })
    ).toBeInTheDocument();
  });

  it("keeps a completed analysis selected across accessible report views", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const completedRun = makeAnalysisRun({ status: "completed", total_reviews: 3 });
    apiMocks.listRuns.mockResolvedValue([completedRun]);
    apiMocks.getSummary.mockResolvedValue(makeRunSummary({ run: completedRun }));
    apiMocks.getReviews.mockResolvedValue({
      run_id: completedRun.run_id,
      total: 1,
      limit: 30,
      offset: 0,
      reviews: [makeReview()]
    });

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    const overview = screen.getByRole("tab", { name: "Vue d’ensemble" });
    expect(overview).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("heading", { name: "Résumé métier" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Irritants détectés" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Journal d'exécution" })).not.toBeInTheDocument();

    overview.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "Insights" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByRole("heading", { name: "Irritants détectés" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Résumé métier" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Avis" }));
    expect(screen.getByRole("tab", { name: "Avis" })).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("La livraison est arrivee trop tard et sans information claire.")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Filtre sentiment" })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Exécution" }));
    expect(screen.getByRole("tab", { name: "Exécution" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "État de l'exécution" })).toBeInTheDocument();
    expect(screen.getByText(/Pages traitées/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Irritants détectés" })).not.toBeInTheDocument();

    await user.click(overview);
    expect(overview).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "Résumé métier" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /example\.com/i })).toBeInTheDocument();
  });

  it("keeps review rows compact while exposing full details and existing corrections", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const run = makeAnalysisRun({ status: "completed" });
    const longVerbatim = `Livraison en retard. ${"Le service client ne répond pas. ".repeat(20)}`;
    apiMocks.listRuns.mockResolvedValue([run]);
    apiMocks.getSummary.mockResolvedValue(makeRunSummary({ run }));
    apiMocks.getRunTrend.mockRejectedValue(new Error("Aucune analyse précédente"));
    apiMocks.getReviews.mockResolvedValue({
      run_id: run.run_id,
      total: 3,
      limit: 30,
      offset: 0,
      reviews: [
        makeReview({ review_id: 301, verbatim: longVerbatim, company_responded: true }),
        makeReview({ review_id: 302, rating: 5, sentiment_label: "Positif", corrected_label: "Négatif", verbatim: "Avis positif court." }),
        makeReview({ review_id: 303, rating: 3, sentiment_label: "Neutre", verbatim: "Avis neutre." })
      ]
    });
    apiMocks.saveReviewFeedback.mockImplementation(async (_runId: number, _reviewId: number, label: string) => ({
      corrected_label: label,
      comment: null,
      updated_at: "2026-08-28"
    }));
    apiMocks.deleteReviewFeedback.mockResolvedValue(undefined);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await user.click(screen.getByRole("tab", { name: "Avis" }));
    expect(await screen.findByText(/Livraison en retard\. Le service client/)).toBeInTheDocument();
    expect(screen.queryByText(longVerbatim)).not.toBeInTheDocument();
    expect(screen.getAllByRole("columnheader").map((header) => header.textContent)).toEqual([
      "Note", "Sentiment", "Avis", "Réponse", "Actions"
    ]);
    const firstRow = screen.getByRole("button", { name: "Voir le détail de l'avis nº 301" }).closest("tr") as HTMLElement;
    expect(within(firstRow).getByText("Répondu")).toBeInTheDocument();
    expect(within(firstRow).getByText("Non corrigé")).toBeInTheDocument();
    const openFirst = within(firstRow).getByRole("button", { name: "Voir le détail de l'avis nº 301" });
    expect(openFirst).toHaveAttribute("aria-expanded", "false");
    await user.click(openFirst);
    expect(screen.getByText(longVerbatim.trim())).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Texte de l'avis" })).toBeInTheDocument();
    expect(within(firstRow).getByRole("button", { name: "Masquer le détail de l'avis nº 301" })).toHaveAttribute("aria-expanded", "true");
    await user.click(within(firstRow).getByRole("button", { name: "Masquer le détail de l'avis nº 301" }));
    expect(screen.queryByText(longVerbatim)).not.toBeInTheDocument();

    const correctedRow = screen.getByRole("button", { name: "Voir le détail de l'avis nº 302" }).closest("tr") as HTMLElement;
    expect(within(correctedRow).getByText("Correction : Négatif")).toBeInTheDocument();
    expect(within(correctedRow).getByText("Sans réponse")).toBeInTheDocument();
    expect(within(correctedRow).getByText("5 / 5")).toBeInTheDocument();
    expect(screen.getByText("Avis neutre.")).toBeInTheDocument();
    await user.click(within(correctedRow).getByRole("button", { name: "Modifier la correction de l'avis nº 302" }));
    const detail = document.getElementById("review-detail-302") as HTMLElement;
    expect(within(detail).getByText("Sentiment corrigé : Négatif")).toBeInTheDocument();
    await user.click(within(detail).getByRole("button", { name: "Neutre" }));
    await waitFor(() => expect(apiMocks.saveReviewFeedback).toHaveBeenCalledWith(run.run_id, 302, "Neutre"));
    expect(await within(correctedRow).findByText("Correction : Neutre")).toBeInTheDocument();
    await user.click(within(detail).getByRole("button", { name: "Retirer la correction" }));
    await waitFor(() => expect(apiMocks.deleteReviewFeedback).toHaveBeenCalledWith(run.run_id, 302));
    expect(await within(correctedRow).findByText("Non corrigé")).toBeInTheDocument();
    await user.click(within(detail).getByRole("button", { name: "Positif" }));
    await waitFor(() => expect(apiMocks.saveReviewFeedback).toHaveBeenCalledWith(run.run_id, 302, "Positif"));
    expect(await within(correctedRow).findByText("Correction : Positif")).toBeInTheDocument();
    await user.click(within(detail).getByRole("button", { name: "Négatif" }));
    await waitFor(() => expect(apiMocks.saveReviewFeedback).toHaveBeenCalledWith(run.run_id, 302, "Négatif"));
    expect(await within(correctedRow).findByText("Correction : Négatif")).toBeInTheDocument();
  });

  it("closes review details on pagination, filtering and page-size changes", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const run = makeAnalysisRun({ status: "completed" });
    apiMocks.listRuns.mockResolvedValue([run]);
    apiMocks.getSummary.mockResolvedValue(makeRunSummary({ run }));
    apiMocks.getRunTrend.mockRejectedValue(new Error("Aucune analyse précédente"));
    apiMocks.getReviews.mockImplementation(async (_runId: number, filter: string, limit: number, offset: number) => ({
      run_id: run.run_id,
      total: filter === "Négatif" ? 0 : 31,
      limit,
      offset,
      reviews: filter === "Négatif" ? [] : [makeReview({ review_id: offset ? 302 : 301, verbatim: offset ? "Avis page deux." : "Avis page un." })]
    }));

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await user.click(screen.getByRole("tab", { name: "Avis" }));
    await user.click(await screen.findByRole("button", { name: "Voir le détail de l'avis nº 301" }));
    expect(within(document.getElementById("review-detail-301") as HTMLElement).getByText("Avis page un.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Suivant" }));
    expect(await screen.findByRole("button", { name: "Voir le détail de l'avis nº 302" })).toHaveAttribute("aria-expanded", "false");
    expect(document.getElementById("review-detail-301")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir le détail de l'avis nº 302" }));
    await user.click(within(screen.getByRole("group", { name: "Filtre sentiment" })).getByRole("button", { name: "Négatif" }));
    expect(await screen.findByText("Aucun avis pour ce filtre.")).toBeInTheDocument();
    expect(document.getElementById("review-detail-302")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tous" }));
    expect(await screen.findByRole("button", { name: "Voir le détail de l'avis nº 301" })).toHaveAttribute("aria-expanded", "false");
    await user.selectOptions(screen.getByLabelText("Par page"), "60");
    await waitFor(() => expect(apiMocks.getReviews).toHaveBeenCalledWith(run.run_id, "Tous", 60, 0));
  });

  it("keeps full review details available without correction actions in read-only mode", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(memberUser);
    const run = makeAnalysisRun({ status: "completed" });
    apiMocks.listRuns.mockResolvedValue([run]);
    apiMocks.getSummary.mockResolvedValue(makeRunSummary({ run }));
    apiMocks.getRunTrend.mockRejectedValue(new Error("Aucune analyse précédente"));
    apiMocks.getReviews.mockResolvedValue({
      run_id: run.run_id,
      total: 1,
      limit: 30,
      offset: 0,
      reviews: [makeReview({ corrected_label: "Positif", company_responded: true })]
    });

    render(<App />);
    expect(await screen.findByText(memberUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await user.click(screen.getByRole("tab", { name: "Avis" }));
    const open = await screen.findByRole("button", { name: "Voir le détail de l'avis nº 301" });
    expect(screen.queryByRole("button", { name: /Modifier la correction de l'avis/ })).not.toBeInTheDocument();
    await user.click(open);
    expect(screen.getByText("Sentiment corrigé : Positif")).toBeInTheDocument();
    expect(screen.getByText("Répondu", { selector: ".review-reply-status" })).toBeInTheDocument();
    expect(screen.getByText("Lecture seule")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retirer la correction" })).not.toBeInTheDocument();
  });

  it("explains unavailable insights while an analysis is pending", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listRuns.mockResolvedValue([makeAnalysisRun({ status: "pending" })]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    expect(await screen.findByText("Analyse en file d'attente")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Insights" }));
    expect(screen.getByText("Contenu indisponible pour cette analyse.")).toBeInTheDocument();
    expect(screen.queryByText("Avis analysés")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voir l'exécution" }));
    expect(screen.getByRole("tab", { name: "Exécution" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "État de l'exécution" })).toBeInTheDocument();
  });

  it("keeps Première lecture neutral without priority in a completed report", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const completedRun = makeAnalysisRun({
      status: "completed",
      total_reviews: 3
    });
    apiMocks.listRuns.mockResolvedValue([completedRun]);
    apiMocks.getSummary.mockResolvedValue(
      makeRunSummary({
        run: completedRun,
        top_topics: [],
        critical_reviews: [],
        rating_text_mismatches: [],
        business_insights: makeBusinessInsights({
          priorities: [],
          next_actions: [],
          strengths: [],
          watchpoints: []
        })
      })
    );
    apiMocks.getReviews.mockResolvedValue({
      run_id: completedRun.run_id,
      total: 1,
      limit: 30,
      offset: 0,
      reviews: [makeReview()]
    });
    apiMocks.getRunTrend.mockRejectedValue(new Error("Aucun run precedent"));
    apiMocks.listBusinessAlerts.mockResolvedValue([]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    const readoutHeading = await screen.findByRole("heading", {
      name: "Ce rapport est exploitable"
    });
    const readout = readoutHeading.closest(".completed-report-readout");
    expect(readout).not.toBeNull();
    const withinReadout = within(readout as HTMLElement);
    expect(withinReadout.getByText("Lecture du rapport")).toBeInTheDocument();
    expect(withinReadout.queryByText("Signal principal")).not.toBeInTheDocument();
    expect(
      withinReadout.getByText(
        "Lis les KPI, la synthèse et les avis disponibles pour confirmer ce qui mérite une action."
      )
    ).toBeInTheDocument();
    expect(
      withinReadout.queryByText(/signal classé prioritaire/i)
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Aucune alerte ouverte liée à cette analyse")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Aucune priorité critique détectée").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("tab", { name: "Insights" }));
    expect(
      screen.getByText("Aucune action suivante proposée pour ce rapport.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Aucun irritant détecté dans cette analyse. Consulte la synthèse et les avis analysés pour confirmer les signaux faibles."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Aucun avis critique détecté dans cette analyse.")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Aucun décalage note/texte détecté dans cette analyse.")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Avis" }));
    expect(screen.getByText("La livraison est arrivee trop tard et sans information claire.")).toBeInTheDocument();
  });

  it("lets an admin retry a failed analysis run", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const failedRun = makeAnalysisRun({
      status: "failed",
      error_message: "Timeout Trustpilot."
    });
    const runningRun = makeAnalysisRun({
      status: "running",
      error_message: null
    });
    apiMocks.listRuns
      .mockResolvedValueOnce([failedRun])
      .mockResolvedValueOnce([runningRun]);
    apiMocks.getRunEvents.mockResolvedValue([
      {
        event_id: 1,
        run_id: 21,
        level: "info",
        step: "queued",
        message: "Run planifie.",
        created_at: "2026-08-27T08:00:00Z"
      },
      {
        event_id: 2,
        run_id: 21,
        level: "error",
        step: "failed",
        message: "Timeout Trustpilot.",
        created_at: "2026-08-27T08:02:00Z"
      }
    ]);
    apiMocks.executeRun.mockResolvedValue(runningRun);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(await screen.findByText("Analyse échouée")).toBeInTheDocument();
    expect(
      screen.getByText(
        "L'analyse a bien été créée, mais l'exécution s'est arrêtée avant de produire un rapport."
      )
    ).toBeInTheDocument();
    expect(screen.getAllByText("Timeout Trustpilot.").length).toBeGreaterThan(0);
    await user.click(screen.getByRole("tab", { name: "Exécution" }));
    expect(screen.getByText("2 événements")).toBeInTheDocument();
    expect(screen.getByText("1 erreur")).toBeInTheDocument();
    expect(screen.getByText(/Dernière étape : Échec/)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Vue d’ensemble" }));
    await user.click(screen.getByRole("button", { name: "Relancer l'analyse" }));
    await waitFor(() => expect(apiMocks.executeRun).toHaveBeenCalledWith(21));
    expect(await screen.findByText("Analyse en cours")).toBeInTheDocument();
    expect(screen.getAllByText("En cours").length).toBeGreaterThan(0);
  });

  it("keeps failed analysis retry read-only for a member", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(memberUser);
    apiMocks.listRuns.mockResolvedValue([
      makeAnalysisRun({
        status: "failed",
        error_message: "Acces Trustpilot impossible."
      })
    ]);

    render(<App />);
    expect(await screen.findByText(memberUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await user.click(
      await screen.findByRole("button", { name: /example\.com.*Analyse nº 21/i })
    );

    expect(await screen.findByText("Analyse échouée")).toBeInTheDocument();
    expect(
      screen.getByText("Mode lecture seule : seul un administrateur peut relancer cette analyse.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Relancer l'analyse" })).toBeDisabled();
  });

  it("blocks analysis creation when the plan run limit is reached", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getOrganizationUsage.mockResolvedValue(freeLimitUsage);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));

    expect(screen.getByText("Limite d'analyses atteinte")).toBeInTheDocument();
    expect(screen.getByLabelText("Entreprise ou URL Trustpilot")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Lancer l'analyse" })).toBeDisabled();
  });

  it("creates an upgrade request from a plan gate", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getOrganizationUsage.mockResolvedValue(freeLimitUsage);
    apiMocks.createUpgradeRequest.mockResolvedValue({
      upgrade_request_id: 31,
      organization_id: 7,
      requested_plan: "pro",
      current_plan: "free",
      status: "pending",
      source: "analysis_limit",
      note: "Limite d'analyses atteinte",
      metadata: {},
      requested_by_email: "admin@example.test",
      created_at: null,
      updated_at: null,
      handled_at: null
    });

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Analyses/ }));
    await user.click(screen.getByRole("button", { name: "Passer au Pro" }));

    await waitFor(() =>
      expect(apiMocks.createUpgradeRequest).toHaveBeenCalledWith(
        expect.objectContaining({
          requested_plan: "pro",
          source: "analysis_limit"
        })
      )
    );
  });

  it("lets a member add a follow-up comment to a customer action", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(memberUser);
    apiMocks.listCustomerActions.mockResolvedValue([customerAction]);
    apiMocks.listCustomerActionTimeline
      .mockResolvedValueOnce(customerActionTimeline)
      .mockResolvedValueOnce([
        ...customerActionTimeline,
        {
          item_id: "comment-9",
          item_type: "comment",
          action_id: 4,
          organization_id: 7,
          audit_event_id: null,
          comment_id: 9,
          event_type: "customer_action.comment",
          actor_email: "member@example.test",
          author_user_id: 2,
          author_name: "Member Test",
          summary: "Note de suivi ajoutee.",
          body: "Verifier le suivi livraison.",
          metadata: {},
          created_at: "2026-08-27T11:00:00Z"
        }
      ]);

    render(<App />);
    expect(await screen.findByText(memberUser.email)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Accueil/ }));
    await user.click(await screen.findByRole("button", { name: /Suivi \(0\)/ }));
    await waitFor(() =>
      expect(apiMocks.listCustomerActionTimeline).toHaveBeenCalledWith(4)
    );
    expect(await screen.findByText("Action créée")).toBeInTheDocument();
    expect(screen.getByText("Action mise à jour")).toBeInTheDocument();
    expect(screen.getByText("Statut Résolue - Priorité Critique")).toBeInTheDocument();
    expect(
      screen.queryByText("Action client creee: Traiter les avis negatifs.")
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText("Transporteur contacte ce matin.")
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Modifier" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Démarrer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Résoudre" })).not.toBeInTheDocument();

    await user.type(
      screen.getByPlaceholderText("Ajouter une note de suivi..."),
      "Verifier le suivi livraison."
    );
    await user.click(screen.getByRole("button", { name: "Ajouter" }));

    await waitFor(() =>
      expect(apiMocks.createCustomerActionComment).toHaveBeenCalledWith(4, {
        body: "Verifier le suivi livraison."
      })
    );
    expect(
      await screen.findByText("Verifier le suivi livraison.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Verifier le suivi livraison.")).toHaveLength(1);
  });

  it("keeps a created customer action note visible when timeline reload fails", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(memberUser);
    apiMocks.listCustomerActions.mockResolvedValue([customerAction]);
    apiMocks.listCustomerActionTimeline
      .mockResolvedValueOnce(customerActionTimeline)
      .mockRejectedValueOnce(new Error("Suivi impossible a charger"));
    apiMocks.createCustomerActionComment.mockResolvedValue({
      ...customerActionComment,
      comment_id: 10,
      body: "Verifier le suivi livraison hors ligne.",
      created_at: "2026-08-27T10:00:00Z"
    });

    render(<App />);
    expect(await screen.findByText(memberUser.email)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Accueil/ }));
    await user.click(await screen.findByRole("button", { name: /Suivi \(0\)/ }));
    const textarea = screen.getByPlaceholderText("Ajouter une note de suivi...");
    await user.type(textarea, "Verifier le suivi livraison hors ligne.");
    await user.click(screen.getByRole("button", { name: "Ajouter" }));

    await waitFor(() =>
      expect(apiMocks.createCustomerActionComment).toHaveBeenCalledWith(4, {
        body: "Verifier le suivi livraison hors ligne."
      })
    );
    expect(
      await screen.findByText("Verifier le suivi livraison hors ligne.")
    ).toBeInTheDocument();
    expect(textarea).toHaveValue("");
  });

  it("creates a customer action from an alert", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.listBusinessAlerts.mockResolvedValue([businessAlert]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Accueil/ }));
    expect(
      await screen.findByText("Part d'avis negatifs a surveiller")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Créer une action" }));

    await waitFor(() =>
      expect(apiMocks.createCustomerAction).toHaveBeenCalledWith({ alert_id: 9 })
    );
  });

  it("validates the customer action workflow from alert to resolved impact", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const createdAction: CustomerAction = {
      ...customerAction,
      impact: notMeasurableImpact
    };
    const inProgressAction: CustomerAction = {
      ...createdAction,
      status: "in_progress",
      updated_by_email: "admin@example.test"
    };
    const criticalAction: CustomerAction = {
      ...inProgressAction,
      priority: "critical"
    };
    const resolvedAction: CustomerAction = {
      ...criticalAction,
      status: "resolved",
      resolved_at: "2026-08-27T12:00:00Z",
      impact: measuredImpact
    };
    const noteBody = "Controle transporteur planifie.";
    const noteItem: CustomerActionTimelineItem = {
      item_id: "comment-12",
      item_type: "comment",
      action_id: 4,
      organization_id: 7,
      audit_event_id: null,
      comment_id: 12,
      event_type: "customer_action.comment",
      actor_email: null,
      author_user_id: 1,
      author_name: "Admin Test",
      summary: "Note de suivi ajoutee.",
      body: noteBody,
      metadata: {},
      created_at: "2026-08-27T09:00:00Z"
    };
    const startedEvent: CustomerActionTimelineItem = {
      ...customerActionTimeline[2],
      item_id: "audit-31",
      audit_event_id: 31,
      metadata: { status: "in_progress", priority: "high" },
      created_at: "2026-08-27T10:00:00Z"
    };
    const priorityEvent: CustomerActionTimelineItem = {
      ...customerActionTimeline[2],
      item_id: "audit-32",
      audit_event_id: 32,
      metadata: { status: "in_progress", priority: "critical" },
      created_at: "2026-08-27T11:00:00Z"
    };
    const resolvedEvent: CustomerActionTimelineItem = {
      ...customerActionTimeline[2],
      item_id: "audit-33",
      audit_event_id: 33,
      metadata: { status: "resolved", priority: "critical" },
      created_at: "2026-08-27T12:00:00Z"
    };
    const createdTimeline = [customerActionTimeline[0]];
    const timelineWithNote = [...createdTimeline, noteItem];
    const timelineStarted = [...timelineWithNote, startedEvent];
    const timelinePriority = [...timelineStarted, priorityEvent];
    const timelineResolved = [...timelinePriority, resolvedEvent];

    apiMocks.listBusinessAlerts.mockResolvedValue([businessAlert]);
    apiMocks.listCustomerActions
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([createdAction])
      .mockRejectedValueOnce(new Error("Liste actions indisponible"))
      .mockResolvedValueOnce([criticalAction])
      .mockResolvedValueOnce([resolvedAction]);
    apiMocks.createCustomerAction.mockResolvedValue(createdAction);
    apiMocks.createCustomerActionComment.mockResolvedValue({
      ...customerActionComment,
      comment_id: 12,
      author_user_id: 1,
      author_name: "Admin Test",
      body: noteBody,
      created_at: "2026-08-27T09:00:00Z"
    });
    apiMocks.updateCustomerAction
      .mockResolvedValueOnce(inProgressAction)
      .mockResolvedValueOnce(criticalAction)
      .mockResolvedValueOnce(resolvedAction);
    apiMocks.listCustomerActionTimeline
      .mockResolvedValueOnce(createdTimeline)
      .mockResolvedValueOnce(timelineWithNote)
      .mockResolvedValueOnce(timelineStarted)
      .mockResolvedValueOnce(timelinePriority)
      .mockResolvedValueOnce(timelineResolved);

    async function actionCard() {
      const title = await screen.findByText("Traiter les avis negatifs");
      const card = title.closest("article");
      expect(card).not.toBeNull();
      return within(card as HTMLElement);
    }

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Accueil/ }));
    expect(
      await screen.findByText("Part d'avis negatifs a surveiller")
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Créer une action" }));
    await waitFor(() =>
      expect(apiMocks.createCustomerAction).toHaveBeenCalledWith({ alert_id: 9 })
    );

    let currentAction = await actionCard();
    expect(currentAction.getByText("A mesurer")).toBeInTheDocument();
    expect(
      currentAction.getByText(
        "Relance une analyse de la meme entreprise pour mesurer l'impact."
      )
    ).toBeInTheDocument();

    await user.click(currentAction.getByRole("button", { name: /Suivi/ }));
    await waitFor(() =>
      expect(apiMocks.listCustomerActionTimeline).toHaveBeenCalledWith(4)
    );
    expect(await screen.findByText("Action créée")).toBeInTheDocument();

    currentAction = await actionCard();
    await user.type(
      currentAction.getByPlaceholderText("Ajouter une note de suivi..."),
      noteBody
    );
    await user.click(currentAction.getByRole("button", { name: "Ajouter" }));
    await waitFor(() =>
      expect(apiMocks.createCustomerActionComment).toHaveBeenCalledWith(4, {
        body: noteBody
      })
    );
    expect(await screen.findByText(noteBody)).toBeInTheDocument();
    expect(screen.getAllByText(noteBody)).toHaveLength(1);

    currentAction = await actionCard();
    await user.click(currentAction.getByRole("button", { name: "Démarrer" }));
    await waitFor(() =>
      expect(apiMocks.updateCustomerAction).toHaveBeenCalledWith(4, {
        status: "in_progress"
      })
    );
    expect((await actionCard()).getByText("En cours")).toBeInTheDocument();
    expect(
      await screen.findByText("Statut En cours - Priorité Haute")
    ).toBeInTheDocument();
    expect(screen.queryByText(/Action impossible/)).not.toBeInTheDocument();

    currentAction = await actionCard();
    await user.click(currentAction.getByRole("button", { name: "Modifier" }));
    await user.selectOptions(currentAction.getByLabelText("Priorité"), "critical");
    await user.click(currentAction.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() =>
      expect(apiMocks.updateCustomerAction).toHaveBeenLastCalledWith(
        4,
        expect.objectContaining({ priority: "critical" })
      )
    );
    expect((await actionCard()).getByText("Critique")).toBeInTheDocument();
    expect(
      await screen.findByText("Statut En cours - Priorité Critique")
    ).toBeInTheDocument();

    currentAction = await actionCard();
    await user.click(currentAction.getByRole("button", { name: "Résoudre" }));
    await waitFor(() =>
      expect(apiMocks.updateCustomerAction).toHaveBeenLastCalledWith(4, {
        status: "resolved"
      })
    );
    await user.click(screen.getByRole("button", { name: "Résolues" }));

    currentAction = await actionCard();
    expect(currentAction.getByText("Résolue")).toBeInTheDocument();
    expect(currentAction.getByText("Amelioration")).toBeInTheDocument();
    expect(currentAction.getByText("Analyse nº 21 → Analyse nº 24")).toBeInTheDocument();
    expect(
      currentAction.getByText(/42,0 pts.*31,0 pts.*-11,0 pts/)
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Statut Résolue - Priorité Critique")
    ).toBeInTheDocument();
    expect(screen.getAllByText(noteBody)).toHaveLength(1);
  });

  it("organizes active customer actions into exclusive triage sections", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const dueSoonDate = new Date(Date.now() + 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);
    const laterDate = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);
    const actions: CustomerAction[] = [
      {
        ...customerAction,
        action_id: 51,
        title: "Retard basse priorite",
        priority: "low",
        owner_name: "Support",
        due_date: "2000-01-01",
        updated_at: "2026-08-20T08:00:00Z"
      },
      {
        ...customerAction,
        action_id: 52,
        title: "Critique recente",
        priority: "critical",
        owner_name: "Qualite",
        due_date: null,
        updated_at: "2026-08-27T08:00:00Z"
      },
      {
        ...customerAction,
        action_id: 53,
        title: "Action en cours non urgente",
        status: "in_progress",
        priority: "medium",
        owner_name: "SAV",
        due_date: laterDate
      },
      {
        ...customerAction,
        action_id: 54,
        title: "Action a planifier",
        priority: "medium",
        owner_name: null,
        due_date: null,
        alert_title: "Retours livraison repetes"
      },
      {
        ...customerAction,
        action_id: 55,
        title: "Echeance proche moyenne",
        priority: "medium",
        owner_name: "Operations",
        due_date: dueSoonDate
      },
      {
        ...customerAction,
        action_id: 56,
        title: "Critique ancienne",
        priority: "critical",
        owner_name: "Qualite",
        due_date: null,
        updated_at: "2026-08-26T08:00:00Z"
      },
      {
        ...customerAction,
        action_id: 57,
        title: "Retard critique",
        priority: "critical",
        owner_name: "Support",
        due_date: "2000-01-05",
        updated_at: "2026-08-19T08:00:00Z"
      }
    ];
    apiMocks.listCustomerActions.mockResolvedValue(actions);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Accueil/ }));

    const nowSection = await screen.findByRole("region", {
      name: "À traiter maintenant"
    });
    const followSection = screen.getByRole("region", { name: "À suivre" });
    const planSection = screen.getByRole("region", { name: "À planifier" });

    expect(within(nowSection).getByText("Retard critique")).toBeInTheDocument();
    expect(
      within(followSection).getByText("Action en cours non urgente")
    ).toBeInTheDocument();
    expect(within(planSection).getByText("Action a planifier")).toBeInTheDocument();

    const nowTitles = Array.from(
      nowSection.querySelectorAll(".customer-action-card-header strong")
    ).map((element) => element.textContent);
    expect(nowTitles).toEqual([
      "Retard critique",
      "Retard basse priorite",
      "Echeance proche moyenne",
      "Critique recente",
      "Critique ancienne"
    ]);

    for (const action of actions) {
      expect(screen.getAllByText(action.title)).toHaveLength(1);
    }
    expect(within(planSection).getByText("Sans responsable")).toBeInTheDocument();
    expect(within(planSection).getByText("Aucune échéance")).toBeInTheDocument();
    expect(
      within(planSection).getByText("Alerte : Retours livraison repetes")
    ).toBeInTheDocument();

    const planCard = within(planSection)
      .getByText("Action a planifier")
      .closest(".customer-action-card") as HTMLElement;
    expect(within(planCard).getByRole("button", { name: /Suivi/ })).toBeEnabled();
    expect(within(planCard).getByRole("button", { name: "Modifier" })).toBeEnabled();
    expect(within(planCard).getByRole("button", { name: "Démarrer" })).toBeEnabled();
    expect(within(planCard).getByRole("button", { name: "Résoudre" })).toBeEnabled();
  });

  it("surfaces overdue and due-soon customer actions", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    const dueSoonDate = new Date(Date.now() + 24 * 60 * 60 * 1000)
      .toISOString()
      .slice(0, 10);

    apiMocks.listCustomerActions.mockResolvedValue([
      {
        ...customerAction,
        action_id: 41,
        title: "Relancer le transporteur",
        status: "in_progress",
        due_date: "2000-01-01"
      },
      {
        ...customerAction,
        action_id: 42,
        title: "Verifier la promesse SAV",
        due_date: dueSoonDate
      }
    ]);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Accueil/ }));

    expect(await screen.findByText(/1 en retard, 1 à relancer/)).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: "À traiter maintenant" })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "En retard" }));
    expect(
      screen.queryByRole("region", { name: "À traiter maintenant" })
    ).not.toBeInTheDocument();
    expect(screen.getByText("Relancer le transporteur")).toBeInTheDocument();
    expect(screen.queryByText("Verifier la promesse SAV")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Échéance proche" }));
    expect(screen.getByText("Verifier la promesse SAV")).toBeInTheDocument();
    expect(screen.queryByText("Relancer le transporteur")).not.toBeInTheDocument();
    expect(screen.getByText("À relancer")).toBeInTheDocument();
  });

  it("shows an upgrade gate for model training outside Business", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getOrganizationUsage.mockResolvedValue(proUsage);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Qualité IA/ }));

    expect(
      screen.getByText("Réentraînement IA réservé au plan Business")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Réentraîner" })).toBeDisabled();
  });

  it("labels the human correction metric without implying a model error rate", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getFeedbackQuality.mockResolvedValue({
      ...feedbackQuality,
      total_corrections: 42,
      changed_label_count: 41,
      apparent_error_rate: 41 / 42
    });

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Qualité IA/ }));

    expect(screen.getByText("Corrections ayant changé le sentiment")).toBeInTheDocument();
    expect(screen.getByText("Parmi les corrections humaines")).toBeInTheDocument();
    expect(screen.queryByText("Erreur apparente")).not.toBeInTheDocument();
  });

  it("shows an unavailable state instead of zero quality KPIs when the request fails", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getFeedbackQuality.mockRejectedValue(new Error("Service momentanément indisponible"));

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Qualité IA/ }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Qualité IA indisponible : Service momentanément indisponible"
    );
    expect(screen.queryByText("Corrections ayant changé le sentiment")).not.toBeInTheDocument();
    expect(
      within(screen.getByRole("button", { name: /Qualité IA/ })).getByText("—")
    ).toBeInTheDocument();
  });

  it("groups available correction KPIs and recent changes without implying model error", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getFeedbackQuality.mockResolvedValue({
      ...feedbackQuality,
      total_corrections: 2,
      changed_label_count: 1,
      confirmed_label_count: 1,
      apparent_error_rate: 0.5,
      training_ready_count: 2,
      corrected_company_count: 1,
      by_company: [{ company_id: 3, company_name: "example.com", correction_count: 2, changed_label_count: 1, run_count: 1 }],
      corrected_label_distribution: [{ label: "Positif", count: 1 }],
      transitions: [{ predicted_label: "Négatif", corrected_label: "Positif", count: 1 }],
      recent_corrections: [{
        feedback_id: 9,
        review_id: 301,
        run_id: 21,
        company_name: "example.com",
        rating: 1,
        predicted_label: "Négatif",
        corrected_label: "Positif",
        feedback_comment: null,
        feedback_updated_at: null,
        verbatim: "Correction de démonstration"
      }]
    });

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Qualité IA/ }));

    expect(screen.getByRole("heading", { name: "Indicateurs de correction" })).toBeInTheDocument();
    expect(screen.getByText("Parmi les corrections humaines")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Détail des corrections" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dernières corrections" })).toBeInTheDocument();
    expect(screen.getByText("Analyse nº 21")).toBeInTheDocument();
    expect(screen.getByText("Correction de démonstration")).toBeInTheDocument();
    expect(screen.getByText("Aucun entraînement lancé depuis l'interface pour le moment.")).toBeInTheDocument();
  });

  it("separates empty correction data from unavailable training data", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getModelTrainingOverview.mockRejectedValue(new Error("Training unavailable"));

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Qualité IA/ }));

    expect(screen.getByText("Aucune correction humaine enregistrée pour le moment.")).toBeInTheDocument();
    expect(screen.getByText("Historique des entraînements indisponible.")).toBeInTheDocument();
    expect(screen.queryByText("Aucun entraînement lancé depuis l'interface pour le moment.")).not.toBeInTheDocument();
  });

  it("groups administration without changing member invitation", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.inviteOrganizationUser.mockResolvedValue({ email: "invite@example.test", invitation_accept_url: null });

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Administration/ }));

    for (const section of ["Organisation", "Membres", "Plan et usage", "Activité"]) {
      expect(screen.getByRole("region", { name: section })).toBeInTheDocument();
    }
    expect(screen.getByText("Plan actif et quotas")).toBeInTheDocument();
    expect(screen.getByText("Aucune activité d'administration enregistrée pour le moment.")).toBeInTheDocument();
    expect(screen.getByText("Aucune demande ouverte.")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Membres" })).getByText(adminUser.email)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Adresse e-mail"), "invite@example.test");
    await user.type(screen.getByLabelText("Nom complet"), "Invité Test");
    await user.click(screen.getByRole("button", { name: "Inviter" }));
    expect(apiMocks.inviteOrganizationUser).toHaveBeenCalledWith({
      email: "invite@example.test",
      full_name: "Invité Test",
      role: "member"
    });
  });
});
