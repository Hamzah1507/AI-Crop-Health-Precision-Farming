import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/auth';
import {
  chatbotAPI, predictionsAPI, recommendationsAPI, soilAPI
} from '../services/api';
import ChatbotSidebar from '../components/chatbot/ChatbotSidebar';
import ChatMessage from '../components/chatbot/ChatMessage';
import ChatbotInput from '../components/chatbot/ChatbotInput';
import ChatbotContextPanel from '../components/chatbot/ChatbotContextPanel';
import {
  FiMenu, FiSidebar, FiAlertCircle, FiPlus, FiArrowRight
} from 'react-icons/fi';
import { WiDaySunny } from 'react-icons/wi';

export default function Chatbot() {
  const { user } = useAuth();

  // State: Conversations & Active Chat
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(() => {
    const saved = localStorage.getItem('agrix_active_conv_id');
    return saved ? parseInt(saved, 10) : null;
  });
  const [messages, setMessages] = useState([]);
  const [currentTitle, setCurrentTitle] = useState('New Consultation');

  // Loading & Network States
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingChat, setLoadingChat] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [prefillMessage, setPrefillMessage] = useState('');

  // Context Panel Data
  const [predictions, setPredictions] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [soilRecord, setSoilRecord] = useState(null);

  // Responsive Drawer Toggles for Mobile / Tablet
  const [showMobileSidebar, setShowMobileSidebar] = useState(false);
  const [showMobileContext, setShowMobileContext] = useState(false);

  // Auto-scroll anchor
  const messagesEndRef = useRef(null);

  // Initial prompt questions matching Capstone requirements
  const INITIAL_PROMPTS = [
    {
      title: 'Soil Health Improvement',
      prompt: 'How can I improve my soil health?'
    },
    {
      title: 'Tomato Leaf Spot Diagnosis',
      prompt: 'What is causing yellow spots on my tomato leaves?'
    },
    {
      title: 'Hot Weather Irrigation Management',
      prompt: 'How should I manage irrigation during hot weather?'
    },
    {
      title: 'Essential Crop Nutrients',
      prompt: 'Which nutrients are important for healthy crop growth?'
    },
    {
      title: 'Plant Disease Prevention',
      prompt: 'How can I prevent common plant diseases?'
    }
  ];

  // 1. Fetch conversations and context on initial mount
  useEffect(() => {
    let active = true;

    async function init() {
      try {
        const [convsRes, predsRes, recsRes, soilRes] = await Promise.allSettled([
          chatbotAPI.getConversations(),
          predictionsAPI.getAll(0, 10),
          recommendationsAPI.getAll(),
          soilAPI.getLatest()
        ]);

        if (!active) return;

        if (convsRes.status === 'fulfilled' && convsRes.value?.data) {
          const list = convsRes.value.data || [];
          setConversations(list);
          if (list.length > 0) {
            setActiveConversationId((prev) => (prev && list.some((c) => c.id === prev) ? prev : list[0].id));
          }
        }
        setLoadingConversations(false);

        if (predsRes.status === 'fulfilled' && predsRes.value?.data) {
          setPredictions(predsRes.value.data);
        }
        if (recsRes.status === 'fulfilled' && recsRes.value?.data) {
          setRecommendations(recsRes.value.data);
        }
        if (soilRes.status === 'fulfilled' && soilRes.value?.data) {
          setSoilRecord(soilRes.value.data);
        }
      } catch {
        if (active) setLoadingConversations(false);
      }
    }

    init();
    return () => { active = false; };
  }, []);

  // 2. Fetch messages whenever activeConversationId changes
  useEffect(() => {
    if (!activeConversationId) {
      localStorage.removeItem('agrix_active_conv_id');
      return undefined;
    }
    let active = true;
    localStorage.setItem('agrix_active_conv_id', String(activeConversationId));

    chatbotAPI.getConversation(activeConversationId).then((res) => {
      if (!active) return;
      if (res.data) {
        setMessages(res.data.messages || []);
        setCurrentTitle(res.data.title || 'Consultation');
      }
    }).catch(() => {
      if (!active) return;
      setError('Failed to load conversation messages.');
    }).finally(() => {
      if (active) setLoadingChat(false);
    });

    return () => { active = false; };
  }, [activeConversationId]);

  // 3. Auto-scroll to bottom of chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, sending]);

  const handleNewChat = () => {
    setActiveConversationId(null);
    setMessages([]);
    setCurrentTitle('New Consultation');
    setError('');
    setShowMobileSidebar(false);
  };

  const handleSelectConversation = (convId) => {
    setActiveConversationId(convId);
    setShowMobileSidebar(false);
  };

  const handleDeleteConversation = async (convId) => {
    try {
      await chatbotAPI.deleteConversation(convId);
      const updated = conversations.filter(c => c.id !== convId);
      setConversations(updated);

      if (activeConversationId === convId) {
        if (updated.length > 0) {
          setActiveConversationId(updated[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch {
      setError('Failed to delete conversation.');
    }
  };

  const handleSendMessage = async (userText) => {
    if (!userText.trim() || sending) return;

    setError('');
    setSending(true);

    // Optimistically append user message
    const nextId = messages.length > 0 ? (messages[messages.length - 1].id || 0) + 1 : 1;
    const tempUserMsg = {
      id: nextId,
      conversation_id: activeConversationId || 0,
      role: 'user',
      content: userText,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, tempUserMsg]);

    try {
      const res = await chatbotAPI.sendMessage({
        conversation_id: activeConversationId || undefined,
        message: userText
      });

      const conversationData = res.data;
      if (conversationData) {
        setActiveConversationId(conversationData.id);
        setCurrentTitle(conversationData.title);
        setMessages(conversationData.messages || []);

        // Refresh conversation list in sidebar
        chatbotAPI.getConversations().then(r => setConversations(r.data || []));
      }
    } catch {
      setError('Could not reach the AI Agronomist service. Please check your connection and try again.');
    } finally {
      setSending(false);
    }
  };

  const handleSelectWorkflowPrompt = (promptText) => {
    setPrefillMessage(promptText);
    setShowMobileSidebar(false);
  };

  return (
    <div className="relative flex h-[calc(100vh-6.5rem)] min-h-[580px] w-full overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-card">
      {/* ============================================================= */}
      {/* 1. LEFT PANEL: Chat Navigation & History (IMAGE 1 Recreation)   */}
      {/* ============================================================= */}
      {/* Desktop Left Sidebar */}
      <div className="hidden lg:block lg:w-[260px] xl:w-[280px] shrink-0 h-full">
        <ChatbotSidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          onNewChat={handleNewChat}
          onDeleteConversation={handleDeleteConversation}
          onSelectWorkflowPrompt={handleSelectWorkflowPrompt}
          loading={loadingConversations}
          error={error && !messages.length ? error : ''}
        />
      </div>

      {/* Mobile / Tablet Left Sidebar Drawer */}
      {showMobileSidebar && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={() => setShowMobileSidebar(false)} />
          <div className="relative z-10 w-72 max-w-[85vw] h-full bg-white shadow-lift animate-fadeIn">
            <ChatbotSidebar
              conversations={conversations}
              activeConversationId={activeConversationId}
              onSelectConversation={handleSelectConversation}
              onNewChat={handleNewChat}
              onDeleteConversation={handleDeleteConversation}
              onSelectWorkflowPrompt={handleSelectWorkflowPrompt}
              loading={loadingConversations}
            />
          </div>
        </div>
      )}

      {/* ============================================================= */}
      {/* 2. CENTER PANEL: Main Chat Experience (IMAGE 1 Recreation)     */}
      {/* ============================================================= */}
      <div className="flex min-w-0 flex-1 flex-col h-full bg-[#FAF9F5] border-r border-slate-200">
        {/* Chat Header Bar */}
        <div className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
          <div className="flex items-center gap-3">
            {/* Mobile Left Toggle */}
            <button
              type="button"
              onClick={() => setShowMobileSidebar(true)}
              className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden"
              aria-label="Open conversation history"
            >
              <FiMenu className="text-lg" />
            </button>

            {/* AgrixAI Avatar Badge */}
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-green-700 text-white shadow-sm">
              <WiDaySunny className="text-2xl" aria-hidden="true" />
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-display text-base font-semibold text-slate-900 leading-tight">
                  AgrixAI Agronomist
                </h2>
                <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-[10px] font-medium text-green-800">
                  <span className="h-1.5 w-1.5 rounded-full bg-green-600 animate-pulse" />
                  Online
                </span>
              </div>
              <p className="text-xs text-slate-500 truncate max-w-[220px] sm:max-w-md">
                {currentTitle}
              </p>
            </div>
          </div>

          {/* Header Action Controls */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleNewChat}
              title="Start New Chat"
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 hover:text-green-800"
            >
              <FiPlus />
              <span className="hidden sm:inline">New Chat</span>
            </button>

            {/* Right Panel Toggle on Tablet & Mobile */}
            <button
              type="button"
              onClick={() => setShowMobileContext(true)}
              title="View Contextual Farm Insights"
              className="rounded-xl border border-slate-200 bg-white p-2 text-slate-600 shadow-sm transition hover:bg-slate-50 xl:hidden"
              aria-label="Toggle farm context panel"
            >
              <FiSidebar className="text-base" />
            </button>
          </div>
        </div>

        {/* Scrollable Conversation Stream */}
        <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 space-y-6">
          {loadingChat ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <div className="mx-auto h-8 w-8 rounded-full border-3 border-green-600 border-t-transparent animate-spin" />
                <p className="mt-2 text-xs text-slate-500">Loading consultation messages...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            /* Empty State Hero & Agricultural Suggestions */
            <div className="mx-auto max-w-2xl py-6 animate-fadeIn">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 text-center shadow-card">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-green-50 text-green-700 shadow-sm">
                  <WiDaySunny className="text-4xl" />
                </div>
                <h3 className="mt-4 font-display text-2xl font-semibold text-slate-900">
                  Welcome to AgrixAI Agronomist
                </h3>
                <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600 leading-relaxed">
                  Your dedicated intelligent agricultural advisor. Ask any question about leaf disease diagnostics,
                  soil chemistry, fertilizer dosages, or irrigation management for your cultivated crops.
                </p>

                {/* Initial Suggested Agricultural Questions (Mandatory specification) */}
                <div className="mt-6 text-left">
                  <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5">
                    Recommended Questions to Get Started
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {INITIAL_PROMPTS.map((item, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleSendMessage(item.prompt)}
                        className="group flex items-start justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50/70 p-3 text-left transition hover:border-green-400 hover:bg-green-50/60 hover:shadow-sm"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-semibold text-slate-800 group-hover:text-green-900 truncate">
                            {item.title}
                          </p>
                          <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5 leading-snug">
                            {item.prompt}
                          </p>
                        </div>
                        <FiArrowRight className="mt-1 text-slate-400 transition group-hover:translate-x-0.5 group-hover:text-green-700 shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            /* Render Message History */
            <div className="space-y-5">
              {messages.map((msg, index) => (
                <ChatMessage
                  key={msg.id || index}
                  message={msg}
                  currentUserName={user?.username || 'Farmer'}
                />
              ))}

              {/* Typing / Analyzing Indicator */}
              {sending && (
                <div className="flex items-start gap-2 animate-fadeIn">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-700 text-white shadow-sm shrink-0">
                    <WiDaySunny className="text-base" />
                  </div>
                  <div className="rounded-2xl rounded-tl-none border border-slate-200 bg-white px-4 py-3 shadow-card">
                    <div className="flex items-center gap-2 text-xs text-slate-600">
                      <span className="flex gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-green-600 animate-bounce" />
                        <span className="h-1.5 w-1.5 rounded-full bg-green-600 animate-bounce [animation-delay:0.2s]" />
                        <span className="h-1.5 w-1.5 rounded-full bg-green-600 animate-bounce [animation-delay:0.4s]" />
                      </span>
                      <span className="font-medium text-slate-700">AgrixAI is analyzing agronomic knowledge...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Error Banner */}
              {error && (
                <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700 flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <FiAlertCircle className="text-red-600 text-sm shrink-0" />
                    <span>{error}</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setError('')}
                    className="font-semibold underline ml-3 text-red-800 hover:text-red-900"
                  >
                    Dismiss
                  </button>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom Floating Input Section */}
        <div className="shrink-0 p-4 sm:px-6 sm:pb-5 bg-gradient-to-t from-white via-white to-transparent">
          <ChatbotInput
            onSendMessage={handleSendMessage}
            disabled={loadingChat}
            sending={sending}
            prefillMessage={prefillMessage}
            onClearPrefill={() => setPrefillMessage('')}
          />
        </div>
      </div>

      {/* ============================================================= */}
      {/* 3. RIGHT PANEL: Contextual Farm Information (IMAGE 1 Match)   */}
      {/* ============================================================= */}
      {/* Desktop Right Context Panel */}
      <div className="hidden xl:block xl:w-[320px] 2xl:w-[350px] shrink-0 h-full">
        <ChatbotContextPanel
          predictions={predictions}
          recommendations={recommendations}
          soilRecord={soilRecord}
        />
      </div>

      {/* Mobile / Tablet Right Context Drawer */}
      {showMobileContext && (
        <div className="fixed inset-0 z-50 flex justify-end xl:hidden">
          <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs" onClick={() => setShowMobileContext(false)} />
          <div className="relative z-10 w-80 max-w-[85vw] h-full bg-white shadow-lift animate-fadeIn">
            <div className="flex items-center justify-between p-3.5 border-b border-slate-200">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-700">Farm Context</span>
              <button
                type="button"
                onClick={() => setShowMobileContext(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              >
                Close
              </button>
            </div>
            <div className="h-[calc(100%-48px)] overflow-y-auto">
              <ChatbotContextPanel
                predictions={predictions}
                recommendations={recommendations}
                soilRecord={soilRecord}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
