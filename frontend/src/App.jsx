import { Route, Routes, useLocation } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Masterclass from "./pages/Masterclass";
import Signup from "./pages/Signup";

export default function App() {
  const location = useLocation();

  return (
    <AuthProvider>
      {/* Keyed on path: a subtle fade eases the marketing ↔ app transition. */}
      <div key={location.pathname} className="animate-page-in">
        <Routes location={location}>
          <Route path="/" element={<Landing />} />
          <Route path="/masterclass" element={<Masterclass />} />
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
          <Route path="*" element={<Landing />} />
        </Routes>
      </div>
    </AuthProvider>
  );
}
