/* Lawgic — React + TypeScript frontend */
import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const API_BASE = "http://localhost:8000";
const CHAT_STORAGE_KEY = "lawgic_react_chats_v4";
const THEME_STORAGE_KEY = "lawgic_theme";
const AUTH_STORAGE_KEY = "lawgic_auth_token";
const USER_NAME_STORAGE_KEY = "lawgic_user_name";

type Theme = "light" | "dark";

type Citation = {
  citation?: string;
  section?: string;
  reference_type?: string;
  score?: number | null;
  document_name?: string;
};

type Clause = {
  clause_id?: number;
  clause_text?: string;
  clause_type?: string;
  entities?: Record<string, unknown>[];
  confidence?: number | null;
};

type Risk = {
  clause_id?: number;
  clause_text?: string;
  clause_type?: string;
  risk_level?: string;
  triggers?: string[];
};

type DocumentMetadata = {
  document_type?: string;
  document_title?: string;
  parties_involved?: string[];
  effective_date?: string;
  duration_validity?: string;
  governing_law_jurisdiction?: string;
  key_terms?: string[];
};

type DocumentData = {
  filename: string;
  total_clauses: number;
  summary?: string;
  document_metadata?: DocumentMetadata;
  document_citations?: Citation[];
  clauses?: Clause[];
  risks?: Risk[];
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  context?: {
    text?: string;
    metadata?: Record<string, unknown>;
    score?: number | null;
  }[];
  streaming?: boolean;
  error?: boolean;
  isOverview?: boolean;
};

type Chat = {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  documentData?: DocumentData | null;
};

const makeId = () =>
  `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

const createChat = (): Chat => ({
  id: makeId(),
  title: "New Chat",
  messages: [],
  createdAt: Date.now(),
  documentData: null,
});

const isCasualMessage = (text: string) => {
  const value = text
    .trim()
    .toLowerCase()
    .replace(/[!?.,]+$/g, "");

  return /^(hi|hello|hey|hii|hiii|good morning|good afternoon|good evening|thanks|thank you|thx|bye|goodbye|who are you|what can you do)$/.test(
    value
  );
};

const casualReply = (text: string) => {
  const value = text.trim().toLowerCase();

  if (/^(thanks|thank you|thx)/.test(value)) {
    return "You're welcome! 😊";
  }

  if (/^(bye|goodbye)/.test(value)) {
    return "Goodbye! 👋";
  }

  if (/^(who are you|what can you do)/.test(value)) {
    return "I'm Lawgic, your legal document assistant. Upload a PDF, analyze it, and ask me questions about its contents.";
  }

  if (value.includes("good morning")) {
    return "Good morning! ☀️ How can I help you with your legal document today?";
  }

  if (value.includes("good afternoon")) {
    return "Good afternoon! 👋 How can I help you with your legal document today?";
  }

  if (value.includes("good evening")) {
    return "Good evening! 🌙 How can I help you with your legal document today?";
  }

  return "Hi! 👋 How can I help you with your legal document?";
};

function App() {
  const [theme, setTheme] = useState<Theme>(
    () =>
      (localStorage.getItem(THEME_STORAGE_KEY) as Theme) || "light"
  );

  const [chats, setChats] = useState<Chat[]>(() => {
    try {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      const parsed = saved ? JSON.parse(saved) : [];

      return Array.isArray(parsed) && parsed.length
        ? parsed
        : [createChat()];
    } catch {
      return [createChat()];
    }
  });

  const [activeChatId, setActiveChatId] = useState<string>(() => {
    try {
      const saved = localStorage.getItem(CHAT_STORAGE_KEY);
      const parsed = saved ? JSON.parse(saved) : [];

      return parsed?.[0]?.id || "";
    } catch {
      return "";
    }
  });

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentData, setDocumentData] =
    useState<DocumentData | null>(null);

  const [backendConnected, setBackendConnected] =
    useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showDocumentPanel, setShowDocumentPanel] =
    useState(true);

  const [mobilePanelOpen, setMobilePanelOpen] =
    useState(false);

  const [authOpen, setAuthOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const [authToken, setAuthToken] = useState(
    () => localStorage.getItem(AUTH_STORAGE_KEY) || ""
  );

  const [userName, setUserName] = useState(
    () => localStorage.getItem(USER_NAME_STORAGE_KEY) || ""
  );

  const [error, setError] = useState("");

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const activeChat = useMemo(
    () =>
      chats.find((chat) => chat.id === activeChatId) ||
      chats[0],
    [chats, activeChatId]
  );

  useEffect(() => {
    if (!activeChatId && chats[0]) {
      setActiveChatId(chats[0].id);
    }
  }, [activeChatId, chats]);

  useEffect(() => {
    localStorage.setItem(
      CHAT_STORAGE_KEY,
      JSON.stringify(chats)
    );
  }, [chats]);

  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    document.documentElement.setAttribute(
      "data-theme",
      theme
    );
  }, [theme]);

  useEffect(() => {
    document.title = "Lawgic — Legal Intelligence";

    const params = new URLSearchParams(
      window.location.search
    );

    const returnedToken =
      params.get("token") ||
      params.get("access_token") ||
      params.get("auth_token");

    const returnedName = params.get("name");

    if (returnedToken) {
      localStorage.setItem(
        AUTH_STORAGE_KEY,
        returnedToken
      );
      setAuthToken(returnedToken);
    }

    if (returnedName) {
      const decoded = decodeURIComponent(returnedName);

      localStorage.setItem(
        USER_NAME_STORAGE_KEY,
        decoded
      );

      setUserName(decoded);
    }

    if (returnedToken || returnedName) {
      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [activeChat?.messages, sending]);

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(
          `${API_BASE}/health`
        );

        setBackendConnected(response.ok);
      } catch {
        setBackendConnected(false);
      }
    };

    checkBackend();

    const timer = window.setInterval(
      checkBackend,
      10000
    );

    return () => window.clearInterval(timer);
  }, []);

  const updateActiveChat = (
    updater: Chat | ((chat: Chat) => Chat)
  ) => {
    setChats((prev) =>
      prev.map((chat) =>
        chat.id === activeChatId
          ? typeof updater === "function"
            ? updater(chat)
            : updater
          : chat
      )
    );
  };

  const addMessage = (
    message: Omit<ChatMessage, "id">
  ) => {
    updateActiveChat((chat) => ({
      ...chat,
      messages: [
        ...chat.messages,
        {
          id: makeId(),
          ...message,
        },
      ],
    }));
  };

  const updateLastAssistantMessage = (
    patch: Partial<ChatMessage>
  ) => {
    setChats((prev) =>
      prev.map((chat) => {
        if (chat.id !== activeChatId) return chat;

        const messages = [...chat.messages];
        const index = messages.length - 1;

        if (
          index < 0 ||
          messages[index].role !== "assistant"
        ) {
          return chat;
        }

        messages[index] = {
          ...messages[index],
          ...patch,
        };

        return {
          ...chat,
          messages,
        };
      })
    );
  };

  const handleNewChat = () => {
    const chat = createChat();

    setChats((prev) => [chat, ...prev]);
    setActiveChatId(chat.id);

    setSelectedFile(null);
    setDocumentData(null);
    setError("");
    setSidebarOpen(false);
  };

  const handleDeleteChat = () => {
    if (!activeChat) return;

    const remaining = chats.filter(
      (chat) => chat.id !== activeChat.id
    );

    if (!remaining.length) {
      const fresh = createChat();

      setChats([fresh]);
      setActiveChatId(fresh.id);
      setDocumentData(null);
    } else {
      setChats(remaining);
      setActiveChatId(remaining[0].id);
      setDocumentData(
        remaining[0].documentData || null
      );
    }

    setSelectedFile(null);
  };

  const selectChat = (id: string) => {
    setActiveChatId(id);

    const chat = chats.find(
      (item) => item.id === id
    );

    setDocumentData(
      chat?.documentData || null
    );

    setSelectedFile(null);
    setSidebarOpen(false);
  };

  const handleGoogleSignIn = () => {
    window.location.href =
      `${API_BASE}/auth/google/login`;
  };

  const handleSignOut = () => {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(
      USER_NAME_STORAGE_KEY
    );

    setAuthToken("");
    setUserName("");
    setProfileOpen(false);
  };

  const handleFileSelect = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];

    if (!file) return;

    setError("");

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      setError("Please select a PDF file.");
      event.target.value = "";
      return;
    }

    setSelectedFile(file);
    setDocumentData(null);
  };

  const formatFileSize = (bytes: number) =>
    bytes < 1024 * 1024
      ? `${(bytes / 1024).toFixed(0)} KB`
      : `${(bytes / 1024 / 1024).toFixed(2)} MB`;

  const generateDocumentOverview = (
    data: DocumentData
  ) => {
    const metadata =
      data.document_metadata || {};

    const risks = data.risks || [];
    const clauses = data.clauses || [];

    const content = [
      `## Analysis complete`,
      ``,
      `I've analyzed **${data.filename}** and prepared the document intelligence panel alongside this chat.`,
      ``,
      `### Quick summary`,
      data.summary ||
        "The document was analyzed successfully.",
      ``,
      `### What I found`,
      `- **Document type:** ${
        metadata.document_type || "Not found"
      }`,
      `- **Clauses detected:** ${
        data.total_clauses ?? clauses.length
      }`,
      `- **Risks flagged:** ${risks.length}`,
      metadata.effective_date
        ? `- **Effective date:** ${metadata.effective_date}`
        : "",
      ``,
      `You can now ask questions about the document. Try one of the suggested questions below.`,
    ]
      .filter(Boolean)
      .join("\n");

    addMessage({
      role: "assistant",
      content,
      citations: data.document_citations || [],
      context: [],
      isOverview: true,
    });
  };

  const handleAnalyzeDocument = async () => {
    if (!selectedFile || analyzing) return;

    setAnalyzing(true);
    setError("");

    try {
      const formData = new FormData();

      formData.append("file", selectedFile);

      const response = await fetch(
        `${API_BASE}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

      const data: DocumentData =
        await response.json();

      if (!response.ok) {
        throw new Error(
          (
            data as unknown as {
              detail?: string;
            }
          ).detail ||
            "Document analysis failed."
        );
      }

      setDocumentData(data);

      setChats((prev) =>
        prev.map((chat) =>
          chat.id === activeChatId
            ? {
                ...chat,
                title:
                  selectedFile.name
                    .replace(/\.pdf$/i, "")
                    .slice(0, 42) ||
                  "Legal Document",
                documentData: data,
              }
            : chat
        )
      );

      setShowDocumentPanel(true);
      setMobilePanelOpen(false);

      generateDocumentOverview(data);
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Unable to analyze the PDF.";

      setError(message);

      addMessage({
        role: "assistant",
        content: `### Analysis failed\n\n${message}`,
        error: true,
      });
    } finally {
      setAnalyzing(false);
    }
  };

  const sendMessage = async () => {
    const question = input.trim();

    if (!question || sending) return;

    setInput("");

    if (isCasualMessage(question)) {
      addMessage({
        role: "user",
        content: question,
      });

      window.setTimeout(
        () =>
          addMessage({
            role: "assistant",
            content: casualReply(question),
          }),
        100
      );

      return;
    }

    if (!documentData) {
      addMessage({
        role: "user",
        content: question,
      });

      addMessage({
        role: "assistant",
        content: selectedFile
          ? "Please click **Analyze Document** first. Once the analysis is complete, I can answer questions about the PDF."
          : "Please upload and analyze a PDF first. Once it's analyzed, you can ask me questions about it.",
      });

      return;
    }

    addMessage({
      role: "user",
      content: question,
    });

    addMessage({
      role: "assistant",
      content: "",
      citations: [],
      context: [],
      streaming: true,
    });

    setSending(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE}/ask/stream`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            question,
            clause_text: null,
            top_k: 5,

            // Hard-bind every chat request
            // to the currently analyzed PDF.
            document_name: documentData.filename,
          }),
        }
      );

      if (!response.ok || !response.body) {
        const errorData =
          await response.json().catch(() => ({}));

        throw new Error(
          errorData.detail ||
            "Unable to get a response."
        );
      }

      const reader =
        response.body.getReader();

      const decoder = new TextDecoder();

      let buffer = "";

      let finalCitations: Citation[] = [];

      let finalContext: {
        text?: string;
        metadata?: Record<string, unknown>;
        score?: number | null;
      }[] = [];

      const processEvent = (
        rawEvent: string
      ) => {
        const lines =
          rawEvent.split(/\r?\n/);

        let eventName = "message";
        let dataText = "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line
              .slice(6)
              .trim();
          } else if (
            line.startsWith("data:")
          ) {
            dataText += line
              .slice(5)
              .trim();
          }
        }

        if (!dataText) return;

        let payload: Record<string, any>;

        try {
          payload = JSON.parse(dataText);
        } catch {
          payload = {
            text: dataText,
          };
        }

        const type =
          payload.type || eventName;

        if (type === "context") {
          finalContext =
            payload.context ||
            payload.retrieved_context ||
            [];

          finalCitations =
            payload.citations || [];

          updateLastAssistantMessage({
            context: finalContext,
            citations: finalCitations,
          });
        }

        if (type === "token") {
          const token =
            payload.token ??
            payload.delta ??
            payload.text ??
            payload.content ??
            "";

          if (token) {
            setChats((prev) =>
              prev.map((chat) => {
                if (
                  chat.id !== activeChatId
                ) {
                  return chat;
                }

                const messages = [
                  ...chat.messages,
                ];

                const index =
                  messages.length - 1;

                if (
                  index < 0 ||
                  messages[index]
                    .role !== "assistant"
                ) {
                  return chat;
                }

                messages[index] = {
                  ...messages[index],
                  content: `${
                    messages[index]
                      .content || ""
                  }${token}`,
                };

                return {
                  ...chat,
                  messages,
                };
              })
            );
          }
        }

        if (type === "done") {
          finalCitations =
            payload.citations ||
            finalCitations;

          finalContext =
            payload.context ||
            payload.retrieved_context ||
            finalContext;

          updateLastAssistantMessage({
            streaming: false,
            citations: finalCitations,
            context: finalContext,
          });
        }

        if (type === "error") {
          throw new Error(
            payload.detail ||
              payload.error ||
              payload.message ||
              "Streaming failed."
          );
        }
      };

      while (true) {
        const {
          value,
          done,
        } = await reader.read();

        if (done) break;

        buffer += decoder.decode(
          value,
          { stream: true }
        );

        const events =
          buffer.split(
            /\r?\n\r?\n/
          );

        buffer =
          events.pop() || "";

        for (const event of events) {
          processEvent(event);
        }
      }

      if (buffer.trim()) {
        processEvent(buffer);
      }

      updateLastAssistantMessage({
        streaming: false,
      });
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : "Something went wrong while communicating with the backend.";

      updateLastAssistantMessage({
        content: message,
        error: true,
        streaming: false,
      });

      setError(message);
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>
  ) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey
    ) {
      event.preventDefault();
      sendMessage();
    }
  };

  const autoResize = () => {
    const element =
      textareaRef.current;

    if (!element) return;

    element.style.height = "auto";

    element.style.height = `${Math.min(
      element.scrollHeight,
      180
    )}px`;
  };

  const suggestedQuestions = [
    "What are the main obligations in this document?",
    "What are the biggest risks or unusual clauses?",
    "What are the termination conditions?",
    "Which important dates should I know?",
  ];

  const metadata =
    documentData?.document_metadata || {};

  const risks =
    documentData?.risks || [];

  const clauses =
    documentData?.clauses || [];

  const citations =
    documentData?.document_citations || [];

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="mobile-backdrop"
          onClick={() =>
            setSidebarOpen(false)
          }
          aria-label="Close menu"
        />
      )}

      <aside
        className={`sidebar ${
          sidebarOpen ? "open" : ""
        }`}
      >
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <img
              src={
                theme === "dark"
                  ? "/lawgic-logo-dark.png"
                  : "/lawgic-logo-light.png"
              }
              alt="Lawgic"
            />

            <div>
              <strong>Lawgic</strong>
              <span>
                Legal Intelligence
              </span>
            </div>
          </div>

          <button
            className="sidebar-close mobile-only"
            onClick={() =>
              setSidebarOpen(false)
            }
          >
            ×
          </button>
        </div>

        <div className="sidebar-content">
          <button
            className="new-chat-button"
            onClick={handleNewChat}
          >
            <span>＋</span>
            New chat
          </button>

          <div className="sidebar-label">
            Recent chats
          </div>

          <div className="chat-history">
            {chats.map((chat) => (
              <button
                key={chat.id}
                className={`chat-history-item ${
                  chat.id === activeChatId
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  selectChat(chat.id)
                }
              >
                <span className="history-icon">
                  ◌
                </span>

                <span>
                  {chat.title}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="connection-row">
            <span
              className={`status-dot ${
                backendConnected
                  ? "online"
                  : "offline"
              }`}
            />

            {backendConnected
              ? "Backend connected"
              : "Backend offline"}
          </div>

          <button
            className="sidebar-action"
            onClick={() =>
              setTheme(
                theme === "light"
                  ? "dark"
                  : "light"
              )
            }
          >
            <span>
              {theme === "light"
                ? "☾"
                : "☀"}
            </span>

            {theme === "light"
              ? "Dark mode"
              : "Light mode"}
          </button>

          <button
            className="account-row"
            onClick={() =>
              authToken
                ? setProfileOpen(
                    !profileOpen
                  )
                : setAuthOpen(true)
            }
          >
            <span className="avatar">
              {authToken
                ? (
                    userName?.[0] ||
                    "U"
                  ).toUpperCase()
                : "G"}
            </span>

            <span>
              {authToken
                ? userName ||
                  "My account"
                : "Sign in"}
            </span>
          </button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="menu-button"
              onClick={() =>
                setSidebarOpen(true)
              }
              aria-label="Open sidebar"
            >
              ☰
            </button>

            <div className="mobile-brand">
              <img
                src={
                  theme === "dark"
                    ? "/lawgic-logo-dark.png"
                    : "/lawgic-logo-light.png"
                }
                alt="Lawgic"
              />

              <strong>
                Lawgic
              </strong>
            </div>
          </div>

          <div className="topbar-actions">
            <span
              className={`top-status ${
                backendConnected
                  ? "online"
                  : "offline"
              }`}
              title={
                backendConnected
                  ? "Backend connected"
                  : "Backend offline"
              }
            />

            <button
              className="topbar-button hide-small"
              onClick={handleNewChat}
            >
              ＋ New chat
            </button>

            <button
              className="topbar-button danger hide-small"
              onClick={handleDeleteChat}
            >
              Delete
            </button>

            <button
              className="icon-button"
              onClick={() =>
                setTheme(
                  theme === "light"
                    ? "dark"
                    : "light"
                )
              }
              aria-label="Toggle theme"
            >
              {theme === "light"
                ? "☾"
                : "☀"}
            </button>

            <button
              className="profile-button"
              onClick={() =>
                authToken
                  ? setProfileOpen(
                      !profileOpen
                    )
                  : setAuthOpen(true)
              }
            >
              <span className="avatar small">
                {authToken
                  ? (
                      userName?.[0] ||
                      "U"
                    ).toUpperCase()
                  : "G"}
              </span>

              <span className="hide-small">
                {authToken
                  ? userName ||
                    "Account"
                  : "Sign in"}
              </span>
            </button>
          </div>

          {profileOpen && authToken && (
            <div className="profile-menu">
              <strong>
                {userName ||
                  "Signed in user"}
              </strong>

              <button
                onClick={handleSignOut}
              >
                Sign out
              </button>
            </div>
          )}
        </header>

        <div className="workspace">
          <section
            className={`chat-column ${
              showDocumentPanel &&
              documentData
                ? "analysis-visible"
                : ""
            }`}
          >
            <div className="chat-header">
              <div className="chat-heading">
                <h1>
                  {activeChat?.title ||
                    "Legal Assistant"}
                </h1>

                <p>
                  Ask questions,
                  understand clauses,
                  and review legal
                  risks.
                </p>
              </div>

              {documentData && (
                <button
                  className="document-button"
                  onClick={() =>
                    setMobilePanelOpen(
                      true
                    )
                  }
                >
                  <span>▤</span>
                  Analysis
                </button>
              )}
            </div>

            <div
              className={`messages-area ${
                !activeChat?.messages
                  ?.length
                  ? "empty"
                  : ""
              }`}
            >
              {!activeChat?.messages
                ?.length ? (
                <div className="welcome-screen">
                  <div className="welcome-orb">
                    <img
                      src={
                        theme === "dark"
                          ? "/lawgic-logo-dark.png"
                          : "/lawgic-logo-light.png"
                      }
                      alt="Lawgic"
                    />
                  </div>

                  <div className="eyebrow">
                    AI-POWERED LEGAL ASSISTANT
                  </div>

                  <h2>
                    How can I help
                    with your
                    document?
                  </h2>

                  <p>
                    Upload a legal
                    PDF, analyze it,
                    then chat
                    naturally with
                    Lawgic about
                    clauses, risks,
                    dates,
                    obligations,
                    and more.
                  </p>

                  <div className="upload-card">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="application/pdf,.pdf"
                      hidden
                      onChange={
                        handleFileSelect
                      }
                    />

                    {!selectedFile ? (
                      <button
                        className="upload-dropzone"
                        onClick={() =>
                          fileInputRef.current?.click()
                        }
                      >
                        <span className="upload-symbol">
                          ↑
                        </span>

                        <strong>
                          Upload a PDF
                        </strong>

                        <span>
                          Choose a legal
                          document from
                          your computer
                        </span>
                      </button>
                    ) : (
                      <div className="selected-file">
                        <div className="pdf-badge">
                          PDF
                        </div>

                        <div className="file-info">
                          <strong>
                            {selectedFile.name}
                          </strong>

                          <span>
                            {formatFileSize(
                              selectedFile.size
                            )}
                          </span>
                        </div>

                        <button
                          className="remove-file"
                          onClick={() => {
                            setSelectedFile(
                              null
                            );

                            if (
                              fileInputRef.current
                            ) {
                              fileInputRef.current.value =
                                "";
                            }
                          }}
                        >
                          ×
                        </button>
                      </div>
                    )}

                    {selectedFile && (
                      <button
                        className="analyze-button"
                        onClick={
                          handleAnalyzeDocument
                        }
                        disabled={analyzing}
                      >
                        {analyzing ? (
                          <>
                            <span className="spinner" />
                            Analyzing
                            document...
                          </>
                        ) : (
                          <>
                            ✦ Analyze
                            document
                          </>
                        )}
                      </button>
                    )}

                    {error && (
                      <div className="error-banner">
                        {error}
                      </div>
                    )}
                  </div>

                  <div className="feature-row">
                    <span>
                      ✦ Clause detection
                    </span>

                    <span>
                      ⚠ Risk analysis
                    </span>

                    <span>
                      ⌕ AI document chat
                    </span>
                  </div>
                </div>
              ) : (
                <div className="message-list">
                  {activeChat.messages.map(
                    (message) => (
                      <div
                        className={`message-row ${
                          message.role
                        }`}
                        key={message.id}
                      >
                        <div className="message-avatar">
                          {message.role ===
                          "assistant"
                            ? "L"
                            : "You"}
                        </div>

                        <div
                          className={`message-bubble ${
                            message.error
                              ? "error"
                              : ""
                          }`}
                        >
                          <div className="message-role">
                            {message.role ===
                            "assistant"
                              ? "Lawgic"
                              : "You"}
                          </div>

                          <div className="message-content">
                            {message.streaming &&
                            !message.content ? (
                              <div className="typing-indicator">
                                <span />
                                <span />
                                <span />
                              </div>
                            ) : (
                              <ReactMarkdown>
                                {
                                  message.content
                                }
                              </ReactMarkdown>
                            )}
                          </div>

                          {message.citations &&
                            message.citations
                              .length >
                              0 && (
                              <details className="citations">
                                <summary>
                                  Sources &
                                  citations (
                                  {
                                    message
                                      .citations
                                      .length
                                  }
                                  )
                                </summary>

                                <div className="citation-list">
                                  {message.citations
                                    .slice(
                                      0,
                                      12
                                    )
                                    .map(
                                      (
                                        citation,
                                        index
                                      ) => (
                                        <div
                                          className="citation-item"
                                          key={`${citation.citation}-${index}`}
                                        >
                                          <strong>
                                            📄{" "}
                                            {citation.document_name ||
                                              documentData?.filename ||
                                              citation.citation ||
                                              "Uploaded document"}
                                          </strong>

                                          <span>
                                            Section /
                                            Clause:{" "}
                                            {citation.section ||
                                              "Not found in uploaded document"}
                                          </span>
                                        </div>
                                      )
                                    )}
                                </div>
                              </details>
                            )}
                        </div>
                      </div>
                    )
                  )}

                  <div
                    ref={messagesEndRef}
                  />
                </div>
              )}
            </div>

            {documentData &&
              activeChat?.messages
                ?.length === 1 && (
                <div className="suggestions">
                  {suggestedQuestions.map(
                    (question) => (
                      <button
                        key={question}
                        onClick={() => {
                          setInput(
                            question
                          );
                          textareaRef.current?.focus();
                        }}
                      >
                        {question}
                      </button>
                    )
                  )}
                </div>
              )}

            <div className="composer-wrapper">
              <div className="composer">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => {
                    setInput(
                      e.target.value
                    );
                    autoResize();
                  }}
                  onKeyDown={
                    handleKeyDown
                  }
                  rows={1}
                  placeholder={
                    documentData
                      ? "Ask about this document..."
                      : "Upload and analyze a PDF to start chatting..."
                  }
                  disabled={sending}
                />

                <button
                  className="send-button"
                  onClick={sendMessage}
                  disabled={
                    !input.trim() ||
                    sending
                  }
                  aria-label="Send message"
                >
                  {sending ? (
                    <span className="send-spinner" />
                  ) : (
                    "↑"
                  )}
                </button>
              </div>

              <div className="composer-hint">
                Lawgic can make
                mistakes. Verify
                important legal
                information.
              </div>
            </div>
          </section>

          {documentData &&
            showDocumentPanel && (
              <aside className="analysis-panel">
                <div className="analysis-header">
                  <div>
                    <div className="panel-eyebrow">
                      DOCUMENT
                      INTELLIGENCE
                    </div>

                    <h2>
                      Analysis
                    </h2>
                  </div>

                  <button
                    className="panel-close"
                    onClick={() =>
                      setShowDocumentPanel(
                        false
                      )
                    }
                  >
                    ×
                  </button>
                </div>

                <div className="document-file-card">
                  <div className="pdf-badge">
                    PDF
                  </div>

                  <div>
                    <strong>
                      {documentData.filename}
                    </strong>

                    <span>
                      {
                        documentData.total_clauses
                      }{" "}
                      clauses detected
                    </span>
                  </div>
                </div>

                <section className="analysis-section">
                  <h3>
                    Document metadata
                  </h3>

                  <div className="metadata-grid">
                    <div>
                      <span>
                        Type
                      </span>

                      <strong>
                        {metadata.document_type ||
                          "Not found"}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Title
                      </span>

                      <strong>
                        {metadata.document_title ||
                          "Not found"}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Effective date
                      </span>

                      <strong>
                        {metadata.effective_date ||
                          "Not found"}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Duration
                      </span>

                      <strong>
                        {metadata.duration_validity ||
                          "Not found"}
                      </strong>
                    </div>

                    <div>
                      <span>
                        Jurisdiction
                      </span>

                      <strong>
                        {metadata.governing_law_jurisdiction ||
                          "Not found"}
                      </strong>
                    </div>
                  </div>

                  {metadata.parties_involved
                    ?.length ? (
                    <div className="tag-section">
                      <span>
                        Parties
                      </span>

                      <div className="tags">
                        {metadata.parties_involved.map(
                          (party) => (
                            <span
                              key={party}
                            >
                              {party}
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  ) : null}

                  {metadata.key_terms
                    ?.length ? (
                    <div className="tag-section">
                      <span>
                        Key terms
                      </span>

                      <div className="tags">
                        {metadata.key_terms.map(
                          (term) => (
                            <span
                              key={term}
                            >
                              {term}
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  ) : null}
                </section>

                <section className="analysis-section">
                  <div className="section-title-row">
                    <h3>
                      Citations
                    </h3>

                    <span className="count-badge">
                      {citations.length}
                    </span>
                  </div>

                  {citations.length ? (
                    <div className="compact-list">
                      {citations
                        .slice(0, 15)
                        .map(
                          (
                            citation,
                            index
                          ) => (
                            <div
                              className="compact-item"
                              key={`${citation.citation}-${index}`}
                            >
                              <strong>
                                📄{" "}
                                {citation.document_name ||
                                  documentData?.filename ||
                                  citation.citation ||
                                  "Uploaded document"}
                              </strong>

                              <span>
                                Section /
                                Clause:{" "}
                                {citation.section ||
                                  "Not found in uploaded document"}
                              </span>
                            </div>
                          )
                        )}
                    </div>
                  ) : (
                    <p className="muted">
                      No document
                      citations
                      found.
                    </p>
                  )}
                </section>

                <section className="analysis-section">
                  <div className="section-title-row">
                    <h3>
                      Clause detection
                    </h3>

                    <span className="count-badge">
                      {clauses.length}
                    </span>
                  </div>

                  <div className="compact-list">
                    {clauses
                      .slice(0, 15)
                      .map(
                        (clause) => (
                          <details
                            className="clause-item"
                            key={
                              clause.clause_id
                            }
                          >
                            <summary>
                              <span>
                                Clause{" "}
                                {
                                  clause.clause_id
                                }
                              </span>

                              <strong>
                                {clause.clause_type ||
                                  "Legal clause"}
                              </strong>
                            </summary>

                            <p>
                              {clause.clause_text ||
                                "No clause text available."}
                            </p>
                          </details>
                        )
                      )}
                  </div>
                </section>

                <section className="analysis-section">
                  <div className="section-title-row">
                    <h3>
                      Risk analysis
                    </h3>

                    <span className="count-badge risk">
                      {risks.length}
                    </span>
                  </div>

                  <div className="compact-list">
                    {risks.length ? (
                      risks
                        .slice(0, 15)
                        .map(
                          (
                            risk,
                            index
                          ) => (
                            <div
                              className={`risk-item ${
                                (
                                  risk.risk_level ||
                                  ""
                                ).toLowerCase()
                              }`}
                              key={`${risk.clause_id}-${index}`}
                            >
                              <div className="risk-top">
                                <strong>
                                  Clause{" "}
                                  {risk.clause_id ??
                                    "—"}
                                </strong>

                                <span>
                                  {risk.risk_level ||
                                    "Review"}
                                </span>
                              </div>

                              <strong>
                                {risk.clause_type ||
                                  "Legal clause"}
                              </strong>

                              {risk.triggers
                                ?.length ? (
                                <ul>
                                  {risk.triggers.map(
                                    (
                                      trigger
                                    ) => (
                                      <li
                                        key={
                                          trigger
                                        }
                                      >
                                        {
                                          trigger
                                        }
                                      </li>
                                    )
                                  )}
                                </ul>
                              ) : null}
                            </div>
                          )
                        )
                    ) : (
                      <p className="muted">
                        No risks were
                        returned by
                        the analysis.
                      </p>
                    )}
                  </div>
                </section>
              </aside>
            )}
        </div>
      </main>

      {documentData &&
        !showDocumentPanel && (
          <button
            className="floating-analysis"
            onClick={() =>
              setShowDocumentPanel(
                true
              )
            }
          >
            ▤ Analysis
          </button>
        )}

      {authOpen && (
        <div
          className="modal-backdrop"
          onClick={() =>
            setAuthOpen(false)
          }
        >
          <div
            className="auth-modal"
            onClick={(e) =>
              e.stopPropagation()
            }
          >
            <button
              className="modal-close"
              onClick={() =>
                setAuthOpen(false)
              }
            >
              ×
            </button>

            <div className="auth-icon">
              ⚖
            </div>

            <h2>
              Welcome to Lawgic
            </h2>

            <p>
              Sign in to keep your
              Lawgic workspace
              connected to your
              account.
            </p>

            <button
              className="google-button"
              onClick={
                handleGoogleSignIn
              }
            >
              Continue with Google
            </button>

            <button
              className="guest-button"
              onClick={() =>
                setAuthOpen(false)
              }
            >
              Continue as guest
            </button>
          </div>
        </div>
      )}

      {documentData &&
        mobilePanelOpen && (
          <div
            className="mobile-analysis-overlay"
            onClick={() =>
              setMobilePanelOpen(
                false
              )
            }
          >
            <aside
              className="mobile-analysis-drawer"
              onClick={(e) =>
                e.stopPropagation()
              }
            >
              <div className="analysis-header">
                <div>
                  <div className="panel-eyebrow">
                    DOCUMENT
                    INTELLIGENCE
                  </div>

                  <h2>
                    Analysis
                  </h2>
                </div>

                <button
                  className="panel-close"
                  onClick={() =>
                    setMobilePanelOpen(
                      false
                    )
                  }
                >
                  ×
                </button>
              </div>

              <div className="document-file-card">
                <div className="pdf-badge">
                  PDF
                </div>

                <div>
                  <strong>
                    {documentData.filename}
                  </strong>

                  <span>
                    {
                      documentData.total_clauses
                    }{" "}
                    clauses detected
                  </span>
                </div>
              </div>

              <section className="analysis-section">
                <h3>
                  Metadata
                </h3>

                <div className="metadata-grid">
                  <div>
                    <span>
                      Type
                    </span>

                    <strong>
                      {metadata.document_type ||
                        "Not found"}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Title
                    </span>

                    <strong>
                      {metadata.document_title ||
                        "Not found"}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Date
                    </span>

                    <strong>
                      {metadata.effective_date ||
                        "Not found"}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Jurisdiction
                    </span>

                    <strong>
                      {metadata.governing_law_jurisdiction ||
                        "Not found"}
                    </strong>
                  </div>
                </div>
              </section>

              <section className="analysis-section">
                <div className="section-title-row">
                  <h3>
                    Citations
                  </h3>

                  <span className="count-badge">
                    {citations.length}
                  </span>
                </div>

                <div className="compact-list">
                  {citations
                    .slice(0, 12)
                    .map((c, i) => (
                      <div
                        className="compact-item"
                        key={i}
                      >
                        <strong>
                          📄{" "}
                          {c.document_name ||
                            documentData.filename ||
                            c.citation}
                        </strong>

                        <span>
                          Section /
                          Clause:{" "}
                          {c.section ||
                            "Not found in uploaded document"}
                        </span>
                      </div>
                    ))}
                </div>
              </section>

              <section className="analysis-section">
                <div className="section-title-row">
                  <h3>
                    Clauses
                  </h3>

                  <span className="count-badge">
                    {clauses.length}
                  </span>
                </div>

                <div className="compact-list">
                  {clauses
                    .slice(0, 12)
                    .map((c) => (
                      <details
                        className="clause-item"
                        key={c.clause_id}
                      >
                        <summary>
                          <span>
                            Clause{" "}
                            {c.clause_id}
                          </span>

                          <strong>
                            {c.clause_type}
                          </strong>
                        </summary>

                        <p>
                          {c.clause_text}
                        </p>
                      </details>
                    ))}
                </div>
              </section>

              <section className="analysis-section">
                <div className="section-title-row">
                  <h3>
                    Risks
                  </h3>

                  <span className="count-badge risk">
                    {risks.length}
                  </span>
                </div>

                <div className="compact-list">
                  {risks
                    .slice(0, 12)
                    .map((r, i) => (
                      <div
                        className={`risk-item ${
                          (
                            r.risk_level ||
                            ""
                          ).toLowerCase()
                        }`}
                        key={i}
                      >
                        <div className="risk-top">
                          <strong>
                            Clause{" "}
                            {
                              r.clause_id
                            }
                          </strong>

                          <span>
                            {
                              r.risk_level
                            }
                          </span>
                        </div>

                        <strong>
                          {
                            r.clause_type
                          }
                        </strong>
                      </div>
                    ))}
                </div>
              </section>
            </aside>
          </div>
        )}
    </div>
  );
}

export default App;