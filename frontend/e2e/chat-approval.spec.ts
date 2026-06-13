import { test, expect, type Page } from "@playwright/test";

const CONV_ID = "e2e-conv-1";

async function mockCommonApis(page: Page) {
  await page.route("**/api/system/health", async (route) => {
    await route.fulfill({
      json: {
        status: "ok",
        service: "personal-ai",
        version: "1.0.0",
        auth_required: false,
      },
    });
  });

  await page.route("**/api/system/info", async (route) => {
    await route.fulfill({
      json: { conversations: 0, goals: 0, memories: 0, messages: 0 },
    });
  });

  await page.route("**/api/system/llm-providers", async (route) => {
    await route.fulfill({
      json: { providers: [], default: "deepseek-chat" },
    });
  });

  await page.route("**/api/system/mcp-status", async (route) => {
    await route.fulfill({
      json: { enabled: false, servers: [], total_tools: 0 },
    });
  });

  await page.route("**/api/reviews/**", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route("**/api/inbox/**", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route("**/api/chat/conversations**", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        json: [
          {
            id: CONV_ID,
            title: "测试对话",
            summary: null,
            created_at: "2026-06-10T00:00:00Z",
            updated_at: "2026-06-10T00:00:00Z",
          },
        ],
      });
      return;
    }
    await route.continue();
  });

  await page.route(`**/api/chat/conversations/${CONV_ID}/messages`, async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: [] });
      return;
    }
    await route.continue();
  });

  await page.route("**/api/goals**", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route("**/api/approvals/**", async (route) => {
    await route.fulfill({ json: [] });
  });

  await page.route("**/api/chat/approvals/*/resolve", async (route) => {
    await route.fulfill({
      json: { status: "denied", assistant_message: "操作已取消" },
    });
  });

  await page.route("**/api/notifications**", async (route) => {
    await route.fulfill({ json: [] });
  });
}

test.describe("Chat flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("onboarding_done", "1");
    });
    await mockCommonApis(page);
  });

  test("home page shows greeting and new chat", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/欢迎回来/)).toBeVisible();
    await expect(page.getByRole("button", { name: "开始新对话" })).toBeVisible();
  });

  test("navigation to goals page", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "目标" }).click();
    await expect(page).toHaveURL(/\/goals/);
    await expect(page.getByText("目标").first()).toBeVisible();
  });

  test("settings page shows export button", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByText("导出全部数据")).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "数据主权" })
    ).toBeVisible();
  });

  test("chat input and send button present on new conversation", async ({
    page,
  }) => {
    await page.goto(`/chat/${CONV_ID}`);
    await expect(page.getByPlaceholder(/输入消息/)).toBeVisible();
    await expect(page.getByRole("button", { name: "发送" })).toBeVisible();
  });
});

test.describe("Chat approval flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      localStorage.setItem("onboarding_done", "1");
    });
    await mockCommonApis(page);
  });

  test("shows confirmation dialog and resolves approval", async ({ page }) => {
    await page.route(`**/api/chat/conversations/${CONV_ID}/messages`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ json: [] });
        return;
      }

      const sse =
        'data: {"type":"confirmation_required","tool_name":"write_file","tool_args":{"path":"/tmp/e2e.txt","content":"hello"},"approval_id":"ap-e2e-1","tool_call_id":"tc-e2e-1"}\n\n' +
        'data: {"type":"done"}\n\n';

      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: sse,
      });
    });

    await page.route("**/api/chat/approvals/ap-e2e-1/resolve", async (route) => {
      await route.fulfill({
        json: { status: "approved", result: '{"ok":true}' },
      });
    });

    await page.goto(`/chat/${CONV_ID}`);

    await page.getByPlaceholder(/输入消息/).fill("请写入一个文件");
    await page.getByRole("button", { name: "发送" }).click();

    await expect(page.getByText(/确认写入文件/)).toBeVisible({ timeout: 10000 });

    await page.getByRole("button", { name: "确认执行" }).click();

    await expect(page.getByText(/确认写入文件/)).not.toBeVisible({ timeout: 5000 });
  });

  test("user can deny pending tool approval", async ({ page }) => {
    await page.route(`**/api/chat/conversations/${CONV_ID}/messages`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ json: [] });
        return;
      }

      const sse =
        'data: {"type":"confirmation_required","tool_name":"write_file","tool_args":{"path":"/tmp/e2e.txt","content":"hello"},"approval_id":"ap-e2e-2","tool_call_id":"tc-e2e-2"}\n\n' +
        'data: {"type":"done"}\n\n';

      await route.fulfill({
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
        body: sse,
      });
    });

    await page.goto(`/chat/${CONV_ID}`);

    await page.getByPlaceholder(/输入消息/).fill("请写入一个文件");
    await page.getByRole("button", { name: "发送" }).click();

    await expect(page.getByText(/确认写入文件/)).toBeVisible({ timeout: 10000 });

    const dialog = page.locator(".bg-amber-900\\/30");
    await dialog.getByRole("button", { name: "取消" }).click();

    await expect(page.getByText(/确认写入文件/)).not.toBeVisible({ timeout: 5000 });
  });
});
