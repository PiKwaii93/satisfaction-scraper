import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Download,
  FileText,
  Hourglass,
  ListChecks,
  Loader2,
  Play,
  RefreshCw,
  Search,
  TableProperties
} from "lucide-react";
import {
  createRun,
  executeRun,
  exportReviews,
  getReviews,
  getRunEvents,
  getSummary,
  listRuns
} from "./api";
import type {
  AnalysisRunEvent,
  AnalysisRun,
  BusinessInsights,
  BusinessPriority,
  BusinessStrength,
  BusinessWatchpoint,
  DistributionRow,
  Review,
  RunSummary,
  SentimentLabel,
  SummaryReview
} from "./types";

const SENTIMENTS: Array<SentimentLabel | "Tous"> = [
  "Tous",
  "Négatif",
  "Neutre",
  "Positif"
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

function reportFileName(run: AnalysisRun) {
  const slug = run.company_name.replace(/[^a-zA-Z0-9_-]+/g, "_").replace(/^_+|_+$/g, "");
  return `rapport_${slug || "analyse"}_run_${run.run_id}.pdf`;
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
          <p><strong>Action recommandee :</strong> ${escapeHtml(priority.recommendation)}</p>
          <p class="meta">${priority.negative_reviews} avis negatifs - ${formatPercent(priority.share_of_reviews)} du corpus</p>
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
          <td>${escapeHtml(topic.topic?.replaceAll("_", " ") ?? "Sujet")}</td>
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
        <p>Trustpilot - Run #${run.run_id} - Rapport genere le ${escapeHtml(createdAt)}</p>
      </div>
      <div class="score">
        <span>Score sante</span>
        <strong>${insights.health_score}</strong>
        <span>Risque ${escapeHtml(formatRisk(insights.risk_level))}</span>
      </div>
    </header>

    <section>
      <h2>Synthese executive</h2>
      <p>${escapeHtml(insights.executive_summary)}</p>
    </section>

    <section class="grid">
      <div class="kpi"><span>Avis analyses</span><strong>${summary.kpis.review_count}</strong></div>
      <div class="kpi"><span>Note moyenne</span><strong>${formatNumber(summary.kpis.average_rating)} / 5</strong></div>
      <div class="kpi"><span>Confiance IA</span><strong>${formatNumber(summary.kpis.average_confidence, 2)}</strong></div>
      <div class="kpi"><span>Reponses entreprise</span><strong>${summary.kpis.responded_count ?? 0}</strong></div>
    </section>

    <section>
      <h2>Priorites recommandees</h2>
      <div class="priority-list">${priorities || "<p>Aucune priorite critique detectee.</p>"}</div>
    </section>

    <section class="two-cols">
      <div class="box">
        <h2>Actions suivantes</h2>
        <ol>${actions}</ol>
      </div>
      <div class="box">
        <h2>Forces a preserver</h2>
        <ul>${strengths || "<li>Aucun point fort isole pour le moment.</li>"}</ul>
      </div>
    </section>

    <section class="two-cols">
      <div class="box">
        <h2>Sentiment global</h2>
        <table>
          <tbody>
            ${distributionRows(summary.sentiment_distribution, [
              { label: "Negatif", key: "Négatif" as SentimentLabel },
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
          <tbody>${topics || "<tr><td>Aucun irritant detecte</td><td>0</td></tr>"}</tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Avis critiques representatifs</h2>
      <div class="review-list">${criticalReviews || "<p>Aucun avis critique detecte.</p>"}</div>
    </section>

    <section>
      <h2>Cas note vs texte</h2>
      <div class="review-list">${mismatches || "<p>Aucun ecart note / texte detecte.</p>"}</div>
    </section>

    <section class="box">
      <h2>Points de vigilance</h2>
      <ul>${watchpoints || "<li>Aucun signal faible majeur.</li>"}</ul>
    </section>

    <section class="limits">
      <h2>Limites de lecture</h2>
      <p>Ce rapport repose sur les avis collectes lors du run, les verbatims disponibles et le modele de sentiment actuellement deploye. Les recommandations doivent etre relues avec le contexte metier avant arbitrage operationnel.</p>
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
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [summary, setSummary] = useState<RunSummary | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [runEvents, setRunEvents] = useState<AnalysisRunEvent[]>([]);
  const [sentimentFilter, setSentimentFilter] =
    useState<SentimentLabel | "Tous">("Tous");
  const [company, setCompany] = useState(
    "https://fr.trustpilot.com/review/www.darty.com"
  );
  const [pagesPerStar, setPagesPerStar] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryingRunId, setRetryingRunId] = useState<number | null>(null);
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

  useEffect(() => {
    refreshRuns()
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

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

  const selectedRun = useMemo(
    () => runs.find((run) => run.run_id === selectedRunId) ?? null,
    [runs, selectedRunId]
  );

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
    if (!selectedRunId || !selectedRun) {
      setSummary(null);
      setReviews([]);
      return;
    }

    if (selectedRun.status === "pending" || selectedRun.status === "running") {
      setSummary(null);
      setReviews([]);
      return;
    }

    if (selectedRun.status === "failed") {
      setSummary(null);
      setReviews([]);
      setIsSummaryLoading(false);
      return;
    }

    setIsSummaryLoading(true);
    setError(null);

    Promise.all([
      getSummary(selectedRunId),
      getReviews(selectedRunId, sentimentFilter)
    ])
      .then(([nextSummary, nextReviews]) => {
        setSummary(nextSummary);
        setReviews(nextReviews.reviews);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setIsSummaryLoading(false));
  }, [selectedRunId, selectedRun?.status, sentimentFilter]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validationError = validateCompanyInput(company);
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const run = await createRun({
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

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">SC</div>
          <div>
            <h1>Satisfaction Client</h1>
            <p>Analyse d'avis Trustpilot</p>
          </div>
        </div>

        <form className="analysis-form" onSubmit={handleSubmit}>
          <label htmlFor="company">Entreprise ou URL Trustpilot</label>
          <div className="input-with-icon">
            <Search aria-hidden="true" size={18} />
            <input
              id="company"
              value={company}
              onChange={(event) => setCompany(event.target.value)}
              placeholder="www.darty.com"
              disabled={isSubmitting}
            />
          </div>

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

          <button className="primary-action" disabled={isSubmitting}>
            {isSubmitting ? (
              <Loader2 className="spin" size={18} />
            ) : (
              <Play size={18} />
            )}
            {isSubmitting ? "Analyse en cours" : "Lancer l'analyse"}
          </button>
        </form>

        <div className="run-panel">
          <div className="panel-heading">
            <h2>Historique</h2>
            <button
              className="icon-button"
              onClick={() => refreshRuns(true)}
              title="Rafraichir les analyses"
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
      </aside>

      <section className="workspace">
        {error && (
          <div className="alert" role="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

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
                  Trustpilot - Run #{selectedRun.run_id} -{" "}
                  {selectedRun.total_reviews} avis
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
                </div>
              </div>
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
                    helper="Source Trustpilot"
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
                      <p>{reviews.length} avis affichés</p>
                    </div>
                    <div className="segmented" role="group" aria-label="Filtre sentiment">
                      {SENTIMENTS.map((sentiment) => (
                        <button
                          className={sentimentFilter === sentiment ? "active" : ""}
                          key={sentiment}
                          onClick={() => setSentimentFilter(sentiment)}
                          type="button"
                        >
                          {sentiment}
                        </button>
                      ))}
                    </div>
                  </div>
                  <ReviewsTable reviews={reviews} />
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
  return <span className={`status-badge ${status}`}>{status}</span>;
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

function ReviewsTable({ reviews }: { reviews: Review[] }) {
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
              <td>{compactText(review.verbatim, 190)}</td>
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
