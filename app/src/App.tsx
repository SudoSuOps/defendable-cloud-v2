import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import { Shell } from "./components/Shell";
import { Spinner } from "./components/ui";
import { Login } from "./pages/Login";
import { AuthCallback } from "./pages/AuthCallback";
import { Landing } from "./pages/Landing";
import { Verify } from "./pages/Verify";
import { Dashboard } from "./pages/Dashboard";
import { NewRun } from "./pages/NewRun";
import { RunDetail } from "./pages/RunDetail";
import { Datasets } from "./pages/Datasets";
import { AgentProfiles, AgentProfileDetail } from "./pages/AgentProfiles";
import { StackPlanner } from "./pages/StackPlanner";
import { Incidents } from "./pages/Incidents";
import { Org } from "./pages/Org";
import { ShareView } from "./pages/ShareView";
import { NotFound } from "./pages/NotFound";

function Protected({ children }: { children: React.ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Opening the vault…" />
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

// Public landing for unauth visitors; signed-in workspace for the rest.
function Home() {
  const { me, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Spinner label="Opening the vault…" />
      </div>
    );
  }
  if (!me) return <Landing />;
  return (
    <Shell>
      <Dashboard />
    </Shell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/verify" element={<Verify />} />
        <Route path="/r/:token" element={<ShareView />} />
        <Route path="/" element={<Home />} />
        <Route path="/runs/new" element={<Protected><NewRun /></Protected>} />
        <Route path="/runs/:id" element={<Protected><RunDetail /></Protected>} />
        <Route path="/plan" element={<Protected><StackPlanner /></Protected>} />
        <Route path="/agents" element={<Protected><AgentProfiles /></Protected>} />
        <Route path="/agents/:id" element={<Protected><AgentProfileDetail /></Protected>} />
        <Route path="/incidents" element={<Protected><Incidents /></Protected>} />
        <Route path="/datasets" element={<Protected><Datasets /></Protected>} />
        <Route path="/org" element={<Protected><Org /></Protected>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </AuthProvider>
  );
}
