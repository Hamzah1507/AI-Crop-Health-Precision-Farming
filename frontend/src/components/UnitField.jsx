// Numeric form field with a unit suffix, hint text and an accessible inline error.
export default function UnitField({ id, label, unit, value, onChange, hint, error, ...rest }) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  return (
    <div>
      <label className="label" htmlFor={id}>{label}</label>
      <div className="relative">
        <input id={id} type="number" inputMode="decimal" value={value} onChange={(e) => onChange(e.target.value)}
          aria-invalid={error ? true : undefined} aria-describedby={describedBy}
          className={`input ${unit ? 'pr-16' : ''}`} {...rest} />
        {unit && (
          <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-xs text-slate-500" aria-hidden="true">{unit}</span>
        )}
      </div>
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-xs text-red-600">{error}</p>
      ) : hint ? (
        <p id={`${id}-hint`} className="hint">{hint}</p>
      ) : null}
    </div>
  );
}
