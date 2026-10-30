// A white card with an icon-tile heading, used to group related form fields or results.
export default function SectionCard({ icon: Icon, title, description, actions, children, className = '', bodyClassName = 'p-5' }) {
  return (
    <section className={`card flex flex-col ${className}`}>
      {(title || actions) && (
        <header className="flex items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
          <div className="flex min-w-0 items-start gap-3">
            {Icon && <span className="icon-tile-sm" aria-hidden="true"><Icon /></span>}
            <div className="min-w-0">
              <h2 className="section-title">{title}</h2>
              {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
            </div>
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className={`flex-1 ${bodyClassName}`}>{children}</div>
    </section>
  );
}
