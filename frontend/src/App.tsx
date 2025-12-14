/**
 * Main App component with React Router.
 */
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { UIProvider } from "./context/UIContext";

import { MainLayout } from "./layouts/MainLayout";
import { ChatsPage } from "./pages/ChatsPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProjectDetailPage } from "./pages/ProjectDetailPage";
import { ChatViewPage } from "./pages/ChatViewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { LoadingSpinner } from "./components/LoadingSpinner";

// Query client for TanStack Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60, // 1 minute
      refetchOnWindowFocus: false,
    },
  },
});

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <LoadingSpinner fullScreen />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Auth route wrapper with navigation
function AuthRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();

  if (user) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

// Login route with callbacks
function LoginRoute() {
  const navigate = useNavigate();

  return (
    <LoginPage
      onSwitchToRegister={() => navigate("/register")}
      onForgotPassword={() => alert("Password reset coming soon")}
      onSuccess={() => navigate("/")}
    />
  );
}

// Register route with callbacks
function RegisterRoute() {
  const navigate = useNavigate();

  return (
    <RegisterPage
      onSwitchToLogin={() => navigate("/login")}
      onSuccess={() => navigate("/")}
    />
  );
}

// App routes
function AppRoutes() {
  return (
    <Routes>
      {/* Auth routes */}
      <Route
        path="/login"
        element={
          <AuthRoute>
            <LoginRoute />
          </AuthRoute>
        }
      />
      <Route
        path="/register"
        element={
          <AuthRoute>
            <RegisterRoute />
          </AuthRoute>
        }
      />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ChatsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ProjectsPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ProjectDetailPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat/:id"
        element={
          <ProtectedRoute>
            <MainLayout>
              <ChatViewPage />
            </MainLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <MainLayout>
              <SettingsPage onClose={() => window.history.back()} />
            </MainLayout>
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider>
          <AuthProvider>
            <UIProvider>
              <AppRoutes />
            </UIProvider>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
