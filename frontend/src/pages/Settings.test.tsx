import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import SettingsPage from "./Settings";

vi.mock("../api/client", () => ({
  getSystemHealth: vi.fn().mockResolvedValue({
    status: "ok",
    version: "0.9.0",
    auth_required: false,
  }),
  fetchSystemInfo: vi.fn().mockResolvedValue({
    conversations: 5,
    goals: 2,
    memories: 10,
    messages: 20,
  }),
  getLlmProviders: vi.fn().mockResolvedValue({
    providers: [{ name: "deepseek", available: true }],
    default: "deepseek-chat",
  }),
  getMcpStatus: vi.fn().mockResolvedValue({
    enabled: true,
    servers: [{ name: "playwright", status: "connected", tool_count: 5 }],
    total_tools: 5,
  }),
  exportData: vi.fn().mockResolvedValue({ events: [] }),
  importData: vi.fn(),
  listInboxEmails: vi.fn().mockResolvedValue([]),
  ApiError: class extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

vi.mock("../stores/errorStore", () => ({
  useErrorStore: (selector: (s: { addError: () => void }) => unknown) =>
    selector({ addError: vi.fn() }),
}));

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders system status and export button", async () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText("设置")).toBeInTheDocument();
    });
    expect(screen.getByText("导出全部数据")).toBeInTheDocument();
    expect(screen.getByText("0.9.0")).toBeInTheDocument();
  });

  it("shows MCP server status", async () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText("playwright")).toBeInTheDocument();
    });
    expect(screen.getByText("已连接")).toBeInTheDocument();
  });

  it("shows email connectivity status", async () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>
    );
    await waitFor(() => {
      expect(screen.getByText("邮箱 / 收件箱")).toBeInTheDocument();
    });
    expect(screen.getByText("已连通")).toBeInTheDocument();
  });
});
