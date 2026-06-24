import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Building2,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Download,
  FileText,
  Hourglass,
  ListChecks,
  Loader2,
  LogOut,
  Play,
  RefreshCw,
  Search,
  TableProperties,
  Users,
  UserPlus
} from "lucide-react";
import {
  compareRuns,
  acceptOrganizationInvitation,
  createModelTrainingRun,
  createRun,
  clearAuthToken,
  deleteReviewFeedback,
  executeRun,
  exportFeedback,
  exportReviews,
  getCurrentUser,
  getFeedbackQuality,
  getModelTrainingOverview,
  getReviews,
  getRunEvents,
  getRunTrend,
  getSummary,
  hasAuthToken,
  inviteOrganizationUser,
  listOrganizationUsers,
  listReviewSources,
  listRuns,
  login,
  previewCsvFile,
  saveReviewFeedback,
  uploadCsvRun
} from "./api";
import type {
  AnalysisRunEvent,
  AnalysisRun,
  AnalysisRunTrend,
  AnalysisSource,
  BenchmarkCompany,
  BusinessInsights,
  BusinessPriority,
  BusinessStrength,
  BusinessWatchpoint,
  CurrentUser,
  CsvColumnMapping,
  CsvImportPreview,
  DistributionRow,
  FeedbackQuality,
  ModelTrainingOverview,
  ModelTrainingRun,
  OrganizationUser,
  Review,
  ReviewSource,
  RunsComparison,
  RunSummary,
  SentimentLabel,
  SummaryReview,
  UserRole
} from "./types";

const SENTIMENTS: Array<SentimentLabel | "Tous"> = [
  "Tous",
  "Négatif",
  "Neutre",
  "Positif"
];

const FEEDBACK_SENTIMENTS = SENTIMENTS.filter(
  (sentiment): sentiment is SentimentLabel => sentiment !== "Tous"
);

const REVIEW_PAGE_SIZES = [30, 60, 120, 500];
const SOURCE_LABELS: Record<AnalysisSource, string> = {
  trustpilot: "Trustpilot",
  csv: "CSV"
};

const DEFAULT_REVIEW_SOURCES: ReviewSource[] = [
  {
    source_id: "trustpilot",
    label: "Trustpilot",
    status: "active",
    category: "web public",
    description: "Avis publics Trustpilot par entreprise et par note.",
    primary_action: "Coller une URL ou un domaine",
    setup_hint: "Disponible sans configuration.",
    supports_analysis: true,
    is_configured: true,
    required_fields: ["URL ou domaine Trustpilot"],
    optional_fields: ["Pages par note"],
    column_aliases: {}
  },
  {
    source_id: "csv",
    label: "CSV",
    status: "active",
    category: "import fichier",
    description: "Exports clients, SAV, enquete ou autres plateformes.",
    primary_action: "Importer un fichier CSV",
    setup_hint: "Mapping des colonnes avant import.",
    supports_analysis: true,
    is_configured: true,
    required_fields: ["verbatim"],
    optional_fields: ["rating", "author", "date", "company_responded"],
    column_aliases: {}
  }
];

const CSV_MAPPING_FIELDS: Array<{
  key: keyof CsvColumnMapping;
  label: string;
  required?: boolean;
}> = [
  { key: "verbatim", label: "Texte", required: true },
  { key: "rating", label: "Note" },
  { key: "author", label: "Auteur" },
  { key: "date", label: "Date" },
  { key: "company_responded", label: "Reponse entreprise" }
];

const sentimentClass: Record<SentimentLabel, string> = {
  Négatif: "negative",
  Neutre: "neutral",
  Positif: "positive"
};

function formatDate(value: string | null) {
  if (!value) return "Non disponible";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "0";
  }
  return value.toLocaleString("fr-FR", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits
  });
}

function compactText(value: string | null | undefined, maxLength = 230) {
  const text = (value ?? "").trim();
  if (!text) return "Avis sans verbatim";
  return text.length > maxLength ? `${text.slice(0, maxLength)}...` : text;
}

function formatReviewRange(offset: number, displayedCount: number, total: number) {
  if (total <= 0) {
    return "0 avis";
  }

  if (displayedCount <= 0) {
    return `0 sur ${total} avis`;
  }

  const firstReview = offset + 1;
  const lastReview = Math.min(offset + displayedCount, total);
  return `${firstReview}-${lastReview} sur ${total} avis`;
}

function validateCompanyInput(value: string) {
  const trimmedValue = value.trim();
  const normalizedValue = trimmedValue.toLowerCase();
  if (trimmedValue.length < 2) {
    return "Renseigne une entreprise ou une URL Trustpilot.";
  }

  if (
    normalizedValue.includes("trustpilot.") &&
    !normalizedValue.includes("/review/")
  ) {
    return "L'URL Trustpilot doit contenir /review/, par exemple https://fr.trustpilot.com/review/www.darty.com.";
  }

  return null;
}

function isAnalysisSource(sourceId: string): sourceId is AnalysisSource {
  return sourceId === "trustpilot" || sourceId === "csv";
}

function sourceIcon(sourceId: string) {
  if (sourceId === "trustpilot") {
    return <Search aria-hidden="true" size={18} />;
  }

  if (sourceId === "csv") {
    return <FileText aria-hidden="true" size={18} />;
  }

  return <ListChecks aria-hidden="true" size={18} />;
}

function formatDuration(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined) {
    return null;
  }

  if (seconds < 60) {
    return `${seconds} s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return remainingSeconds > 0
    ? `${minutes} min ${remainingSeconds} s`
    : `${minutes} min`;
}

function formatTopic(value: string | null | undefined) {
  const normalizedValue = value?.replaceAll("_", " ").trim().toLowerCase();
  if (!normalizedValue) return "Sujet";

  const labels: Record<string, string> = {
    commande: "Commande",
    delai: "Délai",
    livraison: "Livraison",
    prix: "Prix",
    produit: "Produit",
    "qualite produit": "Qualité produit",
    remboursement: "Remboursement",
    retour: "Retour",
    sav: "SAV",
    "service client": "Service client",
    "site app": "Site/app"
  };

  return labels[normalizedValue] ?? `${normalizedValue[0].toUpperCase()}${normalizedValue.slice(1)}`;
}

function getDistributionCount<T extends string | number>(
  rows: DistributionRow<T>[],
  key: T
) {
  const row = rows.find((item) => item.label === key || item.rating === key);
  return row?.count ?? 0;
}

function escapeHtml(value: string | number | null | undefined) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPercent(value: number | null | undefined) {
  return `${formatNumber(value, 1)} %`;
}

function formatSignedNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, digits)}`;
}

function formatMetricValue(value: number | null | undefined, unit: string | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  if (unit === "/5") {
    return `${formatNumber(value)} / 5`;
  }
  if (unit === "/100") {
    return `${formatNumber(value, 0)} / 100`;
  }
  if (unit === "score") {
    return formatNumber(value, 2);
  }
  return `${formatNumber(value, 0)}${unit ? ` ${unit}` : ""}`;
}

function sentimentTrendTone(row: AnalysisRunTrend["sentiment"][number]) {
  const label = row.label
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();

  if (row.direction === "flat") {
    return "flat";
  }
  if (label.includes("negatif")) {
    return row.direction === "down" ? "positive" : "negative";
  }
  if (label.includes("positif")) {
    return row.direction === "up" ? "positive" : "negative";
  }
  return row.direction;
}

function reportFileName(run: AnalysisRun) {
  const slug = run.company_name.replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  return `rapport_${slug || "analyse"}_run_${run.run_id}.pdf`;
}

function benchmarkReportFileName(comparison: RunsComparison) {
  const runSlug = comparison.run_ids.join("_");
  return `rapport_benchmark_runs_${runSlug || "selection"}.pdf`;
}

function distributionRows<T extends string | number>(
  rows: DistributionRow<T>[],
  items: Array<{ label: string; key: T }>
) {
  return items
    .map((item) => {
      const count = getDistributionCount(rows, item.key);
      return `<tr><td>${escapeHtml(item.label)}</td><td>${count}</td></tr>`;
    })
    .join("");
}

function reviewExcerpt(review: SummaryReview) {
  return `
    <article class="review">
      <div class="review-meta">
        <strong>#${escapeHtml(review.review_id)}</strong>
        <span>${escapeHtml(review.rating ?? "-")} / 5</span>
        <span>${escapeHtml(review.sentiment_label)}</span>
        <span>Score ${formatNumber(review.sentiment_score, 2)}</span>
      </div>
      <p>${escapeHtml(compactText(review.verbatim, 360))}</p>
    </article>
  `;
}

function buildPrintableReport(run: AnalysisRun, summary: RunSummary) {
  const insights = summary.business_insights;
  const createdAt = new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "long",
    timeStyle: "short"
  }).format(new Date());

  const priorities = insights.priorities
    .slice(0, 4)
    .map(
      (priority) => `
        <article class="priority">
          <div class="priority-heading">
            <strong>#${priority.rank} ${escapeHtml(priority.title)}</strong>
            <span>${escapeHtml(formatSeverity(priority.severity))}</span>
          </div>
          <p>${escapeHtml(priority.impact)}</p>
          <p><strong>Action recommandée :</strong> ${escapeHtml(priority.recommendation)}</p>
          <p class="meta">${priority.negative_reviews} avis négatifs - ${formatPercent(priority.share_of_reviews)} du corpus</p>
        </article>
      `
    )
    .join("");

  const strengths = insights.strengths
    .slice(0, 3)
    .map(
      (strength) => `
        <li>
          <strong>${escapeHtml(strength.title)}</strong>
          <span>${strength.positive_reviews} avis positifs</span>
        </li>
      `
    )
    .join("");

  const watchpoints = insights.watchpoints
    .map(
      (watchpoint) => `
        <li>
          <strong>${escapeHtml(watchpoint.title)}</strong>
          <span>${escapeHtml(watchpoint.message)}</span>
        </li>
      `
    )
    .join("");

  const actions = insights.next_actions
    .map((action) => `<li>${escapeHtml(action)}</li>`)
    .join("");

  const topics = summary.top_topics
    .slice(0, 8)
    .map(
      (topic) => `
        <tr>
          <td>${escapeHtml(formatTopic(topic.topic))}</td>
          <td>${topic.count}</td>
        </tr>
      `
    )
    .join("");

  const criticalReviews = summary.critical_reviews
    .slice(0, 5)
    .map(reviewExcerpt)
    .join("");

  const mismatches = summary.rating_text_mismatches
    .slice(0, 3)
    .map(reviewExcerpt)
    .join("");

  return `<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Rapport ${escapeHtml(run.company_name)} - Run #${run.run_id}</title>
  <style>
    :root {
      color: #18202c;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }
    body {
      margin: 0;
      background: #eef1f4;
    }
    .page {
      max-width: 1120px;
      margin: 0 auto;
      padding: 34px;
      background: #ffffff;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      border-bottom: 3px solid #18202c;
      padding-bottom: 18px;
      margin-bottom: 22px;
    }
    h1, h2, h3, p {
      margin-top: 0;
    }
    h1 {
      font-size: 30px;
      margin-bottom: 8px;
    }
    h2 {
      font-size: 18px;
      margin-bottom: 12px;
      color: #1d4ed8;
    }
    .eyebrow {
      color: #2563eb;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .score {
      min-width: 132px;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 12px;
      text-align: center;
    }
    .score strong {
      display: block;
      font-size: 36px;
      line-height: 1;
      margin: 5px 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin: 18px 0;
    }
    .kpi, .box, .priority, .review {
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 12px;
      break-inside: avoid;
    }
    .kpi span, .meta {
      color: #667085;
      font-size: 12px;
    }
    .kpi strong {
      display: block;
      margin-top: 5px;
      font-size: 22px;
    }
    section {
      margin-top: 24px;
      break-inside: avoid;
    }
    .two-cols {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    .priority-list {
      display: grid;
      gap: 10px;
    }
    .priority-heading, .review-meta {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .priority-heading span {
      color: #b42318;
      font-weight: 800;
    }
    ul, ol {
      margin: 0;
      padding-left: 20px;
    }
    li {
      margin-bottom: 8px;
    }
    li span {
      display: block;
      color: #667085;
      font-size: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    td, th {
      border-bottom: 1px solid #d9dee7;
      padding: 7px 5px;
      text-align: left;
    }
    th {
      color: #475467;
      font-size: 12px;
      text-transform: uppercase;
    }
    .review-list {
      display: grid;
      gap: 10px;
    }
    .review p {
      margin-bottom: 0;
      color: #344054;
    }
    .limits {
      color: #475467;
      font-size: 13px;
    }
    @media print {
      body {
        background: #ffffff;
      }
      .page {
        max-width: none;
        padding: 0;
      }
      @page {
        margin: 16mm;
      }
    }
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <span class="eyebrow">Rapport entreprise</span>
        <h1>${escapeHtml(run.company_name)}</h1>
        <p>${SOURCE_LABELS[run.source]} - Run #${run.run_id} - Rapport généré le ${escapeHtml(createdAt)}</p>
      </div>
      <div class="score">
        <span>Score santé</span>
        <strong>${insights.health_score}</strong>
        <span>Risque ${escapeHtml(formatRisk(insights.risk_level))}</span>
      </div>
    </header>

    <section>
      <h2>Synthèse exécutive</h2>
      <p>${escapeHtml(insights.executive_summary)}</p>
    </section>

    <section class="grid">
      <div class="kpi"><span>Avis analysés</span><strong>${summary.kpis.review_count}</strong></div>
      <div class="kpi"><span>Note moyenne</span><strong>${formatNumber(summary.kpis.average_rating)} / 5</strong></div>
      <div class="kpi"><span>Confiance IA</span><strong>${formatNumber(summary.kpis.average_confidence, 2)}</strong></div>
      <div class="kpi"><span>Réponses entreprise</span><strong>${summary.kpis.responded_count ?? 0}</strong></div>
    </section>

    <section>
      <h2>Priorités recommandées</h2>
      <div class="priority-list">${priorities || "<p>Aucune priorité critique détectée.</p>"}</div>
    </section>

    <section class="two-cols">
      <div class="box">
        <h2>Actions suivantes</h2>
        <ol>${actions}</ol>
      </div>
      <div class="box">
        <h2>Forces à préserver</h2>
        <ul>${strengths || "<li>Aucun point fort isolé pour le moment.</li>"}</ul>
      </div>
    </section>

    <section class="two-cols">
      <div class="box">
        <h2>Sentiment global</h2>
        <table>
          <tbody>
            ${distributionRows(summary.sentiment_distribution, [
              { label: "Négatif", key: "Négatif" as SentimentLabel },
              { label: "Neutre", key: "Neutre" as SentimentLabel },
              { label: "Positif", key: "Positif" as SentimentLabel }
            ])}
          </tbody>
        </table>
      </div>
      <div class="box">
        <h2>Irritants principaux</h2>
        <table>
          <thead><tr><th>Sujet</th><th>Occurrences</th></tr></thead>
          <tbody>${topics || "<tr><td>Aucun irritant détecté</td><td>0</td></tr>"}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Avis critiques représentatifs</h2>
      <div class="review-list">${criticalReviews || "<p>Aucun avis critique détecté.</p>"}</div>
    </section>

    <section>
      <h2>Cas note vs texte</h2>
      <div class="review-list">${mismatches || "<p>Aucun écart note / texte détecté.</p>"}</div>
    </section>

    <section class="box">
      <h2>Points de vigilance</h2>
      <ul>${watchpoints || "<li>Aucun signal faible majeur.</li>"}</ul>
    </section>

    <section class="limits">
      <h2>Limites de lecture</h2>
      <p>Ce rapport repose sur les avis collectés lors du run, les verbatims disponibles et le modèle de sentiment actuellement déployé. Les recommandations doivent être relues avec le contexte métier avant arbitrage opérationnel.</p>
    </section>
  </main>
</body>
</html>`;
}

function benchmarkCompanyRows(companies: BenchmarkCompany[]) {
  return companies
    .map(
      (company) => `
        <tr>
          <td>
            <strong>${escapeHtml(company.company_name)}</strong>
            <span>Run #${company.run_id}</span>
          </td>
          <td>${company.health_score}</td>
          <td>${escapeHtml(formatRisk(company.risk_level))}</td>
          <td>${company.review_count}</td>
          <td>${formatNumber(company.average_rating)} / 5</td>
          <td>${company.negative_count} (${formatPercent(company.negative_rate)})</td>
          <td>${company.neutral_count}</td>
          <td>${company.positive_count}</td>
          <td>
            ${
              company.unique_topics.length > 0
                ? company.unique_topics
                    .slice(0, 4)
                    .map((topic) => `${escapeHtml(formatTopic(topic.topic))} (${topic.count})`)
                    .join("<br />")
                : "Aucun sujet spécifique"
            }
          </td>
        </tr>
      `
    )
    .join("");
}

function benchmarkCommonTopicRows(comparison: RunsComparison) {
  return comparison.common_topics
    .slice(0, 8)
    .map(
      (topic) => `
        <tr>
          <td>${escapeHtml(formatTopic(topic.topic))}</td>
          <td>${topic.total_count}</td>
          <td>${topic.run_count}</td>
          <td>
            ${topic.companies
              .map((company) => `${escapeHtml(company.company_name)}: ${company.count}`)
              .join("<br />")}
          </td>
        </tr>
      `
    )
    .join("");
}

function buildPrintableBenchmarkReport(comparison: RunsComparison) {
  const createdAt = new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "long",
    timeStyle: "short"
  }).format(new Date());

  const bestHealth = comparison.highlights.best_health;
  const highestRisk = comparison.highlights.highest_negative_rate;
  const mostReviews = comparison.highlights.most_reviews;
  const sharedPriority = comparison.highlights.shared_priority;

  const avgHealth =
    comparison.companies.length > 0
      ? comparison.companies.reduce((total, company) => total + company.health_score, 0) /
        comparison.companies.length
      : 0;

  const totalReviews = comparison.companies.reduce(
    (total, company) => total + company.review_count,
    0
  );

  const recommendationCompany = highestRisk ?? comparison.companies[0] ?? null;
  const recommendationTopic = sharedPriority?.topic
    ? formatTopic(sharedPriority.topic)
    : recommendationCompany?.top_topics[0]?.topic
      ? formatTopic(recommendationCompany.top_topics[0].topic)
      : "le principal irritant client";

  return `<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>Rapport benchmark - Runs ${escapeHtml(comparison.run_ids.join(", "))}</title>
  <style>
    :root {
      color: #18202c;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.45;
    }
    body {
      margin: 0;
      background: #eef1f4;
    }
    .page {
      max-width: 1180px;
      margin: 0 auto;
      padding: 34px;
      background: #ffffff;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      border-bottom: 3px solid #18202c;
      padding-bottom: 18px;
      margin-bottom: 22px;
    }
    h1, h2, h3, p {
      margin-top: 0;
    }
    h1 {
      font-size: 30px;
      margin-bottom: 8px;
    }
    h2 {
      color: #1d4ed8;
      font-size: 18px;
      margin-bottom: 12px;
    }
    .eyebrow {
      color: #2563eb;
      font-size: 12px;
      font-weight: 800;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .score {
      min-width: 150px;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 12px;
      text-align: center;
    }
    .score strong {
      display: block;
      font-size: 34px;
      line-height: 1;
      margin: 5px 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin: 18px 0;
    }
    .kpi, .box {
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 12px;
      break-inside: avoid;
    }
    .kpi span, .score span, td span, .muted {
      color: #667085;
      font-size: 12px;
    }
    .kpi strong {
      display: block;
      margin-top: 5px;
      font-size: 22px;
    }
    section {
      margin-top: 24px;
      break-inside: avoid;
    }
    .two-cols {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    td, th {
      border-bottom: 1px solid #d9dee7;
      padding: 8px 5px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: #475467;
      font-size: 12px;
      text-transform: uppercase;
    }
    td strong,
    td span {
      display: block;
    }
    ol, ul {
      margin: 0;
      padding-left: 20px;
    }
    li {
      margin-bottom: 8px;
    }
    .risk {
      color: #b42318;
      font-weight: 800;
    }
    @media print {
      body {
        background: #ffffff;
      }
      .page {
        max-width: none;
        padding: 0;
      }
      @page {
        margin: 14mm;
      }
    }
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <span class="eyebrow">Benchmark concurrentiel</span>
        <h1>Comparaison multi-entreprises</h1>
        <p>${comparison.companies.length} entreprises comparées sur les runs ${escapeHtml(
          comparison.run_ids.join(", ")
        )} - Rapport généré le ${escapeHtml(createdAt)}</p>
      </div>
      <div class="score">
        <span>Score moyen</span>
        <strong>${formatNumber(avgHealth, 0)}</strong>
        <span>Santé comparée</span>
      </div>
    </header>

    <section>
      <h2>Synthèse benchmark</h2>
      <p>
        Le benchmark compare ${comparison.companies.length} entreprises et ${totalReviews}
        avis analysés. ${
          bestHealth
            ? `${escapeHtml(bestHealth.company_name)} obtient le meilleur score santé (${bestHealth.health_score}).`
            : "Aucun meilleur score n'est disponible."
        } ${
          highestRisk
            ? `${escapeHtml(highestRisk.company_name)} concentre le plus fort taux négatif (${formatPercent(
                highestRisk.negative_rate
              )}).`
            : ""
        }
      </p>
    </section>

    <section class="grid">
      <div class="kpi">
        <span>Meilleur score santé</span>
        <strong>${bestHealth ? bestHealth.health_score : "-"}</strong>
        <span>${bestHealth ? escapeHtml(bestHealth.company_name) : "Non disponible"}</span>
      </div>
      <div class="kpi">
        <span>Plus gros risque</span>
        <strong>${highestRisk ? formatPercent(highestRisk.negative_rate) : "-"}</strong>
        <span>${highestRisk ? escapeHtml(highestRisk.company_name) : "Non disponible"}</span>
      </div>
      <div class="kpi">
        <span>Plus gros volume</span>
        <strong>${mostReviews ? mostReviews.review_count : "-"}</strong>
        <span>${mostReviews ? escapeHtml(mostReviews.company_name) : "Non disponible"}</span>
      </div>
      <div class="kpi">
        <span>Irritant partage</span>
        <strong>${sharedPriority ? escapeHtml(formatTopic(sharedPriority.topic)) : "Aucun"}</strong>
        <span>${sharedPriority ? `${sharedPriority.total_count} occurrences` : "Pas de sujet commun fort"}</span>
      </div>
    </section>

    <section>
      <h2>Tableau comparatif</h2>
      <table>
        <thead>
          <tr>
            <th>Entreprise</th>
            <th>Score</th>
            <th>Risque</th>
            <th>Avis</th>
            <th>Note</th>
            <th>Négatif</th>
            <th>Neutre</th>
            <th>Positif</th>
            <th>Irritants propres</th>
          </tr>
        </thead>
        <tbody>${benchmarkCompanyRows(comparison.companies)}</tbody>
      </table>
    </section>

    <section class="two-cols">
      <div class="box">
        <h2>Irritants communs</h2>
        ${
          comparison.common_topics.length === 0
            ? "<p>Aucun irritant commun fort détecté.</p>"
            : `<table>
                <thead><tr><th>Sujet</th><th>Total</th><th>Runs</th><th>Détail</th></tr></thead>
                <tbody>${benchmarkCommonTopicRows(comparison)}</tbody>
              </table>`
        }
      </div>
      <div class="box">
        <h2>Actions recommandées</h2>
        <ol>
          <li>Prioriser ${escapeHtml(recommendationTopic.toLocaleLowerCase("fr-FR"))} pour l'entreprise la plus exposée.</li>
          <li>Comparer les irritants propres pour distinguer les sujets sectoriels des problèmes internes.</li>
          <li>Utiliser le meilleur score santé comme point de référence opérationnelle.</li>
        </ol>
      </div>
    </section>

    <section class="box">
      <h2>Lecture métier</h2>
      <p>
        Ce benchmark sert à repérer les écarts relatifs entre entreprises analysées avec le même modèle.
        Il ne remplace pas une étude qualitative complète, mais il aide à prioriser les irritants qui
        reviennent le plus et les entreprises qui concentrent le plus de risque client.
      </p>
    </section>
  </main>
</body>
</html>`;
}

function formatRisk(value: string) {
  const labels: Record<string, string> = {
    faible: "Faible",
    modere: "Modéré",
    eleve: "Élevé",
    critique: "Critique"
  };
  return labels[value] ?? value;
}

function formatSeverity(value: string) {
  const labels: Record<string, string> = {
    moderee: "Modérée",
    elevee: "Élevée",
    critique: "Critique"
  };
  return labels[value] ?? value;
}

export default function App() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [isLoginSubmitting, setIsLoginSubmitting] = useState(false);
  const [isAcceptingInvitation, setIsAcceptingInvitation] = useState(false);
  const [loginEmail, setLoginEmail] = useState("demo@satisfaction.local");
  const [loginPassword, setLoginPassword] = useState("demo-password");
  const [invitationToken, setInvitationToken] = useState(
    () => new URLSearchParams(window.location.search).get("invitation_token") ?? ""
  );
  const [invitationFullName, setInvitationFullName] = useState("");
  const [invitationPassword, setInvitationPassword] = useState("");
  const [organizationUsers, setOrganizationUsers] = useState<OrganizationUser[]>([]);
  const [isOrganizationUsersLoading, setIsOrganizationUsersLoading] = useState(false);
  const [isCreatingOrganizationUser, setIsCreatingOrganizationUser] = useState(false);
  const [organizationUserEmail, setOrganizationUserEmail] = useState("");
  const [organizationUserFullName, setOrganizationUserFullName] = useState("");
  const [organizationUserRole, setOrganizationUserRole] =
    useState<UserRole>("member");
  const [organizationUserError, setOrganizationUserError] = useState<string | null>(
    null
  );
  const [organizationUserMessage, setOrganizationUserMessage] =
    useState<string | null>(null);
  const [reviewSources, setReviewSources] =
    useState<ReviewSource[]>(DEFAULT_REVIEW_SOURCES);
  const [isReviewSourcesLoading, setIsReviewSourcesLoading] = useState(false);
  const [reviewSourcesError, setReviewSourcesError] = useState<string | null>(
    null
  );
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [trend, setTrend] = useState<AnalysisRunTrend | null>(null);
  const [isTrendLoading, setIsTrendLoading] = useState(false);
  const [trendError, setTrendError] = useState<string | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reviewsTotal, setReviewsTotal] = useState(0);
  const [reviewsLimit, setReviewsLimit] = useState(30);
  const [reviewsOffset, setReviewsOffset] = useState(0);
  const [runEvents, setRunEvents] = useState<AnalysisRunEvent[]>([]);
  const [sentimentFilter, setSentimentFilter] =
    useState<SentimentLabel | "Tous">("Tous");
  const [company, setCompany] = useState(
    "https://fr.trustpilot.com/review/www.darty.com"
  );
  const [sourceMode, setSourceMode] = useState<AnalysisSource>("trustpilot");
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvColumnMapping, setCsvColumnMapping] =
    useState<CsvColumnMapping>({});
  const [csvPreview, setCsvPreview] = useState<CsvImportPreview | null>(null);
  const [csvPreviewError, setCsvPreviewError] = useState<string | null>(null);
  const [isCsvPreviewLoading, setIsCsvPreviewLoading] = useState(false);
  const [pagesPerStar, setPagesPerStar] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryingRunId, setRetryingRunId] = useState<number | null>(null);
  const [correctingReviewId, setCorrectingReviewId] = useState<number | null>(null);
  const [comparisonRunIds, setComparisonRunIds] = useState<number[]>([]);
  const [comparison, setComparison] = useState<RunsComparison | null>(null);
  const [isComparisonLoading, setIsComparisonLoading] = useState(false);
  const [feedbackQuality, setFeedbackQuality] = useState<FeedbackQuality | null>(null);
  const [isFeedbackQualityLoading, setIsFeedbackQualityLoading] = useState(false);
  const [trainingOverview, setTrainingOverview] =
    useState<ModelTrainingOverview | null>(null);
  const [isTrainingOverviewLoading, setIsTrainingOverviewLoading] = useState(false);
  const [isTrainingSubmitting, setIsTrainingSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshRuns(selectLatest = false) {
    const nextRuns = await listRuns();
    setRuns(nextRuns);
    if (selectLatest && nextRuns.length > 0) {
      setSelectedRunId(nextRuns[0].run_id);
      return;
    }
    if (!selectedRunId && nextRuns.length > 0) {
      setSelectedRunId(nextRuns[0].run_id);
    }
  }

  async function refreshFeedbackQuality() {
    setIsFeedbackQualityLoading(true);
    try {
      const quality = await getFeedbackQuality();
      setFeedbackQuality(quality);
    } finally {
      setIsFeedbackQualityLoading(false);
    }
  }

  async function refreshTrainingOverview() {
    setIsTrainingOverviewLoading(true);
    try {
      const overview = await getModelTrainingOverview();
      setTrainingOverview(overview);
    } finally {
      setIsTrainingOverviewLoading(false);
    }
  }

  async function refreshOrganizationUsers() {
    setIsOrganizationUsersLoading(true);
    try {
      const users = await listOrganizationUsers();
      setOrganizationUsers(users);
    } finally {
      setIsOrganizationUsersLoading(false);
    }
  }

  async function refreshReviewSources() {
    setIsReviewSourcesLoading(true);
    setReviewSourcesError(null);
    try {
      const sources = await listReviewSources();
      setReviewSources(sources);
      const activeSources = sources.filter(
        (source) =>
          source.status === "active" &&
          source.supports_analysis &&
          isAnalysisSource(source.source_id)
      );
      if (!activeSources.some((source) => source.source_id === sourceMode)) {
        setSourceMode((activeSources[0]?.source_id as AnalysisSource) ?? "trustpilot");
      }
    } finally {
      setIsReviewSourcesLoading(false);
    }
  }

  useEffect(() => {
    if (!hasAuthToken()) {
      setIsAuthLoading(false);
      setIsLoading(false);
      return;
    }

    getCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => {
        clearAuthToken();
        setCurrentUser(null);
      })
      .finally(() => setIsAuthLoading(false));
  }, []);

  useEffect(() => {
    if (!currentUser) {
      return;
    }

    setIsLoading(true);
    refreshRuns()
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsLoading(false));
    refreshFeedbackQuality().catch((err: Error) => setError(err.message));
    refreshTrainingOverview().catch((err: Error) => setError(err.message));
    refreshOrganizationUsers().catch((err: Error) => setOrganizationUserError(err.message));
    refreshReviewSources().catch((err: Error) => setReviewSourcesError(err.message));
  }, [currentUser?.user_id]);

  useEffect(() => {
    const hasActiveRun = runs.some(
      (run) => run.status === "pending" || run.status === "running"
    );

    if (!hasActiveRun) {
      return;
    }

    const timer = window.setInterval(() => {
      refreshRuns().catch((err: Error) => setError(err.message));
    }, 3000);

    return () => window.clearInterval(timer);
  }, [runs, selectedRunId]);

  useEffect(() => {
    const hasActiveTraining = Boolean(trainingOverview?.active_run);

    if (!hasActiveTraining) {
      return;
    }

    const timer = window.setInterval(() => {
      refreshTrainingOverview().catch((err: Error) => setError(err.message));
    }, 4000);

    return () => window.clearInterval(timer);
  }, [trainingOverview?.active_run?.training_run_id, trainingOverview?.active_run?.status]);

  const selectedRun = useMemo(
    () => runs.find((run) => run.run_id === selectedRunId) ?? null,
    [runs, selectedRunId]
  );
  const selectedRunDuration = formatDuration(
    selectedRun?.execution_duration_seconds
  );
  const completedRuns = useMemo(
    () => runs.filter((run) => run.status === "completed"),
    [runs]
  );
  const reviewsPage = Math.floor(reviewsOffset / reviewsLimit) + 1;
  const reviewsPageCount = Math.max(1, Math.ceil(reviewsTotal / reviewsLimit));
  const canGoToPreviousReviews = reviewsOffset > 0;
  const canGoToNextReviews = reviewsOffset + reviews.length < reviewsTotal;

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoginSubmitting(true);
    setError(null);

    try {
      const token = await login(loginEmail.trim(), loginPassword);
      setCurrentUser(token.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible");
    } finally {
      setIsLoginSubmitting(false);
    }
  }

  async function handleAcceptInvitation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsAcceptingInvitation(true);
    setError(null);

    try {
      const token = await acceptOrganizationInvitation({
        token: invitationToken.trim(),
        password: invitationPassword,
        full_name: invitationFullName.trim() || null
      });
      setInvitationPassword("");
      setInvitationFullName("");
      setCurrentUser(token.user);
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invitation impossible a accepter");
    } finally {
      setIsAcceptingInvitation(false);
    }
  }

  function handleLogout() {
    clearAuthToken();
    setCurrentUser(null);
    setRuns([]);
    setSelectedRunId(null);
    setSummary(null);
    setTrend(null);
    setTrendError(null);
    setReviews([]);
    setReviewsTotal(0);
    setRunEvents([]);
    setComparisonRunIds([]);
    setComparison(null);
    setFeedbackQuality(null);
    setTrainingOverview(null);
    setOrganizationUsers([]);
    setOrganizationUserError(null);
    setOrganizationUserMessage(null);
    setReviewSources(DEFAULT_REVIEW_SOURCES);
    setReviewSourcesError(null);
    setError(null);
  }

  async function handleCreateOrganizationUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setOrganizationUserError(null);
    setOrganizationUserMessage(null);
    setIsCreatingOrganizationUser(true);

    try {
      const invitedUser = await inviteOrganizationUser({
        email: organizationUserEmail.trim(),
        full_name: organizationUserFullName.trim() || null,
        role: organizationUserRole
      });
      setOrganizationUserEmail("");
      setOrganizationUserFullName("");
      setOrganizationUserRole("member");
      setOrganizationUserMessage(
        invitedUser.invitation_accept_url
          ? `Invitation creee pour ${invitedUser.email}. Lien: ${invitedUser.invitation_accept_url}`
          : `Invitation creee pour ${invitedUser.email}.`
      );
      await refreshOrganizationUsers();
    } catch (err) {
      setOrganizationUserError(
        err instanceof Error ? err.message : "Invitation utilisateur impossible"
      );
    } finally {
      setIsCreatingOrganizationUser(false);
    }
  }

  function handleReviewSourceSelect(sourceId: string) {
    if (!isAnalysisSource(sourceId)) {
      return;
    }

    setSourceMode(sourceId);
    setError(null);
  }

  function toggleComparisonRun(runId: number) {
    if (comparisonRunIds.includes(runId)) {
      setComparisonRunIds((currentRunIds) =>
        currentRunIds.filter((currentRunId) => currentRunId !== runId)
      );
      setError(null);
      return;
    }

    if (comparisonRunIds.length >= 4) {
      setError("Tu peux comparer jusqu'à 4 analyses en même temps.");
      return;
    }

    setComparisonRunIds((currentRunIds) => [...currentRunIds, runId]);
    setError(null);
  }

  async function handleCompareRuns() {
    if (comparisonRunIds.length < 2) {
      setError("Sélectionne au moins 2 analyses terminées à comparer.");
      return;
    }

    setIsComparisonLoading(true);
    setError(null);

    try {
      const nextComparison = await compareRuns(comparisonRunIds);
      setComparison(nextComparison);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setIsComparisonLoading(false);
    }
  }

  async function handleStartModelTraining() {
    setIsTrainingSubmitting(true);
    setError(null);

    try {
      await createModelTrainingRun();
      await Promise.all([refreshTrainingOverview(), refreshFeedbackQuality()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setIsTrainingSubmitting(false);
    }
  }

  function buildDetectedColumnMapping(preview: CsvImportPreview): CsvColumnMapping {
    return CSV_MAPPING_FIELDS.reduce<CsvColumnMapping>((mapping, field) => {
      mapping[field.key] = preview.detected_columns[field.key] ?? "";
      return mapping;
    }, {});
  }

  async function loadCsvPreview(
    file: File,
    columnMapping: CsvColumnMapping | null,
    syncDetectedMapping = false
  ) {
    setCsvPreview(null);
    setCsvPreviewError(null);
    setIsCsvPreviewLoading(true);

    try {
      const preview = await previewCsvFile(file, columnMapping);
      setCsvPreview(preview);
      setCsvPreviewError(preview.error_message);
      if (syncDetectedMapping) {
        setCsvColumnMapping(buildDetectedColumnMapping(preview));
      }
    } catch (err) {
      setCsvPreviewError(
        err instanceof Error ? err.message : "CSV impossible a previsualiser"
      );
    } finally {
      setIsCsvPreviewLoading(false);
    }
  }

  async function handleCsvFileChange(file: File | null) {
    setCsvFile(file);
    setCsvColumnMapping({});
    setCsvPreview(null);
    setCsvPreviewError(null);

    if (!file) {
      return;
    }

    await loadCsvPreview(file, null, true);
  }

  function handleCsvColumnMappingChange(
    field: keyof CsvColumnMapping,
    column: string
  ) {
    const nextMapping = {
      ...csvColumnMapping,
      [field]: column
    };
    setCsvColumnMapping(nextMapping);

    if (csvFile) {
      loadCsvPreview(csvFile, nextMapping).catch((err: Error) =>
        setCsvPreviewError(err.message)
      );
    }
  }

  useEffect(() => {
    if (!selectedRunId || !selectedRun) {
      setRunEvents([]);
      return;
    }

    const runId = selectedRunId;
    let isCancelled = false;

    async function loadEvents() {
      try {
        const events = await getRunEvents(runId);
        if (!isCancelled) {
          setRunEvents(events);
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Erreur inconnue");
        }
      }
    }

    loadEvents();

    if (selectedRun.status !== "pending" && selectedRun.status !== "running") {
      return () => {
        isCancelled = true;
      };
    }

    const timer = window.setInterval(loadEvents, 3000);
    return () => {
      isCancelled = true;
      window.clearInterval(timer);
    };
  }, [selectedRunId, selectedRun?.status]);

  useEffect(() => {
    setReviewsOffset(0);
  }, [selectedRunId, sentimentFilter, reviewsLimit]);

  useEffect(() => {
    if (!selectedRunId || !selectedRun) {
      setSummary(null);
      setTrend(null);
      setTrendError(null);
      setReviews([]);
      setReviewsTotal(0);
      return;
    }

    if (selectedRun.status !== "completed") {
      setSummary(null);
      setTrend(null);
      setTrendError(null);
      setReviews([]);
      setReviewsTotal(0);
      setIsSummaryLoading(false);
      setIsTrendLoading(false);
      return;
    }

    setIsSummaryLoading(true);
    setError(null);

    Promise.all([
      getSummary(selectedRunId),
      getReviews(selectedRunId, sentimentFilter, reviewsLimit, reviewsOffset)
    ])
      .then(([nextSummary, nextReviews]) => {
        setSummary(nextSummary);
        setReviews(nextReviews.reviews);
        setReviewsTotal(nextReviews.total);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsSummaryLoading(false));
  }, [
    selectedRunId,
    selectedRun?.status,
    sentimentFilter,
    reviewsLimit,
    reviewsOffset
  ]);

  useEffect(() => {
    if (!selectedRunId || selectedRun?.status !== "completed") {
      return;
    }

    let isCancelled = false;
    setIsTrendLoading(true);
    setTrendError(null);

    getRunTrend(selectedRunId)
      .then((nextTrend) => {
        if (!isCancelled) {
          setTrend(nextTrend);
        }
      })
      .catch((err: Error) => {
        if (!isCancelled) {
          setTrend(null);
          setTrendError(err.message);
        }
      })
      .finally(() => {
        if (!isCancelled) {
          setIsTrendLoading(false);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [selectedRunId, selectedRun?.status]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (sourceMode === "trustpilot") {
      const validationError = validateCompanyInput(company);
      if (validationError) {
        setError(validationError);
        return;
      }
    } else if (company.trim().length < 2) {
      setError("Renseigne le nom de l'entreprise a analyser.");
      return;
    } else if (!csvFile) {
      setError("Selectionne un fichier CSV d'avis clients.");
      return;
    } else if (isCsvPreviewLoading) {
      setError("Attends la fin de la previsualisation du CSV.");
      return;
    } else if (csvPreviewError || !csvPreview) {
      setError(csvPreviewError ?? "Previsualise le CSV avant de lancer l'analyse.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const run =
        sourceMode === "csv"
          ? await uploadCsvRun(company.trim(), csvFile as File, csvColumnMapping)
          : await createRun({
              company: company.trim(),
              source: "trustpilot",
              stars: [1, 2, 3, 4, 5],
              pages_per_star: pagesPerStar,
              execute_immediately: true
            });
      setSelectedRunId(run.run_id);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRetryRun(runId: number) {
    setRetryingRunId(runId);
    setError(null);

    try {
      const run = await executeRun(runId);
      setSelectedRunId(run.run_id);
      setSummary(null);
      setTrend(null);
      setTrendError(null);
      setReviews([]);
      await refreshRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setRetryingRunId(null);
    }
  }

  async function handleExport(runId: number) {
    try {
      const blob = await exportReviews(runId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `analysis_run_${runId}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  async function handleFeedbackExport(runId: number) {
    try {
      const blob = await exportFeedback(runId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `analysis_run_${runId}_feedback.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    }
  }

  function handleSentimentFilterChange(sentiment: SentimentLabel | "Tous") {
    setSentimentFilter(sentiment);
    setReviewsOffset(0);
  }

  function handleReviewsLimitChange(limit: number) {
    setReviewsLimit(limit);
    setReviewsOffset(0);
  }

  function handlePreviousReviewsPage() {
    setReviewsOffset((currentOffset) => Math.max(0, currentOffset - reviewsLimit));
  }

  function handleNextReviewsPage() {
    setReviewsOffset((currentOffset) => currentOffset + reviewsLimit);
  }

  async function refreshSummaryAfterFeedback(runId: number) {
    const nextSummary = await getSummary(runId);
    if (selectedRunId === runId) {
      setSummary(nextSummary);
    }
  }

  async function handleSaveReviewFeedback(reviewId: number, label: SentimentLabel) {
    if (!selectedRun) {
      return;
    }

    setCorrectingReviewId(reviewId);
    setError(null);

    try {
      const feedback = await saveReviewFeedback(selectedRun.run_id, reviewId, label);
      setReviews((currentReviews) =>
        currentReviews.map((review) =>
          review.review_id === reviewId
            ? {
                ...review,
                corrected_label: feedback.corrected_label,
                feedback_comment: feedback.comment,
                feedback_updated_at: feedback.updated_at
              }
            : review
        )
      );
      await refreshSummaryAfterFeedback(selectedRun.run_id);
      await refreshFeedbackQuality();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setCorrectingReviewId(null);
    }
  }

  async function handleDeleteReviewFeedback(reviewId: number) {
    if (!selectedRun) {
      return;
    }

    setCorrectingReviewId(reviewId);
    setError(null);

    try {
      await deleteReviewFeedback(selectedRun.run_id, reviewId);
      setReviews((currentReviews) =>
        currentReviews.map((review) =>
          review.review_id === reviewId
            ? {
                ...review,
                corrected_label: null,
                feedback_comment: null,
                feedback_updated_at: null
              }
            : review
        )
      );
      await refreshSummaryAfterFeedback(selectedRun.run_id);
      await refreshFeedbackQuality();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setCorrectingReviewId(null);
    }
  }

  function handleReportExport() {
    if (!selectedRun || !summary) {
      setError("Le rapport n'est pas encore disponible.");
      return;
    }

    const reportWindow = window.open("", "_blank");
    if (!reportWindow) {
      setError("Le navigateur a bloque l'ouverture du rapport imprimable.");
      return;
    }

    reportWindow.document.open();
    reportWindow.document.write(buildPrintableReport(selectedRun, summary));
    reportWindow.document.close();
    reportWindow.document.title = reportFileName(selectedRun);
    reportWindow.focus();

    window.setTimeout(() => {
      reportWindow.print();
    }, 400);
  }

  function handleBenchmarkReportExport(comparisonToExport: RunsComparison) {
    const reportWindow = window.open("", "_blank");
    if (!reportWindow) {
      setError("Le navigateur a bloque l'ouverture du rapport benchmark.");
      return;
    }

    reportWindow.document.open();
    reportWindow.document.write(buildPrintableBenchmarkReport(comparisonToExport));
    reportWindow.document.close();
    reportWindow.document.title = benchmarkReportFileName(comparisonToExport);
    reportWindow.focus();

    window.setTimeout(() => {
      reportWindow.print();
    }, 400);
  }

  if (isAuthLoading) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <div className="brand auth-brand">
            <div className="brand-mark">SC</div>
            <div>
              <h1>Satisfaction Client</h1>
              <p>Chargement de la session</p>
            </div>
          </div>
          <div className="loading-line">
            <Loader2 className="spin" size={18} />
            Verification de l'utilisateur connecte...
          </div>
        </section>
      </main>
    );
  }

  if (!currentUser) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <div className="brand auth-brand">
            <div className="brand-mark">SC</div>
            <div>
              <h1>Satisfaction Client</h1>
              <p>Espace client B2B</p>
            </div>
          </div>

          <div className="section-heading">
            <div>
              <span>CONNEXION</span>
              <h3>Acceder a ton espace entreprise</h3>
              <p>Compte demo local cree automatiquement au demarrage de l'API.</p>
            </div>
          </div>

          <form className="auth-form" onSubmit={handleLogin}>
            <label htmlFor="login-email">Email</label>
            <input
              id="login-email"
              type="email"
              value={loginEmail}
              onChange={(event) => setLoginEmail(event.target.value)}
              disabled={isLoginSubmitting}
            />

            <label htmlFor="login-password">Mot de passe</label>
            <input
              id="login-password"
              type="password"
              value={loginPassword}
              onChange={(event) => setLoginPassword(event.target.value)}
              disabled={isLoginSubmitting}
            />

            {error ? <p className="form-error">{error}</p> : null}

            <button className="primary-action" disabled={isLoginSubmitting} type="submit">
              {isLoginSubmitting ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              Se connecter
            </button>
          </form>

          <div className="auth-divider">ou</div>

          <form className="auth-form invitation-form" onSubmit={handleAcceptInvitation}>
            <div className="mini-heading">
              <strong>Accepter une invitation</strong>
              <span>Nouvel utilisateur</span>
            </div>
            <label htmlFor="invitation-token">Token d'invitation</label>
            <input
              id="invitation-token"
              onChange={(event) => setInvitationToken(event.target.value)}
              placeholder="Token recu dans le lien"
              type="text"
              value={invitationToken}
              disabled={isAcceptingInvitation}
            />
            <label htmlFor="invitation-name">Nom complet</label>
            <input
              id="invitation-name"
              onChange={(event) => setInvitationFullName(event.target.value)}
              placeholder="Nom complet"
              type="text"
              value={invitationFullName}
              disabled={isAcceptingInvitation}
            />
            <label htmlFor="invitation-password">Mot de passe</label>
            <input
              id="invitation-password"
              minLength={8}
              onChange={(event) => setInvitationPassword(event.target.value)}
              placeholder="Choisis un mot de passe"
              type="password"
              value={invitationPassword}
              disabled={isAcceptingInvitation}
            />
            <button
              className="secondary-action full-width-action"
              disabled={isAcceptingInvitation || !invitationToken.trim()}
              type="submit"
            >
              {isAcceptingInvitation ? (
                <Loader2 className="spin" size={18} />
              ) : (
                <UserPlus size={18} />
              )}
              Activer mon compte
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">SC</div>
          <div>
            <h1>Satisfaction Client</h1>
            <p>Analyse d'avis clients</p>
          </div>
        </div>

        <section className="tenant-card">
          <div>
            <span>Espace client</span>
            <strong>{currentUser.organization.name}</strong>
            <small>{currentUser.email}</small>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={handleLogout}
            title="Se deconnecter"
          >
            <LogOut size={18} />
          </button>
        </section>

        <ReviewSourcesPanel
          currentSource={sourceMode}
          error={reviewSourcesError}
          isLoading={isReviewSourcesLoading}
          onRefresh={() =>
            refreshReviewSources().catch((err: Error) =>
              setReviewSourcesError(err.message)
            )
          }
          onSelectSource={handleReviewSourceSelect}
          sources={reviewSources}
        />

        <form className="analysis-form" onSubmit={handleSubmit}>
          <div className="analysis-form-heading">
            <span>Nouvelle analyse</span>
            <strong>{SOURCE_LABELS[sourceMode]}</strong>
          </div>

          <label htmlFor="company">
            {sourceMode === "csv"
              ? "Entreprise a analyser"
              : "Entreprise ou URL Trustpilot"}
          </label>
          <div className="input-with-icon">
            <Search aria-hidden="true" size={18} />
            <input
              id="company"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder={
                sourceMode === "csv" ? "Nom de l'entreprise" : "www.darty.com"
              }
              disabled={isSubmitting}
            />
          </div>

          {sourceMode === "csv" ? (
            <>
              <label htmlFor="csv-file">Fichier CSV d'avis</label>
              <label className="file-drop" htmlFor="csv-file">
                <FileText aria-hidden="true" size={18} />
                <span>{csvFile ? csvFile.name : "Choisir un fichier .csv"}</span>
                <input
                  accept=".csv,text/csv"
                  disabled={isSubmitting}
                  id="csv-file"
                  onChange={(event) =>
                    handleCsvFileChange(event.target.files?.[0] ?? null)
                  }
                  type="file"
                />
              </label>
              {isCsvPreviewLoading && (
                <div className="csv-preview-card">
                  <Loader2 className="spin" size={16} />
                  <span>Lecture du CSV...</span>
                </div>
              )}
              {csvPreviewError && !csvPreview && (
                <div className="csv-preview-card error">
                  <AlertTriangle size={16} />
                  <span>{csvPreviewError}</span>
                </div>
              )}
              {csvPreview && (
                <div className="csv-preview-card">
                  <div className="csv-preview-heading">
                    <strong>Controle avant import</strong>
                    <span>{csvPreview.review_count} avis</span>
                  </div>
                  <div className="csv-preview-stats">
                    <span>{csvPreview.review_count} exploitables</span>
                    <span>{csvPreview.skipped_rows} ignores</span>
                  </div>
                  <div className="csv-mapping-grid">
                    {CSV_MAPPING_FIELDS.map((field) => (
                      <label key={field.key}>
                        <span>
                          {field.label}
                          {field.required ? " *" : ""}
                        </span>
                        <select
                          onChange={(event) =>
                            handleCsvColumnMappingChange(
                              field.key,
                              event.target.value
                            )
                          }
                          value={csvColumnMapping[field.key] ?? ""}
                        >
                          {!field.required && (
                            <option value="">Ignorer</option>
                          )}
                          {field.required && (
                            <option value="">Selectionner</option>
                          )}
                          {csvPreview.available_columns.map((column) => (
                            <option key={column} value={column}>
                              {column}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                  {csvPreview.error_message && (
                    <div className="csv-preview-inline-error">
                      <AlertTriangle size={14} />
                      <span>{csvPreview.error_message}</span>
                    </div>
                  )}
                  <div className="csv-preview-list">
                    {csvPreview.preview_reviews.map((review) => (
                      <article key={review.row_number}>
                        <strong>{review.rating} / 5</strong>
                        <p>{review.verbatim}</p>
                      </article>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              <label htmlFor="pages">Pages par note</label>
              <div className="stepper">
                {[1, 3, 5, 10].map((value) => (
                  <button
                    className={pagesPerStar === value ? "active" : ""}
                    key={value}
                    type="button"
                    onClick={() => setPagesPerStar(value)}
                    disabled={isSubmitting}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </>
          )}

          <button
            className="primary-action"
            disabled={
              isSubmitting ||
              (sourceMode === "csv" &&
                (!csvPreview || Boolean(csvPreviewError) || isCsvPreviewLoading))
            }
          >
            {isSubmitting ? (
              <Loader2 className="spin" size={18} />
            ) : (
              <Play size={18} />
            )}
            {isSubmitting
              ? "Analyse en cours"
              : sourceMode === "csv"
                ? "Importer le CSV"
                : "Lancer l'analyse"}
          </button>
        </form>

        <div className="run-panel">
          <div className="panel-heading">
            <h2>Historique</h2>
            <button
              className="icon-button"
              onClick={() => refreshRuns(true)}
              title="Rafraîchir les analyses"
              type="button"
            >
              <RefreshCw size={18} />
            </button>
          </div>

          <div className="run-list">
            {isLoading && <p className="muted">Chargement des analyses...</p>}
            {!isLoading && runs.length === 0 && (
              <p className="muted">Aucune analyse disponible.</p>
            )}
            {runs.map((run) => (
              <button
                className={`run-item ${
                  run.run_id === selectedRunId ? "selected" : ""
                }`}
                key={run.run_id}
                onClick={() => setSelectedRunId(run.run_id)}
                type="button"
              >
                <span>
                  <strong>{run.company_name}</strong>
                  <small>Run #{run.run_id} - {formatDate(run.created_at)}</small>
                </span>
                <StatusBadge status={run.status} />
              </button>
            ))}
          </div>
        </div>

        <div className="benchmark-panel">
          <div className="panel-heading">
            <h2>Benchmark</h2>
            <small>{comparisonRunIds.length}/4</small>
          </div>
          <p className="muted">
            Sélectionne 2 à 4 analyses terminées pour comparer les entreprises.
          </p>

          <div className="benchmark-select-list">
            {completedRuns.length === 0 && (
              <p className="muted">Aucun run termine disponible.</p>
            )}
            {completedRuns.slice(0, 8).map((run) => {
              const isSelected = comparisonRunIds.includes(run.run_id);
              return (
                <button
                  className={`benchmark-choice ${isSelected ? "selected" : ""}`}
                  key={run.run_id}
                  onClick={() => toggleComparisonRun(run.run_id)}
                  type="button"
                >
                  <span aria-hidden="true">{isSelected ? "✓" : "+"}</span>
                  <strong>{run.company_name}</strong>
                  <small>Run #{run.run_id}</small>
                </button>
              );
            })}
          </div>

          <div className="benchmark-actions">
            <button
              className="primary-action"
              disabled={comparisonRunIds.length < 2 || isComparisonLoading}
              onClick={handleCompareRuns}
              type="button"
            >
              {isComparisonLoading ? (
                <Loader2 className="spin" size={18} />
              ) : (
                <BarChart3 size={18} />
              )}
              Comparer
            </button>
            <button
              className="secondary-action"
              disabled={comparisonRunIds.length === 0 && !comparison}
              onClick={() => {
                setComparisonRunIds([]);
                setComparison(null);
              }}
              type="button"
            >
              Reset
            </button>
          </div>
        </div>
      </aside>

      <section className="workspace">
        {error && (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {comparison && (
          <BenchmarkPanel
            comparison={comparison}
            onClose={() => setComparison(null)}
            onExportReport={() => handleBenchmarkReportExport(comparison)}
          />
        )}

        <ClientSpacePanel
          currentUser={currentUser}
          isCreatingUser={isCreatingOrganizationUser}
          isLoadingUsers={isOrganizationUsersLoading}
          message={organizationUserMessage}
          newUserEmail={organizationUserEmail}
          newUserFullName={organizationUserFullName}
          newUserRole={organizationUserRole}
          onCreateUser={handleCreateOrganizationUser}
          onRefreshUsers={() =>
            refreshOrganizationUsers().catch((err: Error) =>
              setOrganizationUserError(err.message)
            )
          }
          onUpdateNewUserEmail={setOrganizationUserEmail}
          onUpdateNewUserFullName={setOrganizationUserFullName}
          onUpdateNewUserRole={setOrganizationUserRole}
          users={organizationUsers}
          usersError={organizationUserError}
        />

        <AIQualityPanel
          isLoading={isFeedbackQualityLoading}
          onRefresh={() =>
            refreshFeedbackQuality().catch((err: Error) => setError(err.message))
          }
          quality={feedbackQuality}
        />

        <ModelTrainingPanel
          feedbackQuality={feedbackQuality}
          isLoading={isTrainingOverviewLoading}
          isSubmitting={isTrainingSubmitting}
          onRefresh={() =>
            refreshTrainingOverview().catch((err: Error) => setError(err.message))
          }
          onStartTraining={handleStartModelTraining}
          overview={trainingOverview}
        />

        {!selectedRun && !isLoading && (
          <div className="empty-state">
            <BarChart3 size={32} />
            <h2>Choisis ou lance une analyse</h2>
            <p>
              Le rapport entreprise apparaitra ici avec les KPI, irritants et avis
              prioritaires.
            </p>
          </div>
        )}

        {selectedRun && (
          <>
            <header className="report-header">
              <div>
                <span className="eyebrow">Rapport entreprise</span>
                <h2>{selectedRun.company_name}</h2>
                <p>
                  {SOURCE_LABELS[selectedRun.source]} - Run #{selectedRun.run_id} -{" "}
                  {selectedRun.total_reviews} avis
                  {selectedRunDuration ? ` - ${selectedRunDuration}` : ""}
                </p>
              </div>
              <div className="header-actions">
                <StatusBadge status={selectedRun.status} />
                {selectedRun.status === "failed" && (
                  <button
                    className="secondary-action danger-action"
                    disabled={retryingRunId === selectedRun.run_id}
                    onClick={() => handleRetryRun(selectedRun.run_id)}
                    title="Relancer cette analyse"
                    type="button"
                  >
                    {retryingRunId === selectedRun.run_id ? (
                      <Loader2 className="spin" size={18} />
                    ) : (
                      <RefreshCw size={18} />
                    )}
                    Relancer
                  </button>
                )}
                <button
                  className="secondary-action"
                  disabled={!summary || selectedRun.status !== "completed"}
                  onClick={handleReportExport}
                  title="Exporter le rapport imprimable"
                  type="button"
                >
                  <FileText size={18} />
                  Rapport PDF
                </button>
                <button
                  className="secondary-action"
                  disabled={selectedRun.status !== "completed"}
                  onClick={() => handleExport(selectedRun.run_id)}
                  title="Exporter le CSV"
                  type="button"
                >
                  <Download size={18} />
                  Export CSV
                </button>
                <button
                  className="secondary-action"
                  disabled={selectedRun.status !== "completed"}
                  onClick={() => handleFeedbackExport(selectedRun.run_id)}
                  title="Exporter les corrections humaines"
                  type="button"
                >
                  <Download size={18} />
                  Corrections CSV
                </button>
              </div>
            </header>

            {isSummaryLoading && (
              <div className="loading-line">
                <Loader2 className="spin" size={18} />
                Chargement du rapport...
              </div>
            )}

            {(selectedRun.status === "pending" ||
              selectedRun.status === "running") && (
              <div className="processing-state">
                <Hourglass size={28} />
                <div>
                  <h3>
                    {selectedRun.status === "pending"
                      ? "Analyse en file d'attente"
                      : "Analyse en cours"}
                  </h3>
                  <p>
                    Le scraping et la prediction tournent dans le worker Celery.
                    Le rapport se mettra a jour automatiquement.
                  </p>
                  <button
                    className="secondary-action compact-action"
                    onClick={() => refreshRuns()}
                    type="button"
                  >
                    <RefreshCw size={18} />
                    Actualiser
                  </button>
                </div>
              </div>
            )}

            {selectedRun.status === "empty" && (
              <EmptyRunState message={selectedRun.error_message} />
            )}

            {selectedRun.status === "failed" && (
              <FailedRunState
                errorMessage={selectedRun.error_message}
                isRetrying={retryingRunId === selectedRun.run_id}
                onRetry={() => handleRetryRun(selectedRun.run_id)}
              />
            )}

            <RunEventLog events={runEvents} />

            {selectedRun.status === "completed" && summary && (
              <div className="report-grid">
                <section className="kpi-strip">
                  <Kpi
                    label="Avis analysés"
                    value={String(summary.kpis.review_count)}
                    helper={`${summary.kpis.text_count ?? 0} verbatims`}
                  />
                  <Kpi
                    label="Note moyenne"
                    value={`${formatNumber(summary.kpis.average_rating)} / 5`}
                    helper={`Source ${SOURCE_LABELS[selectedRun.source]}`}
                  />
                  <Kpi
                    label="Confiance IA"
                    value={formatNumber(summary.kpis.average_confidence, 2)}
                    helper="Score moyen"
                  />
                  <Kpi
                    label="Réponses entreprise"
                    value={String(summary.kpis.responded_count ?? 0)}
                    helper="Avis avec réponse"
                  />
                </section>

                <DecisionPanel insights={summary.business_insights} />

                <TrendPanel
                  error={trendError}
                  isLoading={isTrendLoading}
                  trend={trend}
                />

                <section className="insight-section">
                  <div className="section-heading">
                    <h3>Sentiment global</h3>
                    <BarChart3 size={18} />
                  </div>
                  <SentimentBars rows={summary.sentiment_distribution} />
                </section>

                <section className="insight-section">
                  <div className="section-heading">
                    <h3>Répartition par note</h3>
                    <TableProperties size={18} />
                  </div>
                  <RatingBars rows={summary.rating_distribution} />
                </section>

                <section className="insight-section wide">
                  <div className="section-heading">
                    <h3>Irritants détectés</h3>
                    <AlertTriangle size={18} />
                  </div>
                  <TopicBars rows={summary.top_topics} />
                </section>

                <section className="insight-section">
                  <div className="section-heading">
                    <h3>Avis critiques</h3>
                    <AlertTriangle size={18} />
                  </div>
                  <ReviewCards reviews={summary.critical_reviews} />
                </section>

                <section className="insight-section">
                  <div className="section-heading">
                    <h3>Note vs texte</h3>
                    <CheckCircle2 size={18} />
                  </div>
                  <ReviewCards reviews={summary.rating_text_mismatches} />
                </section>

                <section className="insight-section wide">
                  <div className="section-heading table-heading">
                    <div>
                      <h3>Avis analysés</h3>
                      <p>
                        {formatReviewRange(reviewsOffset, reviews.length, reviewsTotal)} ·{" "}
                        {summary.kpis.feedback_count ?? 0} correction(s)
                      </p>
                    </div>
                    <div className="review-toolbar">
                      <div className="segmented" role="group" aria-label="Filtre sentiment">
                        {SENTIMENTS.map((sentiment) => (
                          <button
                            className={sentimentFilter === sentiment ? "active" : ""}
                            key={sentiment}
                            onClick={() => handleSentimentFilterChange(sentiment)}
                            type="button"
                          >
                            {sentiment}
                          </button>
                        ))}
                      </div>
                      <div className="pagination-controls" aria-label="Pagination des avis">
                        <label>
                          Par page
                          <select
                            value={reviewsLimit}
                            onChange={(event) =>
                              handleReviewsLimitChange(Number(event.target.value))
                            }
                          >
                            {REVIEW_PAGE_SIZES.map((pageSize) => (
                              <option key={pageSize} value={pageSize}>
                                {pageSize}
                              </option>
                            ))}
                          </select>
                        </label>
                        <button
                          disabled={!canGoToPreviousReviews}
                          onClick={handlePreviousReviewsPage}
                          type="button"
                        >
                          <ChevronLeft size={16} />
                          Précédent
                        </button>
                        <span>
                          Page {reviewsPage} / {reviewsPageCount}
                        </span>
                        <button
                          disabled={!canGoToNextReviews}
                          onClick={handleNextReviewsPage}
                          type="button"
                        >
                          Suivant
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </div>
                  <ReviewsTable
                    correctingReviewId={correctingReviewId}
                    onDeleteFeedback={handleDeleteReviewFeedback}
                    onSaveFeedback={handleSaveReviewFeedback}
                    reviews={reviews}
                  />
                </section>
              </div>
            )}
          </>
        )}
      </section>
    </main>
  );
}

function StatusBadge({ status }: { status: AnalysisRun["status"] }) {
  const labels: Record<AnalysisRun["status"], string> = {
    pending: "pending",
    running: "running",
    completed: "completed",
    failed: "failed",
    empty: "aucune donnee"
  };
  return <span className={`status-badge ${status}`}>{labels[status]}</span>;
}

function EmptyRunState({ message }: { message: string | null }) {
  return (
    <section className="empty-run-state">
      <AlertTriangle size={28} />
      <div>
        <h3>Aucun avis recupere</h3>
        <p>
          {message ||
            "Trustpilot n'a retourne aucun avis exploitable pour cette analyse. Essaie une URL plus precise, moins de filtres ou davantage de pages."}
        </p>
      </div>
    </section>
  );
}

function FailedRunState({
  errorMessage,
  isRetrying,
  onRetry
}: {
  errorMessage: string | null;
  isRetrying: boolean;
  onRetry: () => void;
}) {
  return (
    <section className="failed-state">
      <AlertTriangle size={28} />
      <div>
        <h3>Analyse échouée</h3>
        <p>
          {errorMessage?.trim() ||
            "Le worker n'a pas pu terminer cette analyse. Consulte le journal d'exécution pour identifier l'étape bloquante."}
        </p>
        <button
          className="secondary-action danger-action"
          disabled={isRetrying}
          onClick={onRetry}
          type="button"
        >
          {isRetrying ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
          {isRetrying ? "Relance en cours" : "Relancer l'analyse"}
        </button>
      </div>
    </section>
  );
}

function ReviewSourcesPanel({
  currentSource,
  error,
  isLoading,
  onRefresh,
  onSelectSource,
  sources
}: {
  currentSource: AnalysisSource;
  error: string | null;
  isLoading: boolean;
  onRefresh: () => void;
  onSelectSource: (sourceId: string) => void;
  sources: ReviewSource[];
}) {
  const activeSources = sources.filter(
    (source) => source.status === "active" && source.supports_analysis
  );
  const plannedSources = sources.filter((source) => source.status === "planned");

  return (
    <section className="sources-panel">
      <div className="panel-heading compact-heading">
        <div>
          <span>Sources d'avis</span>
          <small>{activeSources.length} active(s)</small>
        </div>
        <button
          className="icon-button"
          disabled={isLoading}
          onClick={onRefresh}
          title="Actualiser les sources"
          type="button"
        >
          {isLoading ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
        </button>
      </div>

      {error ? <p className="form-error">{error}</p> : null}

      <div className="source-card-list">
        {activeSources.map((source) => {
          const canSelect =
            source.status === "active" &&
            source.supports_analysis &&
            isAnalysisSource(source.source_id);
          const isSelected = source.source_id === currentSource;

          return (
            <button
              className={`source-card ${isSelected ? "selected" : ""}`}
              disabled={!canSelect}
              key={source.source_id}
              onClick={() => onSelectSource(source.source_id)}
              type="button"
            >
              <span className="source-card-icon">{sourceIcon(source.source_id)}</span>
              <span className="source-card-body">
                <strong>{source.label}</strong>
                <small>{source.category}</small>
                <span>{source.primary_action ?? "Connecteur a configurer"}</span>
              </span>
              <span
                className={
                  source.status === "active"
                    ? "source-status active"
                    : "source-status planned"
                }
              >
                {source.status === "active" ? "Actif" : "Bientot"}
              </span>
            </button>
          );
        })}
      </div>

      {plannedSources.length > 0 ? (
        <div className="sources-roadmap">
          <span>Prochains connecteurs</span>
          <div>
            {plannedSources.map((source) => (
              <small key={source.source_id}>{source.label}</small>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function ClientSpacePanel({
  currentUser,
  isCreatingUser,
  isLoadingUsers,
  message,
  newUserEmail,
  newUserFullName,
  newUserRole,
  onCreateUser,
  onRefreshUsers,
  onUpdateNewUserEmail,
  onUpdateNewUserFullName,
  onUpdateNewUserRole,
  users,
  usersError
}: {
  currentUser: CurrentUser;
  isCreatingUser: boolean;
  isLoadingUsers: boolean;
  message: string | null;
  newUserEmail: string;
  newUserFullName: string;
  newUserRole: UserRole;
  onCreateUser: (event: FormEvent<HTMLFormElement>) => void;
  onRefreshUsers: () => void;
  onUpdateNewUserEmail: (value: string) => void;
  onUpdateNewUserFullName: (value: string) => void;
  onUpdateNewUserRole: (value: UserRole) => void;
  users: OrganizationUser[];
  usersError: string | null;
}) {
  const isAdmin = currentUser.role === "admin";
  const activeUsers = users.filter((user) => user.account_status === "active");
  const pendingUsers = users.filter((user) => user.account_status === "pending");

  return (
    <section className="client-space-panel insight-section wide">
      <div className="section-heading client-space-heading">
        <div>
          <span className="eyebrow">Espace client</span>
          <h3>{currentUser.organization.name}</h3>
          <p>
            Gestion des membres rattaches a cette organisation. Les invitations
            creent un compte en attente a activer par lien.
          </p>
        </div>
        <button
          className="secondary-action"
          disabled={isLoadingUsers}
          onClick={onRefreshUsers}
          type="button"
        >
          {isLoadingUsers ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          Actualiser
        </button>
      </div>

      <div className="client-space-grid">
        <div className="client-card">
          <Building2 size={20} />
          <div>
            <span>Organisation</span>
            <strong>{currentUser.organization.name}</strong>
            <small>ID #{currentUser.organization.organization_id}</small>
          </div>
        </div>
        <div className="client-card">
          <Users size={20} />
          <div>
            <span>Membres</span>
            <strong>{users.length}</strong>
            <small>
              {activeUsers.length} actif(s), {pendingUsers.length} en attente
            </small>
          </div>
        </div>
        <div className="client-card">
          <CheckCircle2 size={20} />
          <div>
            <span>Session</span>
            <strong>{formatRole(currentUser.role)}</strong>
            <small>{currentUser.email}</small>
          </div>
        </div>
      </div>

      {usersError ? <p className="form-error">{usersError}</p> : null}
      {message ? <p className="form-success">{message}</p> : null}

      <div className="client-members-layout">
        <div className="client-members-list">
          <div className="mini-heading">
            <strong>Utilisateurs de l'organisation</strong>
            <span>{isLoadingUsers ? "Chargement..." : `${users.length} compte(s)`}</span>
          </div>
          {users.length === 0 && !isLoadingUsers ? (
            <p className="muted">Aucun utilisateur rattache pour le moment.</p>
          ) : (
            <div className="member-table">
              {users.map((user) => (
                <div className="member-row" key={user.user_id}>
                  <div>
                    <strong>{user.full_name || user.email}</strong>
                    <small>{user.email}</small>
                    {user.invitation_accept_url ? (
                      <a href={user.invitation_accept_url}>{user.invitation_accept_url}</a>
                    ) : null}
                  </div>
                  <RolePill role={user.role} />
                  <span className={`status-dot ${user.account_status}`}>
                    {formatAccountStatus(user.account_status)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <form className="client-user-form" onSubmit={onCreateUser}>
          <div className="mini-heading">
            <strong>Inviter un utilisateur</strong>
            <span>{isAdmin ? "Admin" : "Lecture seule"}</span>
          </div>
          <input
            disabled={!isAdmin || isCreatingUser}
            onChange={(event) => onUpdateNewUserEmail(event.target.value)}
            placeholder="email@entreprise.fr"
            type="email"
            value={newUserEmail}
          />
          <input
            disabled={!isAdmin || isCreatingUser}
            onChange={(event) => onUpdateNewUserFullName(event.target.value)}
            placeholder="Nom complet"
            type="text"
            value={newUserFullName}
          />
          <select
            disabled={!isAdmin || isCreatingUser}
            onChange={(event) => onUpdateNewUserRole(event.target.value as UserRole)}
            value={newUserRole}
          >
            <option value="member">Membre</option>
            <option value="admin">Admin</option>
          </select>
          <button
            className="primary-action compact-action"
            disabled={!isAdmin || isCreatingUser}
            type="submit"
          >
            {isCreatingUser ? <Loader2 className="spin" size={16} /> : <UserPlus size={16} />}
            Inviter
          </button>
          {!isAdmin ? (
            <p className="muted">Seuls les administrateurs peuvent inviter un membre.</p>
          ) : (
            <p className="muted">
              MVP local : copie le lien genere pour que le membre active son compte.
            </p>
          )}
        </form>
      </div>
    </section>
  );
}

function RolePill({ role }: { role: UserRole }) {
  return <span className={`role-pill ${role}`}>{formatRole(role)}</span>;
}

function formatRole(role: string) {
  return role === "admin" ? "Admin" : "Membre";
}

function formatAccountStatus(status: string) {
  const labels: Record<string, string> = {
    active: "Actif",
    pending: "Invite",
    inactive: "Inactif"
  };
  return labels[status] ?? status;
}

function AIQualityPanel({
  isLoading,
  onRefresh,
  quality
}: {
  isLoading: boolean;
  onRefresh: () => void;
  quality: FeedbackQuality | null;
}) {
  const hasCorrections = Boolean(quality && quality.total_corrections > 0);

  return (
    <section className="ai-quality-panel insight-section wide">
      <div className="section-heading ai-quality-heading">
        <div>
          <span className="eyebrow">Qualité IA</span>
          <h3>Boucle de correction humaine</h3>
          <p>
            {hasCorrections
              ? `${quality?.training_ready_count ?? 0} correction(s) prête(s) pour le prochain entraînement.`
              : "Aucune correction humaine enregistrée pour le moment."}
          </p>
        </div>
        <button
          className="secondary-action"
          disabled={isLoading}
          onClick={onRefresh}
          type="button"
        >
          {isLoading ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
          Actualiser
        </button>
      </div>

      {isLoading && !quality ? (
        <div className="loading-line">
          <Loader2 className="spin" size={18} />
          Chargement de la qualité IA...
        </div>
      ) : (
        <>
          <div className="ai-quality-kpis">
            <Kpi
              label="Corrections"
              value={String(quality?.total_corrections ?? 0)}
              helper={`${quality?.corrected_company_count ?? 0} entreprise(s)`}
            />
            <Kpi
              label="Labels modifiés"
              value={String(quality?.changed_label_count ?? 0)}
              helper={`${quality?.confirmed_label_count ?? 0} confirmation(s)`}
            />
            <Kpi
              label="Erreur apparente"
              value={formatPercent(quality?.apparent_error_rate ?? 0)}
              helper="Sur les avis corrigés"
            />
            <Kpi
              label="Prêt entraînement"
              value={String(quality?.training_ready_count ?? 0)}
              helper={quality?.latest_feedback_at ? formatDate(quality.latest_feedback_at) : "Aucune date"}
            />
          </div>

          {!hasCorrections ? (
            <p className="muted">
              Corrige quelques prédictions dans le tableau d'avis pour alimenter cette
              vue et le prochain dataset d'entraînement.
            </p>
          ) : (
            <div className="ai-quality-grid">
              <div className="quality-block">
                <h4>Entreprises corrigées</h4>
                <div className="quality-list">
                  {quality?.by_company.map((company) => (
                    <div className="quality-list-row" key={company.company_id}>
                      <div>
                        <strong>{company.company_name}</strong>
                        <small>
                          {company.run_count} run(s) · {company.changed_label_count} label(s)
                          modifié(s)
                        </small>
                      </div>
                      <span>{company.correction_count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="quality-block">
                <h4>Prédiction → correction</h4>
                <div className="transition-list">
                  {quality?.transitions.map((transition) => (
                    <div
                      className="transition-row"
                      key={`${transition.predicted_label}-${transition.corrected_label}`}
                    >
                      <SentimentPill label={transition.predicted_label} />
                      <span aria-hidden="true">→</span>
                      <SentimentPill label={transition.corrected_label} />
                      <strong>{transition.count}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="quality-block">
                <h4>Labels corrigés</h4>
                <div className="quality-list compact">
                  {quality?.corrected_label_distribution.map((row) => (
                    <div className="quality-list-row" key={row.label}>
                      <SentimentPill label={row.label} />
                      <span>{row.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="quality-block recent-corrections">
                <h4>Dernières corrections</h4>
                <div className="recent-correction-list">
                  {quality?.recent_corrections.map((correction) => (
                    <article className="recent-correction" key={correction.feedback_id}>
                      <div className="review-meta">
                        <span>{correction.company_name}</span>
                        <span>Run #{correction.run_id}</span>
                        <span>{formatDate(correction.feedback_updated_at)}</span>
                      </div>
                      <div className="transition-row compact">
                        <SentimentPill label={correction.predicted_label} />
                        <span aria-hidden="true">→</span>
                        <SentimentPill label={correction.corrected_label} />
                      </div>
                      <p>{compactText(correction.verbatim, 180)}</p>
                    </article>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ModelTrainingPanel({
  feedbackQuality,
  isLoading,
  isSubmitting,
  onRefresh,
  onStartTraining,
  overview
}: {
  feedbackQuality: FeedbackQuality | null;
  isLoading: boolean;
  isSubmitting: boolean;
  onRefresh: () => void;
  onStartTraining: () => void;
  overview: ModelTrainingOverview | null;
}) {
  const activeRun = overview?.active_run ?? null;
  const latestRun = overview?.latest_run ?? null;
  const productionModel = overview?.production_model ?? null;
  const hasActiveRun = Boolean(activeRun);
  const latestDuration = formatDuration(latestRun?.execution_duration_seconds);

  return (
    <section className="model-training-panel insight-section wide">
      <div className="section-heading model-training-heading">
        <div>
          <span className="eyebrow">Entrainement IA</span>
          <h3>Pilotage du modele de sentiment</h3>
          <p>
            Lance un reentrainement avec les corrections humaines et suis la
            version MLflow de production.
          </p>
        </div>
        <div className="header-actions">
          <button
            className="secondary-action"
            disabled={isLoading}
            onClick={onRefresh}
            type="button"
          >
            {isLoading ? <Loader2 className="spin" size={16} /> : <RefreshCw size={16} />}
            Actualiser
          </button>
          <button
            className="primary-action compact-action"
            disabled={isSubmitting || hasActiveRun}
            onClick={onStartTraining}
            type="button"
          >
            {isSubmitting || hasActiveRun ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <Play size={16} />
            )}
            {hasActiveRun ? "Entrainement en cours" : "Reentrainer"}
          </button>
        </div>
      </div>

      <div className="model-training-kpis">
        <Kpi
          label="Modele production"
          value={productionModel ? `v${productionModel.version}` : "Non detecte"}
          helper={productionModel?.model_uri ?? "Alias MLflow production"}
        />
        <Kpi
          label="Dernier entrainement"
          value={latestRun ? `#${latestRun.training_run_id}` : "Aucun"}
          helper={latestRun ? formatTrainingStatus(latestRun.status) : "Pas encore lance"}
        />
        <Kpi
          label="Accuracy"
          value={formatPercent((latestRun?.accuracy ?? 0) * 100)}
          helper={`Macro F1 ${formatPercent((latestRun?.macro_f1 ?? 0) * 100)}`}
        />
        <Kpi
          label="Corrections pretes"
          value={String(feedbackQuality?.training_ready_count ?? 0)}
          helper={`Poids x${formatNumber(latestRun?.feedback_sample_weight ?? 6, 1)}`}
        />
      </div>

      {activeRun && (
        <div className="training-active-state">
          <Hourglass size={22} />
          <div>
            <strong>Run d'entrainement #{activeRun.training_run_id}</strong>
            <p>
              Le worker Celery reentraine le modele. Cette zone se rafraichit
              automatiquement jusqu'a la fin du run.
            </p>
          </div>
          <TrainingStatusBadge status={activeRun.status} />
        </div>
      )}

      {latestRun?.status === "failed" && (
        <div className="training-error">
          <AlertTriangle size={18} />
          <span>{latestRun.error_message || "Le dernier entrainement a echoue."}</span>
        </div>
      )}

      <div className="training-history">
        <div className="training-history-heading">
          <h4>Historique des entrainements</h4>
          {latestDuration && <small>Derniere duree: {latestDuration}</small>}
        </div>

        {isLoading && !overview ? (
          <div className="loading-line">
            <Loader2 className="spin" size={18} />
            Chargement des entrainements...
          </div>
        ) : overview?.runs.length ? (
          <div className="training-run-list">
            {overview.runs.map((run) => (
              <div className="training-run-row" key={run.training_run_id}>
                <div>
                  <strong>Run #{run.training_run_id}</strong>
                  <small>{formatDate(run.created_at)}</small>
                </div>
                <TrainingStatusBadge status={run.status} />
                <span>{run.model_version ? `v${run.model_version}` : "-"}</span>
                <span>{formatPercent((run.accuracy ?? 0) * 100)}</span>
                <span>{run.training_feedback_rows} correction(s)</span>
                <span>{formatDuration(run.execution_duration_seconds) ?? "-"}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="muted">
            Aucun entrainement lance depuis l'interface pour le moment.
          </p>
        )}
      </div>
    </section>
  );
}

function TrainingStatusBadge({ status }: { status: ModelTrainingRun["status"] }) {
  return <span className={`status-badge ${status}`}>{formatTrainingStatus(status)}</span>;
}

function formatTrainingStatus(status: ModelTrainingRun["status"]) {
  const labels: Record<ModelTrainingRun["status"], string> = {
    pending: "pending",
    running: "running",
    completed: "completed",
    failed: "failed"
  };
  return labels[status];
}

function BenchmarkPanel({
  comparison,
  onClose,
  onExportReport
}: {
  comparison: RunsComparison;
  onClose: () => void;
  onExportReport: () => void;
}) {
  return (
    <section className="benchmark-report insight-section wide">
      <div className="section-heading benchmark-heading">
        <div>
          <span className="eyebrow">Benchmark concurrentiel</span>
          <h3>Comparaison multi-entreprises</h3>
          <p>
            {comparison.companies.length} entreprises comparées sur les runs{" "}
            {comparison.run_ids.join(", ")}.
          </p>
        </div>
        <div className="header-actions">
          <button className="secondary-action" onClick={onExportReport} type="button">
            <FileText size={16} />
            Rapport benchmark
          </button>
          <button className="icon-button" onClick={onClose} title="Fermer" type="button">
          ×
          </button>
        </div>
      </div>

      <div className="benchmark-highlight-grid">
        <BenchmarkHighlight
          label="Meilleur score santé"
          company={comparison.highlights.best_health}
          value={(company) => String(company.health_score)}
          helper={(company) => `Risque ${formatRisk(company.risk_level)}`}
        />
        <BenchmarkHighlight
          label="Plus gros risque"
          company={comparison.highlights.highest_negative_rate}
          value={(company) => formatPercent(company.negative_rate)}
          helper={(company) => `${company.negative_count} avis négatifs`}
        />
        <BenchmarkHighlight
          label="Plus gros volume"
          company={comparison.highlights.most_reviews}
          value={(company) => String(company.review_count)}
          helper={() => "avis analysés"}
        />
        <div className="benchmark-highlight">
          <span>Irritant partage</span>
          <strong>
            {comparison.highlights.shared_priority
              ? formatTopic(comparison.highlights.shared_priority.topic)
              : "Aucun"}
          </strong>
          <small>
            {comparison.highlights.shared_priority
              ? `${comparison.highlights.shared_priority.total_count} occurrences`
              : "Pas de sujet commun fort"}
          </small>
        </div>
      </div>

      <div className="benchmark-table-wrap">
        <table className="benchmark-table">
          <thead>
            <tr>
              <th>Entreprise</th>
              <th>Score santé</th>
              <th>Note moyenne</th>
              <th>Négatif</th>
              <th>Positif</th>
              <th>Irritants propres</th>
            </tr>
          </thead>
          <tbody>
            {comparison.companies.map((company) => (
              <tr key={company.run_id}>
                <td>
                  <strong>{company.company_name}</strong>
                  <small>Run #{company.run_id} - {company.review_count} avis</small>
                </td>
                <td>{company.health_score}</td>
                <td>{formatNumber(company.average_rating)} / 5</td>
                <td>{formatPercent(company.negative_rate)}</td>
                <td>{company.positive_count}</td>
                <td>
                  <BenchmarkTopicList topics={company.unique_topics} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="benchmark-common-topics">
        <h4>Irritants communs</h4>
        {comparison.common_topics.length === 0 ? (
          <p className="muted">Aucun irritant commun fort détecté.</p>
        ) : (
          <div className="compact-list">
            {comparison.common_topics.slice(0, 4).map((topic) => (
              <article className="compact-item" key={topic.topic}>
                <strong>{formatTopic(topic.topic)}</strong>
                <p>
                  {topic.total_count} occurrences dans {topic.run_count} runs.
                </p>
                <small>
                  {topic.companies
                    .map((company) => `${company.company_name}: ${company.count}`)
                    .join(" · ")}
                </small>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function BenchmarkHighlight({
  label,
  company,
  value,
  helper
}: {
  label: string;
  company: BenchmarkCompany | null;
  value: (company: BenchmarkCompany) => string;
  helper: (company: BenchmarkCompany) => string;
}) {
  return (
    <div className="benchmark-highlight">
      <span>{label}</span>
      <strong>{company ? value(company) : "-"}</strong>
      <small>{company ? `${company.company_name} · ${helper(company)}` : "Non disponible"}</small>
    </div>
  );
}

function BenchmarkTopicList({ topics }: { topics: BenchmarkCompany["unique_topics"] }) {
  if (topics.length === 0) {
    return <span className="muted">Aucun sujet spécifique</span>;
  }

  return (
    <div className="topic-tags">
      {topics.map((topic) => (
        <span key={topic.topic}>
          {formatTopic(topic.topic)} ({topic.count})
        </span>
      ))}
    </div>
  );
}

function TrendPanel({
  error,
  isLoading,
  trend
}: {
  error: string | null;
  isLoading: boolean;
  trend: AnalysisRunTrend | null;
}) {
  const topicGroups = [
    { title: "En hausse", rows: trend?.rising_topics ?? [], tone: "negative" },
    { title: "En baisse", rows: trend?.falling_topics ?? [], tone: "positive" },
    { title: "Nouveaux", rows: trend?.new_topics ?? [], tone: "warning" },
    { title: "Resolus", rows: trend?.resolved_topics ?? [], tone: "positive" }
  ];

  return (
    <section className="trend-panel insight-section wide">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Tendance</span>
          <h3>Evolution depuis la derniere analyse</h3>
        </div>
        <BarChart3 size={18} />
      </div>

      {isLoading ? (
        <div className="loading-line compact-loading">
          <Loader2 className="spin" size={18} />
          Calcul de la tendance...
        </div>
      ) : null}

      {error ? <p className="form-error">{error}</p> : null}

      {!isLoading && trend && !trend.has_previous ? (
        <div className="empty-inline-state">
          <strong>Pas encore de comparaison temporelle.</strong>
          <span>{trend.executive_summary}</span>
        </div>
      ) : null}

      {!isLoading && trend?.has_previous ? (
        <>
          <div className="trend-summary">
            <p>{trend.executive_summary}</p>
            <span>
              Comparaison avec run #{trend.previous_run?.run_id} du{" "}
              {formatDate(trend.previous_run?.created_at ?? null)}
            </span>
          </div>

          <div className="trend-metric-grid">
            {trend.metrics.map((metric) => (
              <article className={`trend-metric ${metric.direction}`} key={metric.metric}>
                <span>{metric.label}</span>
                <strong>{formatMetricValue(metric.current_value, metric.unit)}</strong>
                <small>
                  {formatSignedNumber(metric.delta)}
                  {metric.unit && metric.unit !== "score" ? ` ${metric.unit}` : ""}
                </small>
              </article>
            ))}
          </div>

          <div className="trend-sentiment-grid">
            {trend.sentiment.map((row) => {
              const tone = sentimentTrendTone(row);

              return (
                <article className={`trend-sentiment ${tone}`} key={row.label}>
                  <div>
                    <strong>{row.label}</strong>
                    <span>
                      {row.current_count} avis - {formatPercent(row.current_rate)}
                    </span>
                  </div>
                  <small>{formatSignedNumber(row.delta_rate)} pts</small>
                </article>
              );
            })}
          </div>

          <div className="trend-topic-grid">
            {topicGroups.map((group) => (
              <article className="trend-topic-card" key={group.title}>
                <h4>{group.title}</h4>
                {group.rows.length === 0 ? (
                  <span className="muted">Aucun signal.</span>
                ) : (
                  <div className="topic-tags trend-tags">
                    {group.rows.slice(0, 4).map((topic) => (
                      <span className={group.tone} key={topic.topic}>
                        {formatTopic(topic.topic)} ({formatSignedNumber(topic.delta_count, 0)})
                      </span>
                    ))}
                  </div>
                )}
              </article>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function DecisionPanel({ insights }: { insights: BusinessInsights }) {
  return (
    <section className="decision-panel insight-section wide">
      <div className="decision-header">
        <div>
          <span className="eyebrow">Synthèse décisionnelle</span>
          <h3>Priorités recommandées</h3>
          <p>{insights.executive_summary}</p>
        </div>
        <div className={`health-meter risk-${insights.risk_level}`}>
          <span>Score santé</span>
          <strong>{insights.health_score}</strong>
          <small>Risque {formatRisk(insights.risk_level)}</small>
        </div>
      </div>

      <div className="decision-grid">
        <div className="decision-block priority-block">
          <div className="mini-heading">
            <AlertTriangle size={16} />
            <h4>À traiter en premier</h4>
          </div>
          {insights.priorities.length === 0 ? (
            <p className="muted">Aucune priorité critique détectée.</p>
          ) : (
            <div className="priority-list">
              {insights.priorities.slice(0, 3).map((priority) => (
                <PriorityItem key={priority.topic} priority={priority} />
              ))}
            </div>
          )}
        </div>

        <div className="decision-block">
          <div className="mini-heading">
            <CheckCircle2 size={16} />
            <h4>Actions suivantes</h4>
          </div>
          <ol className="action-list">
            {insights.next_actions.map((action) => (
              <li key={action}>{action}</li>
            ))}
          </ol>
        </div>

        <div className="decision-block">
          <div className="mini-heading">
            <BarChart3 size={16} />
            <h4>Forces à préserver</h4>
          </div>
          <StrengthList strengths={insights.strengths} />
        </div>

        <div className="decision-block">
          <div className="mini-heading">
            <ListChecks size={16} />
            <h4>Points de vigilance</h4>
          </div>
          <WatchpointList watchpoints={insights.watchpoints} />
        </div>
      </div>
    </section>
  );
}

function PriorityItem({ priority }: { priority: BusinessPriority }) {
  return (
    <article className="priority-item">
      <div className="priority-topline">
        <span>#{priority.rank}</span>
        <strong>{priority.title}</strong>
        <em className={`severity severity-${priority.severity}`}>
          {formatSeverity(priority.severity)}
        </em>
      </div>
      <p>{priority.impact}</p>
      <p className="recommendation">{priority.recommendation}</p>
      <div className="priority-meta">
        <span>{priority.negative_reviews} avis négatifs</span>
        <span>{formatNumber(priority.share_of_reviews, 1)} % du corpus</span>
      </div>
      {priority.examples.length > 0 && (
        <blockquote>{compactText(priority.examples[0].verbatim, 180)}</blockquote>
      )}
    </article>
  );
}

function StrengthList({ strengths }: { strengths: BusinessStrength[] }) {
  if (strengths.length === 0) {
    return <p className="muted">Aucun point fort isolé pour le moment.</p>;
  }

  return (
    <div className="compact-list">
      {strengths.map((strength) => (
        <article key={strength.topic}>
          <strong>{strength.title}</strong>
          <span>{strength.positive_reviews} avis positifs</span>
          <p>{strength.recommendation}</p>
        </article>
      ))}
    </div>
  );
}

function WatchpointList({ watchpoints }: { watchpoints: BusinessWatchpoint[] }) {
  if (watchpoints.length === 0) {
    return <p className="muted">Aucun signal faible majeur.</p>;
  }

  return (
    <div className="compact-list">
      {watchpoints.map((watchpoint) => (
        <article className={`watchpoint ${watchpoint.level}`} key={watchpoint.title}>
          <strong>{watchpoint.title}</strong>
          <p>{watchpoint.message}</p>
        </article>
      ))}
    </div>
  );
}

const eventStepLabels: Record<string, string> = {
  queued: "File d'attente",
  worker_start: "Worker",
  prepare_outputs: "Preparation",
  scrape_start: "Scraping",
  scrape_star: "Scraping",
  scrape_page: "Page",
  scrape_page_empty: "Page vide",
  scrape_page_error: "Erreur page",
  scrape_output: "JSON",
  scrape_complete: "Scraping",
  scrape_skipped: "JSON existant",
  load_reviews: "Chargement",
  predict: "Prediction",
  persist_reviews: "Sauvegarde",
  export: "Export",
  completed: "Termine",
  failed: "Echec"
};

function RunEventLog({ events }: { events: AnalysisRunEvent[] }) {
  return (
    <section className="execution-log">
      <div className="section-heading">
        <h3>Journal d'execution</h3>
        <ListChecks size={18} />
      </div>

      {events.length === 0 ? (
        <p className="muted">Aucun evenement pour le moment.</p>
      ) : (
        <ol className="event-list">
          {events.map((event) => (
            <li className={`event-item ${event.level}`} key={event.event_id}>
              <span className="event-dot" aria-hidden="true" />
              <div>
                <div className="event-meta">
                  <strong>
                    {event.step
                      ? eventStepLabels[event.step] ?? event.step.replaceAll("_", " ")
                      : "Evenement"}
                  </strong>
                  <span>{formatDate(event.created_at)}</span>
                </div>
                <p>{event.message}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Kpi({
  label,
  value,
  helper
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="kpi">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </div>
  );
}

function SentimentBars({ rows }: { rows: DistributionRow<SentimentLabel>[] }) {
  const total = rows.reduce((sum, row) => sum + row.count, 0) || 1;
  return (
    <div className="bar-list">
      {(["Négatif", "Neutre", "Positif"] as SentimentLabel[]).map((label) => {
        const count = getDistributionCount(rows, label);
        return (
          <BarRow
            key={label}
            label={label}
            count={count}
            total={total}
            className={sentimentClass[label]}
          />
        );
      })}
    </div>
  );
}

function RatingBars({ rows }: { rows: DistributionRow<number>[] }) {
  const total = rows.reduce((sum, row) => sum + row.count, 0) || 1;
  return (
    <div className="bar-list">
      {[1, 2, 3, 4, 5].map((rating) => (
        <BarRow
          key={rating}
          label={`${rating} étoile${rating > 1 ? "s" : ""}`}
          count={getDistributionCount(rows, rating)}
          total={total}
          className="rating"
        />
      ))}
    </div>
  );
}

function TopicBars({ rows }: { rows: DistributionRow[] }) {
  const total = Math.max(...rows.map((row) => row.count), 1);
  if (rows.length === 0) {
    return <p className="muted">Aucun irritant détecté.</p>;
  }
  return (
    <div className="topic-grid">
      {rows.map((row) => (
        <BarRow
          key={row.topic}
          label={row.topic?.replaceAll("_", " ") ?? "Sujet"}
          count={row.count}
          total={total}
          className="topic"
        />
      ))}
    </div>
  );
}

function BarRow({
  label,
  count,
  total,
  className
}: {
  label: string;
  count: number;
  total: number;
  className: string;
}) {
  const width = Math.max((count / total) * 100, count > 0 ? 4 : 0);
  return (
    <div className="bar-row">
      <div className="bar-label">
        <span>{label}</span>
        <strong>{count}</strong>
      </div>
      <div className="bar-track" aria-hidden="true">
        <div className={`bar-fill ${className}`} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function ReviewCards({ reviews }: { reviews: SummaryReview[] }) {
  if (reviews.length === 0) {
    return <p className="muted">Aucun cas détecté.</p>;
  }

  return (
    <div className="review-card-list">
      {reviews.slice(0, 4).map((review) => (
        <article className="review-card" key={review.review_id}>
          <div className="review-meta">
            <span>#{review.review_id}</span>
            <span>{review.rating ?? "-"} / 5</span>
            <SentimentPill label={review.sentiment_label} />
          </div>
          <p>{compactText(review.verbatim)}</p>
        </article>
      ))}
    </div>
  );
}

function ReviewsTable({
  correctingReviewId,
  onDeleteFeedback,
  onSaveFeedback,
  reviews
}: {
  correctingReviewId: number | null;
  onDeleteFeedback: (reviewId: number) => void;
  onSaveFeedback: (reviewId: number, label: SentimentLabel) => void;
  reviews: Review[];
}) {
  if (reviews.length === 0) {
    return <p className="muted">Aucun avis pour ce filtre.</p>;
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Note</th>
            <th>Sentiment</th>
            <th>Correction</th>
            <th>Score</th>
            <th>Irritants</th>
            <th>Verbatim</th>
          </tr>
        </thead>
        <tbody>
          {reviews.map((review) => (
            <tr key={review.review_id}>
              <td>{review.review_id}</td>
              <td>{review.rating ?? "-"}</td>
              <td>
                <SentimentPill label={review.sentiment_label} />
              </td>
              <td>
                <div className="feedback-cell">
                  {review.corrected_label ? (
                    <span className="feedback-status corrected">
                      Corrigé en {review.corrected_label}
                    </span>
                  ) : (
                    <span className="feedback-status">Non corrigé</span>
                  )}
                  <div className="feedback-actions">
                    {FEEDBACK_SENTIMENTS.map((sentiment) => (
                      <button
                        className={
                          review.corrected_label === sentiment ? "active" : ""
                        }
                        disabled={correctingReviewId === review.review_id}
                        key={sentiment}
                        onClick={() => onSaveFeedback(review.review_id, sentiment)}
                        type="button"
                      >
                        {sentiment}
                      </button>
                    ))}
                    <button
                      className="remove-feedback"
                      disabled={
                        !review.corrected_label ||
                        correctingReviewId === review.review_id
                      }
                      onClick={() => onDeleteFeedback(review.review_id)}
                      type="button"
                    >
                      Retirer
                    </button>
                  </div>
                </div>
              </td>
              <td>{formatNumber(review.sentiment_score, 2)}</td>
              <td>
                <div className="topic-tags">
                  {review.topics.length === 0
                    ? "-"
                    : review.topics.slice(0, 3).map((topic) => (
                        <span key={topic}>{topic.replaceAll("_", " ")}</span>
                      ))}
                </div>
              </td>
              <td className="review-verbatim">
                {(review.verbatim ?? "").trim() || "Avis sans verbatim"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SentimentPill({ label }: { label: SentimentLabel }) {
  return <span className={`sentiment-pill ${sentimentClass[label]}`}>{label}</span>;
}
