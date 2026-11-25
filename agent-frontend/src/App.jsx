import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  Outlet,
} from "react-router-dom";

import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import TicketList from "./pages/TicketList";
import TicketDetails from "./pages/TicketDetails";
import Conversations from "./pages/Conversations";
import HistoricalSolutions from "./pages/HistoricalSolutions";
import HistoricalSolutionAttempts from "./pages/HistoricalSolutionAttempts";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

import "./index.css";

function AgentLayout() {
  const agent = sessionStorage.getItem("agent");

  if (!agent) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-section">
        <Header />
        <main className="page-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        <Route path="/" element={<AgentLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="tickets" element={<TicketList />} />
          <Route path="tickets/:ticketId" element={<TicketDetails />} />
          <Route path="conversations" element={<Conversations />} />
          <Route path="historical-solutions" element={<HistoricalSolutions />} />
          <Route path="historical-solution-attempts" element={<HistoricalSolutionAttempts />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
