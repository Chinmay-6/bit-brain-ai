import { NavLink, Route, Routes } from "react-router-dom";
import Overview from "./pages/Overview.jsx";
import AlertQueue from "./pages/AlertQueue.jsx";
import CaseView from "./pages/CaseView.jsx";
import DatasetUpload from "./pages/DatasetUpload.jsx";
import TransactionSearch from "./pages/TransactionSearch.jsx";
import OfflineStatus from "./components/OfflineStatus.jsx";
import AlertCenter from "./components/AlertCenter.jsx";

function NavItem({ to, children }) {
  return (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
          isActive
            ? "bg-canvas-panel text-accent border border-accent/20"
            : "text-slate-400 hover:text-slate-200 hover:bg-canvas-panel/60"
        }`
      }
    >
      {children}
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col text-slate-200">
      <header className="no-print border-b border-canvas-border px-6 py-3 flex items-center gap-6 sticky top-0 bg-canvas/95 backdrop-blur z-10">
        <div className="font-bold text-lg tracking-tight font-mono flex items-center gap-2">
          <span className="w-2 h-2 rounded-sm bg-accent" />
          BIT-BRAIN <span className="text-accent">AI</span>
        </div>
        <nav className="flex gap-1">
          <NavItem to="/">Overview</NavItem>
          <NavItem to="/alerts">Alert Queue</NavItem>
          <NavItem to="/search">Transaction Search</NavItem>
          <NavItem to="/upload">Upload Dataset</NavItem>
        </nav>
        <div className="ml-auto flex items-center gap-4">
          <AlertCenter />
          <OfflineStatus />
        </div>
      </header>
      <main className="flex-1 px-6 py-6 max-w-[1600px] w-full mx-auto">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/alerts" element={<AlertQueue />} />
          <Route path="/case/:entityId" element={<CaseView />} />
          <Route path="/search" element={<TransactionSearch />} />
          <Route path="/upload" element={<DatasetUpload />} />
        </Routes>
      </main>
    </div>
  );
}
