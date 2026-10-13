import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectLayout from "./pages/ProjectLayout";
import OverviewPage from "./pages/OverviewPage";
import PartsPage from "./pages/PartsPage";
import CadPage from "./pages/CadPage";
import EngineeringPage from "./pages/EngineeringPage";
import BomPage from "./pages/BomPage";
import ManufacturingPage from "./pages/ManufacturingPage";
import CostDownPage from "./pages/CostDownPage";
import FactoryPackPage from "./pages/FactoryPackPage";
import DfmPage from "./pages/DfmPage";
import RevisionsPage from "./pages/RevisionsPage";
import RevisionView from "./pages/RevisionView";
import StandardPartsPage, { ConceptsView, LibraryView, MyConceptsView } from "./pages/StandardPartsPage";
import ConceptBuilder from "./pages/ConceptBuilder";
import { STALE_MESSAGE, useServerStale } from "./components/useServerStale";

export default function App() {
  const stale = useServerStale();
  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          Product Workbench
        </Link>
        <nav className="topnav">
          <NavLink to="/" end>
            Projects
          </NavLink>
          <NavLink to="/standard-parts">Standard Parts</NavLink>
        </nav>
      </header>
      {stale && (
        <p className="notice stale-server" role="alert">
          <strong>Restart needed.</strong> {STALE_MESSAGE}
        </p>
      )}
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
        <Route path="/projects/:projectId" element={<ProjectLayout />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="parts" element={<PartsPage />} />
          <Route path="cad" element={<CadPage />} />
          <Route path="engineering" element={<EngineeringPage />} />
          <Route path="bom" element={<BomPage />} />
          <Route path="manufacturing" element={<ManufacturingPage />} />
          <Route path="cost-down" element={<CostDownPage />} />
          <Route path="dfm" element={<DfmPage />} />
          <Route path="factory-pack" element={<FactoryPackPage />} />
          <Route path="revisions" element={<RevisionsPage />} />
          <Route path="revisions/:number" element={<RevisionView />} />
        </Route>
        <Route path="/standard-parts" element={<StandardPartsPage />}>
          <Route index element={<Navigate to="library" replace />} />
          <Route path="library" element={<LibraryView />} />
          <Route path="concepts" element={<ConceptsView />} />
          <Route path="mine" element={<MyConceptsView />} />
          <Route path="mine/:conceptId" element={<ConceptBuilder />} />
        </Route>
      </Routes>
    </div>
  );
}
