import { useState } from 'react';
import {
  FiPlus, FiMessageSquare, FiArchive, FiBookOpen,
  FiTrash2, FiActivity, FiDroplet, FiSearch, FiSun, FiCheck
} from 'react-icons/fi';

export default function ChatbotSidebar({
  conversations = [],
  activeConversationId = null,
  onSelectConversation,
  onNewChat,
  onDeleteConversation,
  onSelectWorkflowPrompt,
  loading = false,
  error = ''
}) {
  const [activeFeature, setActiveFeature] = useState('chat');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);

  // Farming assistance modes / workflows (matches IMAGE 1 Workspaces)
  const WORKSPACES = [
    {
      id: 'crop_health',
      label: 'Crop Health Assistant',
      icon: FiActivity,
      prompt: 'Can you assess my crop health and suggest preventive measures against common fungal and bacterial infections?'
    },
    {
      id: 'soil_analysis',
      label: 'Soil Analysis Assistance',
      icon: FiDroplet,
      prompt: 'How do I interpret my soil NPK and pH readings to select the best fertilizer for my field?'
    },
    {
      id: 'disease_diagnosis',
      label: 'Disease Diagnosis Assistance',
      icon: FiSearch,
      prompt: 'What are the characteristic visual symptoms of blight, leaf spot, and rust on tomato and potato leaves?'
    },
    {
      id: 'irrigation_guidance',
      label: 'Irrigation Guidance',
      icon: FiSun,
      prompt: 'What are the recommended irrigation schedules and moisture levels for summer growing cycles?'
    },
  ];

  const handleDeleteClick = (e, id) => {
    e.stopPropagation();
    if (deleteConfirmId === id) {
      onDeleteConversation(id);
      setDeleteConfirmId(null);
    } else {
      setDeleteConfirmId(id);
      setTimeout(() => setDeleteConfirmId(null), 3500);
    }
  };

  return (
    <div className="flex h-full flex-col bg-white border-r border-slate-200 p-3 sm:p-4 select-none">
      {/* Top Action: New Chat Button (Prominent card like IMAGE 1) */}
      <button
        type="button"
        onClick={onNewChat}
        className="group flex w-full items-center justify-between gap-3 rounded-2xl bg-green-700 px-4 py-3 text-sm font-medium text-white shadow-card transition-all hover:bg-green-800 hover:shadow-lift active:scale-[0.99]"
      >
        <span className="flex items-center gap-2.5">
          <FiPlus className="text-lg transition-transform group-hover:rotate-90" aria-hidden="true" />
          <span>New Chat</span>
        </span>
        <span className="rounded-md bg-green-800/80 px-2 py-0.5 text-[11px] font-normal tracking-wide text-green-100">
          AgrixAI
        </span>
      </button>

      {/* Main Navigation Sections */}
      <div className="mt-4 flex-1 space-y-5 overflow-y-auto pr-1">
        {/* Features Section (matches IMAGE 1) */}
        <div>
          <p className="px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Features</p>
          <div className="mt-1.5 space-y-0.5">
            <button
              type="button"
              onClick={() => setActiveFeature('chat')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium transition ${
                activeFeature === 'chat'
                  ? 'bg-green-50 text-green-800 font-semibold shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <FiMessageSquare className={activeFeature === 'chat' ? 'text-green-700' : 'text-slate-400'} />
              <span>Chat</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveFeature('archived')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium transition ${
                activeFeature === 'archived'
                  ? 'bg-green-50 text-green-800 font-semibold shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <FiArchive className={activeFeature === 'archived' ? 'text-green-700' : 'text-slate-400'} />
              <span>Archived</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveFeature('library')}
              className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs font-medium transition ${
                activeFeature === 'library'
                  ? 'bg-green-50 text-green-800 font-semibold shadow-sm'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <FiBookOpen className={activeFeature === 'library' ? 'text-green-700' : 'text-slate-400'} />
              <span>Library</span>
            </button>
          </div>
        </div>

        {/* Workspaces / Assistance Modes (matches IMAGE 1 Workspaces) */}
        <div>
          <p className="px-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Assistance Workspaces</p>
          <div className="mt-1.5 space-y-0.5">
            {WORKSPACES.map((ws) => {
              const Icon = ws.icon;
              return (
                <button
                  key={ws.id}
                  type="button"
                  onClick={() => onSelectWorkflowPrompt && onSelectWorkflowPrompt(ws.prompt)}
                  title={`Start consultation: ${ws.label}`}
                  className="group flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-xs text-slate-600 transition hover:bg-green-50/70 hover:text-green-900"
                >
                  <Icon className="text-slate-400 transition-colors group-hover:text-green-700" />
                  <span className="truncate">{ws.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Recents Section (matches IMAGE 1 Recents) */}
        <div>
          <div className="flex items-center justify-between px-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Recents</p>
            {conversations.length > 0 && (
              <span className="text-[11px] text-slate-400">{conversations.length}</span>
            )}
          </div>

          <div className="mt-1.5 space-y-1">
            {loading && conversations.length === 0 ? (
              <div className="space-y-2 px-2 py-3">
                <div className="h-4 w-3/4 animate-pulse rounded bg-slate-100" />
                <div className="h-4 w-1/2 animate-pulse rounded bg-slate-100" />
                <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
              </div>
            ) : error ? (
              <p className="px-2 py-3 text-xs text-red-500">{error}</p>
            ) : conversations.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 px-3 py-4 text-center">
                <p className="text-xs text-slate-500">No conversations yet.</p>
                <button
                  type="button"
                  onClick={onNewChat}
                  className="mt-1 text-xs font-medium text-green-700 hover:underline"
                >
                  Start your first chat
                </button>
              </div>
            ) : (
              conversations.map((conv) => {
                const isActive = activeConversationId === conv.id;
                const isConfirming = deleteConfirmId === conv.id;

                return (
                  <div
                    key={conv.id}
                    onClick={() => onSelectConversation(conv.id)}
                    className={`group relative flex items-center justify-between gap-2 rounded-xl px-2.5 py-2 text-xs transition cursor-pointer ${
                      isActive
                        ? 'bg-green-50/90 font-medium text-green-900 border border-green-200/80 shadow-sm'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`}
                  >
                    <div className="flex min-w-0 flex-1 items-center gap-2">
                      <FiMessageSquare
                        className={`shrink-0 text-sm ${isActive ? 'text-green-700' : 'text-slate-400 group-hover:text-slate-600'}`}
                      />
                      <span className="truncate">{conv.title || 'Untitled Conversation'}</span>
                    </div>

                    {/* Delete button (with confirm state) */}
                    <button
                      type="button"
                      onClick={(e) => handleDeleteClick(e, conv.id)}
                      title={isConfirming ? 'Click again to confirm delete' : 'Delete conversation'}
                      className={`shrink-0 rounded-md p-1 transition ${
                        isConfirming
                          ? 'bg-red-50 text-red-600 ring-1 ring-red-300'
                          : 'text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-slate-200 hover:text-red-600'
                      }`}
                    >
                      {isConfirming ? <FiCheck className="text-xs" /> : <FiTrash2 className="text-xs" />}
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

