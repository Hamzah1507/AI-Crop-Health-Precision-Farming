import { useState, useRef, useEffect, useCallback } from 'react';
import {
  FiArrowUp, FiPaperclip, FiSliders, FiGrid,
  FiX, FiCheckCircle
} from 'react-icons/fi';

export default function ChatbotInput({
  onSendMessage,
  disabled = false,
  sending = false,
  prefillMessage = '',
  onClearPrefill
}) {
  const [text, setText] = useState('');
  const [showSettings, setShowSettings] = useState(false);
  const [showPrompts, setShowPrompts] = useState(false);
  const [attachmentNotice, setAttachmentNotice] = useState('');
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);

  // Quick prompt suggestions (matches prompt specification)
  const SUGGESTIONS = [
    'How can I improve my soil health?',
    'What is causing yellow spots on my tomato leaves?',
    'How should I manage irrigation during hot weather?',
    'Which nutrients are important for healthy crop growth?',
    'How can I prevent common plant diseases?'
  ];

  // Adjust textarea height dynamically up to 130px
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 130)}px`;
  }, []);

  // Auto-fill when prefillMessage changes
  const prevPrefillRef = useRef(prefillMessage);
  useEffect(() => {
    if (prefillMessage && prefillMessage !== prevPrefillRef.current) {
      prevPrefillRef.current = prefillMessage;
      setText(prefillMessage);
      onClearPrefill?.();
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }
  }, [prefillMessage, onClearPrefill]);

  useEffect(() => {
    adjustHeight();
  }, [text, adjustHeight]);

  const handleTextChange = (e) => {
    setText(e.target.value);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    const clean = text.trim();
    if (!clean || sending || disabled) return;

    onSendMessage(clean);
    setText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleSelectSuggestion = (prompt) => {
    setText(prompt);
    setShowPrompts(false);
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setAttachmentNotice(`Attached: ${file.name} (${(file.size / 1024).toFixed(0)} KB)`);
      setText((prev) =>
        prev
          ? `${prev}\n[Referencing photo: ${file.name}]`
          : `I have a question about this crop leaf photograph (${file.name}): what symptoms or nutrient deficiencies do you observe?`
      );
    }
  };

  return (
    <div className="relative w-full">
      {/* Settings Modal / Popover */}
      {showSettings && (
        <div className="absolute bottom-full left-4 mb-2 z-30 w-72 rounded-2xl border border-slate-200 bg-white p-3.5 shadow-lift">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
              <FiSliders className="text-green-700" /> Agronomist Settings
            </span>
            <button
              type="button"
              onClick={() => setShowSettings(false)}
              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <FiX className="text-xs" />
            </button>
          </div>
          <div className="mt-2.5 space-y-2 text-xs text-slate-600">
            <div className="flex items-center justify-between">
              <span>Knowledge Engine:</span>
              <span className="font-medium text-green-700">Agronomic Rules</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Vision Model:</span>
              <span className="font-medium text-slate-800">ResNet-18 (18 Classes)</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Agronomy Guidelines:</span>
              <span className="font-medium text-slate-800">Active</span>
            </div>
          </div>
        </div>
      )}

      {/* Prompts Dropdown */}
      {showPrompts && (
        <div className="absolute bottom-full left-4 mb-2 z-30 w-80 max-w-[90vw] rounded-2xl border border-slate-200 bg-white p-3 shadow-lift">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100">
            <span className="text-xs font-semibold text-slate-800">Quick Agricultural Inquiries</span>
            <button
              type="button"
              onClick={() => setShowPrompts(false)}
              className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
            >
              <FiX className="text-xs" />
            </button>
          </div>
          <div className="mt-2 space-y-1 max-h-56 overflow-y-auto pr-1">
            {SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSelectSuggestion(s)}
                className="w-full text-left rounded-xl px-2.5 py-1.5 text-xs text-slate-700 hover:bg-green-50 hover:text-green-900 transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Attachment Tag Notice if active */}
      {attachmentNotice && (
        <div className="mb-2 flex items-center justify-between rounded-xl bg-green-50 px-3 py-1.5 text-xs text-green-800 border border-green-200">
          <span className="flex items-center gap-1.5 truncate">
            <FiCheckCircle className="text-green-600" />
            <span className="truncate">{attachmentNotice}</span>
          </span>
          <button
            type="button"
            onClick={() => setAttachmentNotice('')}
            className="ml-2 text-slate-400 hover:text-slate-600"
          >
            <FiX />
          </button>
        </div>
      )}

      {/* Main Input Card (styled to match bottom card of IMAGE 1) */}
      <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-card transition-all focus-within:border-green-600 focus-within:shadow-lift">
        {/* Top Textarea */}
        <div className="flex items-start gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            disabled={disabled || sending}
            placeholder="Ask anything about crops, soil health, pests or treatments... (Shift+Enter for newline)"
            className="w-full resize-none border-0 bg-transparent px-1 py-1 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-0 leading-relaxed max-h-32"
          />
        </div>

        {/* Bottom Actions Bar */}
        <div className="mt-2.5 flex items-center justify-between border-t border-slate-100 pt-2">
          {/* Left Functional Buttons (Attach, Settings, Options) */}
          <div className="flex items-center gap-1 sm:gap-2">
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              title="Attach leaf image or document"
              className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition"
            >
              <FiPaperclip className="text-sm" />
              <span className="hidden sm:inline">Attach</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setShowSettings(!showSettings);
                setShowPrompts(false);
              }}
              title="Assistant engine settings"
              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs transition ${
                showSettings ? 'bg-green-50 text-green-800' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
              }`}
            >
              <FiSliders className="text-sm" />
              <span className="hidden sm:inline">Settings</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setShowPrompts(!showPrompts);
                setShowSettings(false);
              }}
              title="Browse quick prompts"
              className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs transition ${
                showPrompts ? 'bg-green-50 text-green-800' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
              }`}
            >
              <FiGrid className="text-sm" />
              <span className="hidden sm:inline">Options</span>
            </button>
          </div>

          {/* Right Action: Circular Green Send Button */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!text.trim() || sending || disabled}
              title="Send message (Enter)"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-green-700 text-white shadow-sm transition hover:bg-green-800 disabled:opacity-40 disabled:cursor-not-allowed hover:shadow active:scale-95"
            >
              {sending ? (
                <div className="h-4 w-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
              ) : (
                <FiArrowUp className="text-lg stroke-[2.5]" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
