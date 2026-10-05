import { Link, Navigate, Route, Routes } from "react-router-dom";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectLayout from "./pages/ProjectLayout";
import OverviewPage from "./pages/OverviewPage";
import PartsPage from "./pages/PartsPage";

export default function App() {
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          Product Workbench
        </Link>
      </header>
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="parts" element={<PartsPage />} />
        </Route>
      </Routes>
    </div>
  );
}
