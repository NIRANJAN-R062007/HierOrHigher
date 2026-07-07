import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

/** Gate for authenticated pages: waits for the session, else → /login. */
export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-paper-50">
        <p className="animate-pulse-dot text-sm font-medium text-ink-500">
          Loading your session…
        </p>
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
