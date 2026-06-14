import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";

import { Layout } from "@/components/layout/Layout";
import { SettingsLayout } from "@/components/layout/SettingsLayout";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { LoginPage } from "@/pages/auth/Login";
import { RegisterPage } from "@/pages/auth/Register";
import { DashboardPage } from "@/pages/Dashboard";
import { ProspectsPage } from "@/pages/Prospects";
import { ProspectDetailPage } from "@/pages/ProspectDetail";
import { PipelinePage } from "@/pages/Pipeline";
import { ScoutPage } from "@/pages/Scout";
import { OutreachPage } from "@/pages/Outreach";
import SequencesPage from "@/pages/Sequences";
import { AnalyticsPage } from "@/pages/Analytics";
import { NotFoundPage } from "@/pages/NotFound";
import { ProfileSection } from "@/pages/settings/Profile";
import { IntegrationsSection } from "@/pages/settings/Integrations";
import { TeamSection } from "@/pages/settings/Team";
import { DangerSection } from "@/pages/settings/Danger";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    element: (
      <ProtectedRoute>
        <Layout>
          <Outlet />
        </Layout>
      </ProtectedRoute>
    ),
    children: [
      { path: "/", element: <Navigate to="/dashboard" replace /> },
      { path: "/dashboard", element: <DashboardPage /> },
      { path: "/prospects", element: <ProspectsPage /> },
      { path: "/prospects/:id", element: <ProspectDetailPage /> },
      { path: "/pipeline", element: <PipelinePage /> },
      { path: "/scout", element: <ScoutPage /> },
      { path: "/outreach", element: <OutreachPage /> },
      { path: "/sequences", element: <SequencesPage /> },
      { path: "/analytics", element: <AnalyticsPage /> },
      // Settings: nested layout with left rail (T9.6 audit)
      {
        path: "/settings",
        element: <SettingsLayout />,
        children: [
          { index: true, element: <Navigate to="/settings/profile" replace /> },
          { path: "profile", element: <ProfileSection /> },
          { path: "integrations", element: <IntegrationsSection /> },
          { path: "team", element: <TeamSection /> },
          { path: "danger", element: <DangerSection /> },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <NotFoundPage />,
  },
]);
