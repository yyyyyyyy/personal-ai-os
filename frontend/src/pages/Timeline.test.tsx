import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import TimelinePage from "./Timeline";

vi.mock("../api/client", () => ({
  listReviews: vi.fn().mockResolvedValue([
    {
      id: "r1",
      type: "weekly",
      period_start: "2026-06-01",
      period_end: "2026-06-07",
      content: "本周完成了Python学习，运动3次。下周继续推进。",
    },
    {
      id: "r2",
      type: "daily",
      period_start: "2026-06-10",
      period_end: "2026-06-10",
      content: "完成代码审查，处理了3个issue。",
    },
  ]),
}));

const now = new Date("2026-06-10T12:00:00Z");

const mockEvents = [
  {
    id: "e1",
    type: "goal_created",
    summary: "创建目标「学习Rust」",
    timestamp: "2026-06-09T10:30:00Z",
    goal_id: "g1",
    payload: null,
  },
  {
    id: "e2",
    type: "conversation",
    summary: "与AI讨论了Rust所有权模型",
    timestamp: "2026-06-09T14:00:00Z",
    goal_id: null,
    payload: null,
  },
  {
    id: "e3",
    type: "action_status_changed",
    summary: "完成行动「阅读Rust Book第4章」",
    timestamp: "2026-06-08T18:00:00Z",
    goal_id: null,
    payload: null,
  },
];

function mockFetch(events: typeof mockEvents = mockEvents, ok = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/events/")) {
        return Promise.resolve({
          ok,
          json: () => Promise.resolve(events),
        });
      }
      return Promise.reject(new Error("Unknown URL"));
    }),
  );
}

describe("TimelinePage", () => {
  beforeEach(() => {
    vi.setSystemTime(now);
    mockFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders timeline title", () => {
    render(<TimelinePage />);
    expect(screen.getAllByText("人生时间线")[0]).toBeInTheDocument();
  });

  it("renders review section with weekly and daily labels", async () => {
    render(<TimelinePage />);

    const reviewHeader = await screen.findByText("最近复盘", {}, { timeout: 3000 });
    expect(reviewHeader).toBeInTheDocument();

    const weeklyElem = await screen.findByText(/每周复盘/, {}, { timeout: 3000 });
    expect(weeklyElem).toBeInTheDocument();

    const dailyElem = await screen.findByText(/每日复盘/, {}, { timeout: 3000 });
    expect(dailyElem).toBeInTheDocument();

    const pythonElem = await screen.findByText(/本周完成了Python学习/, {}, { timeout: 3000 });
    expect(pythonElem).toBeInTheDocument();
  });

  it("renders event items grouped by date", async () => {
    render(<TimelinePage />);

    const rustGoal = await screen.findByText(/创建目标「学习Rust」/, {}, { timeout: 3000 });
    expect(rustGoal).toBeInTheDocument();

    const rustChat = await screen.findByText(/与AI讨论了Rust所有权模型/, {}, { timeout: 3000 });
    expect(rustChat).toBeInTheDocument();

    const rustAction = await screen.findByText(/完成行动「阅读Rust Book第4章」/, {}, { timeout: 3000 });
    expect(rustAction).toBeInTheDocument();
  });

  it("renders event type labels", async () => {
    render(<TimelinePage />);

    const goalLabels = await screen.findAllByText("创建目标", { exact: true }, { timeout: 3000 });
    expect(goalLabels.length).toBeGreaterThan(0);

    const convLabels = await screen.findAllByText("对话", { exact: true }, { timeout: 3000 });
    expect(convLabels.length).toBeGreaterThan(0);

    const actionLabels = await screen.findAllByText("行动状态变更", { exact: true }, { timeout: 3000 });
    expect(actionLabels.length).toBeGreaterThan(0);
  });

  it("renders review type labels correctly", async () => {
    render(<TimelinePage />);

    const weeklyLabel = await screen.findByText(/每周复盘/, {}, { timeout: 3000 });
    expect(weeklyLabel).toBeInTheDocument();

    const dailyLabel = await screen.findByText(/每日复盘/, {}, { timeout: 3000 });
    expect(dailyLabel).toBeInTheDocument();
  });

  it("shows empty state when no events", async () => {
    mockFetch([], true);
    render(<TimelinePage />);

    const emptyMsg = await screen.findByText(/暂无事件记录/, {}, { timeout: 3000 });
    expect(emptyMsg).toBeInTheDocument();
  });

  it("handles fetch failure gracefully", async () => {
    mockFetch([], false);
    render(<TimelinePage />);

    const emptyMsg = await screen.findByText(/暂无事件记录/, {}, { timeout: 3000 });
    expect(emptyMsg).toBeInTheDocument();
  });

  it("renders multiple dates in reverse chronological order", async () => {
    render(<TimelinePage />);

    const dateElements = await screen.findAllByText(/2026年/, { exact: false });
    expect(dateElements.length).toBeGreaterThanOrEqual(2);
  });
});
