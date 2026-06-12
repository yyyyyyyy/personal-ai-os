import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Sidebar from "./Sidebar";

describe("Sidebar", () => {
  const defaultProps = {
    currentPage: "chat" as const,
    onNavigate: vi.fn(),
    conversations: [
      { id: "c1", title: "Rust学习讨论" },
      { id: "c2", title: "周末计划" },
    ],
    activeConversationId: "c1",
    onSelectConversation: vi.fn(),
    onNewChat: vi.fn(),
    onDeleteChat: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders app title", () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getByText("Personal AI Runtime")).toBeInTheDocument();
    expect(screen.getByText("你的第二大脑")).toBeInTheDocument();
  });

  it("renders all navigation items", () => {
    render(<Sidebar {...defaultProps} />);
    const dialogItems = screen.getAllByText("对话");
    expect(dialogItems.length).toBeGreaterThan(0);
    expect(screen.getAllByText("目标")[0]).toBeInTheDocument();
    expect(screen.getAllByText("收件箱")[0]).toBeInTheDocument();
    expect(screen.getAllByText("时间线")[0]).toBeInTheDocument();
    expect(screen.getAllByText("记忆")[0]).toBeInTheDocument();
    expect(screen.getAllByText("仪表盘")[0]).toBeInTheDocument();
  });

  it("highlights current page in navigation", () => {
    render(<Sidebar {...defaultProps} currentPage="goals" />);
    const chatButtons = screen.getAllByText("对话");
    const goalsButtons = screen.getAllByText("目标");
    expect(chatButtons[0].closest("button")?.className).toContain("text-gray-400");
    expect(goalsButtons[0].closest("button")?.className).toContain("text-emerald-400");
  });

  it("calls onNavigate when nav item clicked", () => {
    render(<Sidebar {...defaultProps} />);
    fireEvent.click(screen.getAllByText("目标")[0]);
    expect(defaultProps.onNavigate).toHaveBeenCalledWith("goals");
  });

  it("shows new chat button when on chat page", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    const newChatButtons = screen.getAllByText(/^\+ 新对话$/);
    expect(newChatButtons.length).toBeGreaterThan(0);
  });

  it("hides new chat button when not on chat page", () => {
    render(<Sidebar {...defaultProps} currentPage="goals" />);
    expect(screen.queryByText(/^\+ 新对话$/)).not.toBeInTheDocument();
  });

  it("renders conversation list on chat page", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    expect(screen.getAllByText("Rust学习讨论")[0]).toBeInTheDocument();
    expect(screen.getAllByText("周末计划")[0]).toBeInTheDocument();
  });

  it("highlights active conversation", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    const activeConv = screen.getAllByText("Rust学习讨论")[0].closest("div");
    const inactiveConv = screen.getAllByText("周末计划")[0].closest("div");
    expect(activeConv?.className).toContain("text-white");
    expect(inactiveConv?.className).toContain("text-gray-400");
  });

  it("calls onSelectConversation when conversation clicked", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    fireEvent.click(screen.getAllByText("周末计划")[0]);
    expect(defaultProps.onSelectConversation).toHaveBeenCalledWith("c2");
  });

  it("calls onNewChat when new chat button clicked", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    fireEvent.click(screen.getAllByText(/^\+ 新对话$/)[0]);
    expect(defaultProps.onNewChat).toHaveBeenCalledOnce();
  });

  it("calls onDeleteChat when delete button clicked", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    const deleteButtons = screen.getAllByTitle("删除对话");
    expect(deleteButtons.length).toBeGreaterThan(0);
    fireEvent.click(deleteButtons[0]);
    expect(defaultProps.onDeleteChat).toHaveBeenCalledWith("c1");
  });

  it("does not trigger onSelectConversation when delete is clicked", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" />);
    const deleteButtons = screen.getAllByTitle("删除对话");
    fireEvent.click(deleteButtons[0]);
    expect(defaultProps.onSelectConversation).not.toHaveBeenCalled();
  });

  it("shows empty state when no conversations", () => {
    render(<Sidebar {...defaultProps} currentPage="chat" conversations={[]} />);
    expect(screen.getAllByText("暂无对话")[0]).toBeInTheDocument();
  });

  it("hides conversation list when not on chat page", () => {
    render(<Sidebar {...defaultProps} currentPage="goals" />);
    expect(screen.queryByText("Rust学习讨论")).not.toBeInTheDocument();
  });

  it("renders version number", () => {
    render(<Sidebar {...defaultProps} />);
    expect(screen.getAllByText("v0.9.0")[0]).toBeInTheDocument();
  });
});
