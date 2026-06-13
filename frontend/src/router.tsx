import { createBrowserRouter } from "react-router-dom";
import Layout from "./Layout";
import ChatPage from "./pages/ChatPage";
import GoalsPage from "./pages/Goals";
import InboxPage from "./pages/Inbox";
import TimelinePage from "./pages/Timeline";
import MemoriesPage from "./pages/Memories";
import DashboardPage from "./pages/Dashboard";
import SettingsPage from "./pages/Settings";
import KnowledgePage from "./pages/Knowledge";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <ChatPage /> },
      { path: "chat/:conversationId", element: <ChatPage /> },
      { path: "goals", element: <GoalsPage /> },
      { path: "goals/:goalId", element: <GoalsPage /> },
      { path: "inbox", element: <InboxPage /> },
      { path: "timeline", element: <TimelinePage /> },
      { path: "memories", element: <MemoriesPage /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "knowledge", element: <KnowledgePage /> },
    ],
  },
]);
