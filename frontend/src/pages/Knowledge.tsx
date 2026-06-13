import { useEffect, useState } from "react";
import {
  listKnowledgeDocuments,
  importKnowledgeDocument,
  uploadKnowledgeDocument,
  deleteKnowledgeDocument,
  searchKnowledge,
  ApiError,
  type KnowledgeDocument,
} from "../api/client";
import { useErrorStore } from "../stores/errorStore";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import { Input, Textarea } from "../components/ui/Input";
import EmptyState from "../components/ui/EmptyState";
import Spinner from "../components/ui/Spinner";
import Dialog from "../components/ui/Dialog";

export default function KnowledgePage() {
  const addError = useErrorStore((s) => s.addError);
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<
    Array<{ content: string }>
  >([]);
  const [searching, setSearching] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<KnowledgeDocument | null>(
    null
  );

  const load = async () => {
    setLoading(true);
    try {
      setDocs(await listKnowledgeDocuments());
    } catch (err) {
      addError(
        err instanceof ApiError ? err.message : "加载文档失败",
        "知识库"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleImport = async () => {
    if (!title.trim() || !content.trim()) return;
    try {
      await importKnowledgeDocument({ title: title.trim(), content });
      setTitle("");
      setContent("");
      load();
    } catch (err) {
      addError(
        err instanceof ApiError ? err.message : "导入文档失败",
        "知识库"
      );
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await uploadKnowledgeDocument(file);
      load();
    } catch (err) {
      addError(
        err instanceof ApiError ? err.message : "上传文件失败",
        "知识库"
      );
    } finally {
      e.target.value = "";
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    const id = deleteTarget.id;
    setDeleteTarget(null);
    try {
      await deleteKnowledgeDocument(id);
      load();
    } catch (err) {
      addError(
        err instanceof ApiError ? err.message : "删除文档失败",
        "知识库"
      );
    }
  };

  const handleSearch = async () => {
    if (!searchQ.trim()) return;
    setSearching(true);
    try {
      const res = await searchKnowledge(searchQ.trim());
      setSearchResults(res.results || []);
    } catch (err) {
      addError(
        err instanceof ApiError ? err.message : "搜索失败",
        "知识库"
      );
    } finally {
      setSearching(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center gap-2 text-gray-500">
        <Spinner />
        加载知识库…
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-100">知识库</h2>
          <p className="text-sm text-gray-500 mt-1">
            导入文档供 RAG 检索，可在对话中引用相关知识。
          </p>
        </div>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">导入文档</h3>
          <div className="space-y-3">
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="文档标题"
            />
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="文档内容..."
              rows={4}
              autoGrow
              className="w-full resize-none"
            />
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleImport}
                disabled={!title.trim() || !content.trim()}
              >
                导入文本
              </Button>
              <label>
                <span className="inline-flex px-3 py-1.5 text-xs rounded-lg font-medium bg-gray-700 hover:bg-gray-600 text-gray-100 cursor-pointer">
                  上传文件
                </span>
                <input
                  type="file"
                  accept=".txt,.md,.markdown"
                  className="hidden"
                  onChange={handleUpload}
                />
              </label>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-sm font-medium text-gray-300 mb-3">搜索测试</h3>
          <div className="flex gap-2">
            <Input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="输入搜索词..."
              className="flex-1"
            />
            <Button size="sm" onClick={handleSearch} disabled={searching}>
              {searching ? "搜索中…" : "搜索"}
            </Button>
          </div>
          {searchResults.length > 0 && (
            <div className="mt-3 space-y-2">
              {searchResults.map((r, i) => (
                <p
                  key={i}
                  className="text-xs text-gray-400 p-2 bg-gray-800/50 rounded line-clamp-3"
                >
                  {r.content}
                </p>
              ))}
            </div>
          )}
        </Card>

        <div>
          <h3 className="text-sm font-medium text-gray-300 mb-3">
            文档列表 ({docs.length})
          </h3>
          {docs.length === 0 ? (
            <EmptyState
              title="暂无文档"
              description="导入文本或上传 Markdown/TXT 文件开始构建知识库"
            />
          ) : (
            <div className="space-y-2">
              {docs.map((doc) => (
                <Card key={doc.id} padding="sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-gray-200">{doc.title}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {doc.chunk_count} 块 ·{" "}
                        {new Date(doc.created_at).toLocaleDateString("zh-CN")}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="danger"
                      onClick={() => setDeleteTarget(doc)}
                    >
                      删除
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog
        open={!!deleteTarget}
        title="删除文档"
        description={
          deleteTarget
            ? `确定删除「${deleteTarget.title}」？此操作不可撤销。`
            : undefined
        }
        confirmLabel="删除"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
