import { ToastProvider } from "./components/Toast";
import { useRoute } from "./hooks/useRoute";
import { buildHash } from "./lib/route";
import { BuilderPage } from "./pages/BuilderPage";
import { ExamPage } from "./pages/ExamPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LibraryPage } from "./pages/LibraryPage";
import { ResultPage } from "./pages/ResultPage";
import { ReviewPage } from "./pages/ReviewPage";

export function App() {
  const route = useRoute();
  const inExam = route.name === "exam";
  const link = (label: string, hash: string, active: boolean) => (
    <a href={hash} className={active ? "is-active" : ""} aria-current={active ? "page" : undefined}>{label}</a>
  );
  return (
    <ToastProvider>
      <div className="app">
        <header className="topbar">
          <a className="brand" href={buildHash("library")}>GOTCHA</a>
          {!inExam && (
            <nav aria-label="Principal">
              {link("Biblioteca", buildHash("library"), route.name === "library" || route.name === "batch")}
              {link("Novo simulado", buildHash("simulado", "new"), route.name === "simulado")}
              {link("Histórico", buildHash("history"), route.name === "history" || route.name === "result")}
            </nav>
          )}
        </header>
        <main className="container">
          {route.name === "library" && <LibraryPage />}
          {route.name === "batch" && route.id && <ReviewPage id={route.id} />}
          {route.name === "simulado" && <BuilderPage preselected={route.query.exam} />}
          {route.name === "exam" && route.id && <ExamPage key={route.id} id={route.id} />}
          {route.name === "result" && route.id && <ResultPage id={route.id} />}
          {route.name === "history" && <HistoryPage />}
        </main>
      </div>
    </ToastProvider>
  );
}
