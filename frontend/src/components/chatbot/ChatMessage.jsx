import { useState } from 'react';
import { FiCopy, FiCheck, FiThumbsUp, FiCheckCircle } from 'react-icons/fi';
import { WiDaySunny } from 'react-icons/wi';

/**
 * Format ISO datetime into a clean 12-hour time string like "02:48 PM"
 */
function formatTime(isoString) {
  if (!isoString) return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

/**
 * Lightweight, zero-dependency Markdown parser for agricultural responses.
 * Supports bold, inline code, headings, bullet lists, numbered lists, and markdown tables.
 */
function FormattedContent({ content }) {
  if (!content) return null;

  // Split into paragraphs / blocks
  const blocks = content.split(/\n{2,}/);

  return (
    <div className="space-y-3 text-sm leading-relaxed text-slate-800">
      {blocks.map((block, bIdx) => {
        const trimmed = block.trim();

        // Check if block is a markdown table
        if (trimmed.includes('|') && trimmed.split('\n').some(line => line.trim().startsWith('|'))) {
          const lines = trimmed.split('\n').filter(l => l.trim().startsWith('|'));
          if (lines.length >= 2) {
            const parseRow = (line) => line.split('|').map(c => c.trim()).filter((_, i, arr) => i > 0 && i < arr.length - 1);
            const headers = parseRow(lines[0]);
            // Skip line 1 if it is a separator (|---|---|)
            const bodyLines = lines.slice(lines[1].includes('---') ? 2 : 1);

            return (
              <div key={bIdx} className="my-2 overflow-x-auto rounded-xl border border-slate-200">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 font-medium text-slate-700 border-b border-slate-200">
                    <tr>
                      {headers.map((h, hIdx) => (
                        <th key={hIdx} className="px-3 py-2 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {bodyLines.map((rowLine, rIdx) => {
                      const cells = parseRow(rowLine);
                      return (
                        <tr key={rIdx} className="hover:bg-slate-50/50">
                          {cells.map((cell, cIdx) => (
                            <td key={cIdx} className="px-3 py-1.5 text-slate-700">{cell}</td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          }
        }

        // Check for bullet lists
        if (trimmed.split('\n').some(l => /^\s*[-*•]\s+/.test(l))) {
          const items = trimmed.split('\n').filter(l => l.trim().length > 0);
          return (
            <ul key={bIdx} className="my-1.5 space-y-1 pl-4 list-disc marker:text-green-600">
              {items.map((it, iIdx) => {
                const cleanItem = it.replace(/^\s*[-*•]\s+/, '');
                return <li key={iIdx}><InlineText text={cleanItem} /></li>;
              })}
            </ul>
          );
        }

        // Check for numbered lists
        if (trimmed.split('\n').some(l => /^\s*\d+\.\s+/.test(l))) {
          const items = trimmed.split('\n').filter(l => l.trim().length > 0);
          return (
            <ol key={bIdx} className="my-1.5 space-y-1 pl-4 list-decimal marker:text-green-700 marker:font-medium">
              {items.map((it, iIdx) => {
                const cleanItem = it.replace(/^\s*\d+\.\s+/, '');
                return <li key={iIdx}><InlineText text={cleanItem} /></li>;
              })}
            </ol>
          );
        }

        // Standard paragraph (process lines within block)
        const lines = block.split('\n');
        return (
          <p key={bIdx} className="leading-relaxed">
            {lines.map((line, lIdx) => (
              <span key={lIdx}>
                {lIdx > 0 && <br />}
                <InlineText text={line} />
              </span>
            ))}
          </p>
        );
      })}
    </div>
  );
}

/**
 * Handle inline markdown bolding (**bold**), code (`code`), and highlights
 */
function InlineText({ text }) {
  if (!text) return null;

  // Split by **bold** tokens
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);

  return (
    <>
      {parts.map((part, idx) => {
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={idx} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return <code key={idx} className="rounded bg-slate-100 px-1 py-0.5 font-mono text-xs text-green-800">{part.slice(1, -1)}</code>;
        }
        return <span key={idx}>{part}</span>;
      })}
    </>
  );
}

export default function ChatMessage({ message, currentUserName = 'Farmer' }) {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState(false);

  const isUser = message.role === 'user';
  const timeStr = formatTime(message.created_at);

  const handleCopy = () => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className={`flex flex-col gap-1.5 ${isUser ? 'items-end' : 'items-start'} animate-fadeIn`}>
      {/* Sender Header */}
      <div className={`flex items-center gap-2 px-1 text-xs text-slate-500 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        {isUser ? (
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700 shadow-sm">
            {currentUserName?.[0]?.toUpperCase() || 'F'}
          </div>
        ) : (
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-green-700 text-white shadow-sm">
            <WiDaySunny className="text-base" aria-hidden="true" />
          </div>
        )}

        {/* Sender Name */}
        <span className="font-medium text-slate-700">
          {isUser ? currentUserName : 'AgrixAI'}
        </span>

        {/* Timestamp */}
        {timeStr && <span className="text-[11px] text-slate-400">{timeStr}</span>}
      </div>

      {/* Message Bubble */}
      <div
        className={`relative max-w-[85%] rounded-2xl p-4 shadow-sm transition-all sm:max-w-[78%] ${
          isUser
            ? 'rounded-tr-none bg-green-50/90 border border-green-200/80 text-slate-900'
            : 'rounded-tl-none bg-white border border-slate-200/90 text-slate-800 shadow-card'
        }`}
      >
        <FormattedContent content={message.content} />

        {/* Assistant Action Bar (Copy & Helpful Feedback) */}
        {!isUser && (
          <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs text-slate-400">
            <span className="text-[11px] text-slate-400">AI Agronomist • Rule-Based Knowledge Base</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleCopy}
                title="Copy response"
                className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition"
              >
                {copied ? <FiCheck className="text-green-600" /> : <FiCopy />}
                <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
              </button>
              <button
                type="button"
                onClick={() => setLiked(!liked)}
                title={liked ? 'Marked helpful' : 'Mark as helpful'}
                className={`inline-flex items-center gap-1 rounded-md px-1.5 py-1 transition ${
                  liked ? 'text-green-700 font-medium' : 'text-slate-500 hover:bg-slate-100 hover:text-slate-800'
                }`}
              >
                {liked ? <FiCheckCircle className="text-green-600" /> : <FiThumbsUp />}
                <span className="text-[11px]">{liked ? 'Helpful' : 'Helpful'}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

