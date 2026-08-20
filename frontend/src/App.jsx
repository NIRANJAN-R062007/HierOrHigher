import { Route, Routes, useLocation } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import Analytics from "./pages/Analytics";
import Apply from "./pages/Apply";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import PostingScreening from "./pages/PostingScreening";
import Recruiter from "./pages/Recruiter";
import Signup from "./pages/Signup";

export default function App() {
  const location = useLocation();

  return (
    <AuthProvider>
      {/* Keyed on path: a subtle fade eases the marketing ↔ app transition. */}
      <div key={location.pathname} className="animate-page-in">
        <Routes location={location}>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analytics"
            element={
              <ProtectedRoute>
                <Analytics />
              </ProtectedRoute>
            }
          />
          {/* Recruiter side: gated like any other app page. */}
          <Route
            path="/hiring"
            element={
              <ProtectedRoute>
                <Recruiter />
              </ProtectedRoute>
            }
          />
          <Route
            path="/hiring/postings/:postingId"
            element={
              <ProtectedRoute>
                <PostingScreening />
              </ProtectedRoute>
            }
          />
          {/* The one public app route: a candidate applies with no account,
              so it must sit OUTSIDE ProtectedRoute. */}
          <Route path="/apply/:postingId" element={<Apply />} />
          <Route path="*" element={<Landing />} />
        </Routes>
      </div>
    </AuthProvider>
  );
}
