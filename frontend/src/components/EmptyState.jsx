// Friendly placeholder for "nothing here yet" screens.
export default function EmptyState({ icon: Icon, title, description, children, compact = false }) {
  return (
    <div className={`text-center ${compact ? 'py-8 px-4' : 'py-14 px-6'}`}>
      {Icon && (
        <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-green-50 text-green-700 text-lg" aria-hidden="true">
          <Icon />
        </div>
      )}
      <p className="text-sm font-medium text-slate-800">{title}</p>
      {description && <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-slate-500">{description}</p>}
      {children && <div className="mt-4 flex flex-wrap justify-center gap-2">{children}</div>}
    </div>
  );
}
