import { beforeAll, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import ChatView from "./ChatView";

vi.mock("../../api/client", () => ({
  getMessages: vi.fn().mockResolvedValue([]),
  sendMessage: vi.fn(),
  resolveApproval: vi.fn(),
  ApiError: class extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

describe("ChatView", () => {
  beforeAll(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("renders input area and send button", () => {
    render(<ChatView conversationId="test-conv-1" />);

    expect(screen.getByPlaceholderText(/输入消息/)).toBeInTheDocument();
    const buttons = screen.getAllByRole("button", { name: "发送" });
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("disables send button when input is empty", () => {
    render(<ChatView conversationId="test-conv-1" />);

    const buttons = screen.getAllByRole("button", { name: "发送" });
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });
});
