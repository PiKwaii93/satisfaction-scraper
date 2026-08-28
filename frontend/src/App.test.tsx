import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type {
  ActionCenter,
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
  ReviewSource
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
  apiMocks.hasAuthToken.mockReturnValue(false);
  apiMocks.listRuns.mockResolvedValue([]);
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
        name: "Acceder a ton espace entreprise"
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
      screen.getByText(/Mode lecture seule: demande a un administrateur/)
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Entreprise ou URL Trustpilot")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Lancer l'analyse" })).toBeDisabled();
  });

  it("lets an admin launch a Trustpilot analysis", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.createRun.mockResolvedValue({
      run_id: 21,
      company_id: 4,
      company_name: "example.com",
      trustpilot_slug: "example.com",
      source: "trustpilot",
      status: "pending",
      pages_per_star: 1,
      stars_requested: [1, 2, 3, 4, 5],
      total_reviews: 0,
      celery_task_id: null,
      created_at: null,
      started_at: null,
      finished_at: null,
      execution_duration_seconds: null,
      error_message: null
    });

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
    await screen.findByText("Controle avant import");
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
    expect(screen.getByText("Statut Resolue - Priorite Critique")).toBeInTheDocument();
    expect(
      screen.queryByText("Action client creee: Traiter les avis negatifs.")
    ).not.toBeInTheDocument();
    expect(
      await screen.findByText("Transporteur contacte ce matin.")
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Modifier" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Demarrer" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Resoudre" })).not.toBeInTheDocument();

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
    await user.click(screen.getByRole("button", { name: "Creer action" }));

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

    await user.click(screen.getByRole("button", { name: "Creer action" }));
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
    await user.click(currentAction.getByRole("button", { name: "Demarrer" }));
    await waitFor(() =>
      expect(apiMocks.updateCustomerAction).toHaveBeenCalledWith(4, {
        status: "in_progress"
      })
    );
    expect((await actionCard()).getByText("En cours")).toBeInTheDocument();
    expect(
      await screen.findByText("Statut En cours - Priorite Haute")
    ).toBeInTheDocument();
    expect(screen.queryByText(/Action impossible/)).not.toBeInTheDocument();

    currentAction = await actionCard();
    await user.click(currentAction.getByRole("button", { name: "Modifier" }));
    await user.selectOptions(currentAction.getByLabelText("Priorite"), "critical");
    await user.click(currentAction.getByRole("button", { name: "Enregistrer" }));
    await waitFor(() =>
      expect(apiMocks.updateCustomerAction).toHaveBeenLastCalledWith(
        4,
        expect.objectContaining({ priority: "critical" })
      )
    );
    expect((await actionCard()).getByText("Critique")).toBeInTheDocument();
    expect(
      await screen.findByText("Statut En cours - Priorite Critique")
    ).toBeInTheDocument();

    currentAction = await actionCard();
    await user.click(currentAction.getByRole("button", { name: "Resoudre" }));
    await waitFor(() =>
      expect(apiMocks.updateCustomerAction).toHaveBeenLastCalledWith(4, {
        status: "resolved"
      })
    );
    await user.click(screen.getByRole("button", { name: "Resolues" }));

    currentAction = await actionCard();
    expect(currentAction.getByText("Resolue")).toBeInTheDocument();
    expect(currentAction.getByText("Amelioration")).toBeInTheDocument();
    expect(currentAction.getByText("Run #21 -> Run #24")).toBeInTheDocument();
    expect(
      currentAction.getByText(/42,0 pts.*31,0 pts.*-11,0 pts/)
    ).toBeInTheDocument();
    expect(
      await screen.findByText("Statut Resolue - Priorite Critique")
    ).toBeInTheDocument();
    expect(screen.getAllByText(noteBody)).toHaveLength(1);
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

    expect(await screen.findByText(/1 en retard, 1 a relancer/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "En retard" }));
    expect(screen.getByText("Relancer le transporteur")).toBeInTheDocument();
    expect(screen.queryByText("Verifier la promesse SAV")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Echeance proche" }));
    expect(screen.getByText("Verifier la promesse SAV")).toBeInTheDocument();
    expect(screen.queryByText("Relancer le transporteur")).not.toBeInTheDocument();
    expect(screen.getByText("A relancer")).toBeInTheDocument();
  });

  it("shows an upgrade gate for model training outside Business", async () => {
    const user = userEvent.setup();
    configureAuthenticatedSession(adminUser);
    apiMocks.getOrganizationUsage.mockResolvedValue(proUsage);

    render(<App />);
    expect(await screen.findByText(adminUser.email)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Qualite IA/ }));

    expect(
      screen.getByText("Reentrainement IA reserve au plan Business")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reentrainer" })).toBeDisabled();
  });
});
