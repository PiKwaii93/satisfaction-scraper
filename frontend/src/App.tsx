import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Download,
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
  exportReviews,
  getReviews,
  getRunEvents,
  getSummary,
  listRuns
} from "./api";
import type {
  AnalysisRunEvent,
  AnalysisRun,
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

function getDistributionCount<T extends string | number>(
  rows: DistributionRow<T>[],
  key: T
) {
  const row = rows.find((item) => item.label === key || item.rating === key);
  return row?.count ?? 0;
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
    setIsSubmitting(true);
    setError(null);

    try {
      const run = await createRun({
        company,
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
                <button
                  className="secondary-action"
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

            <RunEventLog events={runEvents} />

            {summary && (
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
