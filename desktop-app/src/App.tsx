import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import {
  FolderOpen,
  FileText,
  Settings,
  Sparkles,
  Folder,
  Check,
  AlertCircle,
  Loader2,
} from "lucide-react";
import "./App.css";

interface FileItem {
  path: string;
  name: string;
  size: number;
  modified: string;
  category?: string;
}

interface ClassificationResult {
  category: string;
  subcategory?: string;
  confidence: number;
  suggested_path: string;
  suggested_name?: string;
  tags: string[];
  summary?: string;
  reasoning?: string;
  model_used: string;
  processing_time_ms: number;
  tokens_used: number;
  cost_usd: number;
}

function App() {
  const [selectedFolder, setSelectedFolder] = useState<string>("");
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [organizing, setOrganizing] = useState(false);
  const [currentTab, setCurrentTab] = useState<"organize" | "settings">("organize");
  const [useMultiModel, setUseMultiModel] = useState(false);
  const [userTier, setUserTier] = useState<"FREE" | "STARTER" | "PRO" | "ENTERPRISE">("FREE");
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [classification, setClassification] = useState<ClassificationResult | null>(null);

  const selectFolder = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
      });

      if (selected && typeof selected === "string") {
        setSelectedFolder(selected);
        setStatus(`Selected: ${selected}`);
        await loadFiles(selected);
      }
    } catch (err) {
      setError(`Failed to select folder: ${err}`);
    }
  };

  const loadFiles = async (folder: string) => {
    try {
      setLoading(true);
      setError("");
      const result = await invoke<FileItem[]>("list_files", {
        directory: folder,
      });
      setFiles(result);
      setStatus(`Found ${result.length} files`);
    } catch (err) {
      setError(`Failed to load files: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const organizeFolder = async () => {
    if (!selectedFolder) {
      setError("Please select a folder first");
      return;
    }

    try {
      setOrganizing(true);
      setError("");
      setStatus("Organizing files...");

      const result = await invoke<string>("organize_folder", {
        options: {
          folder: selectedFolder,
          preview: false,
          auto_approve: true,
          deep_analysis: true,
          use_multi_model: useMultiModel,
          user_tier: userTier,
        },
      });

      setStatus("Organization complete!");
      console.log(result);

      // Reload files
      await loadFiles(selectedFolder);
    } catch (err) {
      setError(`Organization failed: ${err}`);
    } finally {
      setOrganizing(false);
    }
  };

  const classifySingleFile = async (filePath: string) => {
    try {
      setLoading(true);
      setError("");
      setStatus(`Classifying ${filePath}...`);

      const result = await invoke<ClassificationResult>("classify_file", {
        filePath,
        useMultiModel,
        tier: userTier,
      });

      setClassification(result);
      setStatus(`Classified as: ${result.category}`);
    } catch (err) {
      setError(`Classification failed: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm">
        <div className="mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sparkles className="w-8 h-8 text-primary-600" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                AI File Organizer
              </h1>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setCurrentTab("organize")}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  currentTab === "organize"
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                }`}
              >
                <Folder className="w-4 h-4" />
                Organize
              </button>
              <button
                onClick={() => setCurrentTab("settings")}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  currentTab === "settings"
                    ? "bg-primary-600 text-white"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300"
                }`}
              >
                <Settings className="w-4 h-4" />
                Settings
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto px-6 py-8 max-w-7xl">
        {currentTab === "organize" ? (
          <div className="space-y-6">
            {/* Folder Selection */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
                Select Folder
              </h2>
              <div className="flex gap-4">
                <button
                  onClick={selectFolder}
                  className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 flex items-center justify-center gap-2"
                >
                  <FolderOpen className="w-5 h-5" />
                  Choose Folder
                </button>
                {selectedFolder && (
                  <button
                    onClick={organizeFolder}
                    disabled={organizing || files.length === 0}
                    className="flex-1 px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {organizing ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Organizing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        Organize Now
                      </>
                    )}
                  </button>
                )}
              </div>

              {selectedFolder && (
                <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700 rounded text-sm text-gray-700 dark:text-gray-300">
                  <strong>Selected:</strong> {selectedFolder}
                </div>
              )}
            </div>

            {/* Status */}
            {status && (
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-start gap-3">
                <Check className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <p className="text-blue-800 dark:text-blue-200">{status}</p>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                <p className="text-red-800 dark:text-red-200">{error}</p>
              </div>
            )}

            {/* Files List */}
            {files.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
                <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Files ({files.length})
                  </h2>
                </div>
                <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-96 overflow-y-auto">
                  {files.map((file, index) => (
                    <div
                      key={index}
                      className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <FileText className="w-5 h-5 text-gray-400" />
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 dark:text-white truncate">
                            {file.name}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {formatFileSize(file.size)}
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => classifySingleFile(file.path)}
                        className="px-3 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50 text-sm opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        Classify
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Classification Result */}
            {classification && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">
                  Classification Result
                </h2>
                <div className="space-y-3">
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Category:</span>{" "}
                    <span className="text-gray-900 dark:text-white">{classification.category}</span>
                    {classification.subcategory && (
                      <span className="text-gray-600 dark:text-gray-400"> / {classification.subcategory}</span>
                    )}
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Confidence:</span>{" "}
                    <span className="text-gray-900 dark:text-white">
                      {(classification.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Suggested Path:</span>{" "}
                    <span className="text-gray-900 dark:text-white">{classification.suggested_path}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Model:</span>{" "}
                    <span className="text-gray-900 dark:text-white">{classification.model_used}</span>
                  </div>
                  <div>
                    <span className="font-semibold text-gray-700 dark:text-gray-300">Processing Time:</span>{" "}
                    <span className="text-gray-900 dark:text-white">{classification.processing_time_ms}ms</span>
                  </div>
                  {classification.cost_usd > 0 && (
                    <div>
                      <span className="font-semibold text-gray-700 dark:text-gray-300">Cost:</span>{" "}
                      <span className="text-gray-900 dark:text-white">${classification.cost_usd.toFixed(6)}</span>
                    </div>
                  )}
                  {classification.reasoning && (
                    <div>
                      <span className="font-semibold text-gray-700 dark:text-gray-300">Reasoning:</span>{" "}
                      <p className="text-gray-900 dark:text-white mt-1">{classification.reasoning}</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Settings */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-6 text-gray-900 dark:text-white">
                AI Settings
              </h2>
              <div className="space-y-6">
                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={useMultiModel}
                      onChange={(e) => setUseMultiModel(e.target.checked)}
                      className="w-5 h-5 text-primary-600 rounded focus:ring-primary-500"
                    />
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white block">
                        Use Multi-Model AI
                      </span>
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        Enable GPT-4, Claude, and Ollama for intelligent model selection
                      </span>
                    </div>
                  </label>
                </div>

                <div>
                  <label className="block font-medium text-gray-900 dark:text-white mb-2">
                    Subscription Tier
                  </label>
                  <select
                    value={userTier}
                    onChange={(e) => setUserTier(e.target.value as any)}
                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="FREE">FREE - Local models only</option>
                    <option value="STARTER">STARTER - GPT-3.5, Claude Haiku</option>
                    <option value="PRO">PRO - GPT-4, Claude Sonnet</option>
                    <option value="ENTERPRISE">ENTERPRISE - Custom models</option>
                  </select>
                  <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                    {userTier === "FREE" && "Uses local Ollama models - completely free, no API costs"}
                    {userTier === "STARTER" && "Fast cloud models - $5/month, good for basic organization"}
                    {userTier === "PRO" && "Advanced AI models - $12/month, best accuracy and features"}
                    {userTier === "ENTERPRISE" && "Custom fine-tuned models - Contact for pricing"}
                  </p>
                </div>
              </div>
            </div>

            {/* Info */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
              <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
                How Multi-Model AI Works
              </h3>
              <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
                <li>• Simple files (images, videos) → Fast models (or local)</li>
                <li>• Medium complexity → Balanced models (GPT-3.5, Claude Haiku)</li>
                <li>• Complex files (documents, code) → Advanced models (GPT-4, Claude Sonnet)</li>
                <li>• FREE tier always uses local Ollama - no costs</li>
                <li>• Cost is automatically optimized based on file complexity</li>
              </ul>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
