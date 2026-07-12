import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type {
  ActionCenter,
  AuthToken,
  CurrentUser,
  FeedbackQuality,
  ModelTrainingOverview,
  OrganizationSettings,
  ReviewSource
} from "./types";

const apiMocks = vi.hoisted(() => ({
  acceptOrganizationInvitation: vi.fn(),
  clearAuthToken: vi.fn(),
  compareRuns: vi.fn(),
  createModelTrainingRun: vi.fn(),
  createRun: vi.fn(),
  deleteReviewFeedback: vi.fn(),
  executeRun: vi.fn(),
  exportFeedback: vi.fn(),
  exportReviews: vi.fn(),
  getCurrentUser: vi.fn(),
  getFeedbackQuality: vi.fn(),
  getModelTrainingOverview: vi.fn(),
  getOrganizationActionCenter: vi.fn(),
  getOrganizationSettings: vi.fn(),
  getReviews: vi.fn(),
  getRunEvents: vi.fn(),
  getRunTrend: vi.fn(),
  getSummary: vi.fn(),
  hasAuthToken: vi.fn(),
  inviteOrganizationUser: vi.fn(),
  listBusinessAlerts: vi.fn(),
  listOrganizationAuditEvents: vi.fn(),
  listOrganizationUsers: vi.fn(),
  listReviewSources: vi.fn(),
  listRuns: vi.fn(),
  login: vi.fn(),
  previewCsvFile: vi.fn(),
  refreshRunBusinessAlerts: vi.fn(),
  saveReviewFeedback: vi.fn(),
  updateBusinessAlertStatus: vi.fn(),
  updateOrganizationSettings: vi.fn(),
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
  apiMocks.getOrganizationActionCenter.mockResolvedValue(actionCenter);
  apiMocks.listOrganizationUsers.mockResolvedValue([]);
  apiMocks.getOrganizationSettings.mockResolvedValue(organizationSettings);
  apiMocks.listOrganizationAuditEvents.mockResolvedValue([]);
  apiMocks.listReviewSources.mockResolvedValue(reviewSources);
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
});
