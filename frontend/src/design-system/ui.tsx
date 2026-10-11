"use client";

import {
  Children,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  type MouseEvent,
} from "react";

export function Icon({
  name = "grid",
  ...props
}: { name?: string } & React.SVGProps<SVGSVGElement>) {
  const paths: Record<string, string> = {
    grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    folder: "M3 7h7l2-3h9v16H3z",
    chart: "M4 20V4 M4 20h17 M8 15l4-5 4 2 5-8",
    globe: "M3 12h18 M12 3c6 5 6 13 0 18 M12 3c-6 5-6 13 0 18",
    wallet: "M3 5h17v15H3z M15 10h6v6h-6z",
    user: "M8 7a4 4 0 1 0 8 0a4 4 0 1 0-8 0 M4 21v-3a8 6 0 0 1 16 0v3",
    menu: "M4 6h16 M4 12h16 M4 18h16",
    close: "M6 6l12 12 M18 6L6 18",
    chevron: "M9 5l7 7-7 7",
    plus: "M12 5v14 M5 12h14",
    more: "M5 12h1 M11 12h1 M17 12h1",
    check: "M5 12l4 4L19 6",
    logout: "M9 4H3v16h6 M9 12h12 M16 7l5 5-5 5",
  };
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {name === "globe" && <circle cx="12" cy="12" r="9" />}
      <path d={paths[name] ?? paths.grid} />
    </svg>
  );
}

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  confirmation?: string;
};
export function Button({
  variant = "secondary",
  size = "md",
  loading,
  disabled,
  className = "",
  children,
  onClick,
  confirmation,
  ...props
}: ButtonProps) {
  const [event, setEvent] = useState<MouseEvent<HTMLButtonElement> | null>(
    null,
  );
  return (
    <>
      <button
        {...props}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        className={`ui-button ui-button--${variant} ui-button--${size} ${className}`}
        onClick={(e) => {
          if (confirmation) {
            e.preventDefault();
            setEvent(e);
          } else onClick?.(e);
        }}
      >
        {loading && <Spinner />}
        {children}
      </button>
      {confirmation && (
        <ConfirmDialog
          open={!!event}
          onClose={() => setEvent(null)}
          title="Confirm action"
          description={confirmation}
          onConfirm={() => {
            if (event) onClick?.(event);
            setEvent(null);
          }}
        />
      )}
    </>
  );
}
export function IconButton({
  label,
  icon,
  ...props
}: ButtonProps & { label: string; icon: string }) {
  return (
    <Button {...props} aria-label={label} title={label}>
      <Icon name={icon} />
    </Button>
  );
}
export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={`ui-input ${className}`} {...props} />;
}
export function Select({
  className = "",
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={`ui-input ui-select ${className}`} {...props} />;
}
export function Textarea({
  className = "",
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea className={`ui-input ui-textarea ${className}`} {...props} />
  );
}
export function Checkbox(props: InputHTMLAttributes<HTMLInputElement>) {
  return <Input {...props} type="checkbox" />;
}
export function Radio(props: InputHTMLAttributes<HTMLInputElement>) {
  return <Input {...props} type="radio" />;
}
export function Switch(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <Input
      {...props}
      role="switch"
      type="checkbox"
      className={`ui-switch ${props.className ?? ""}`}
    />
  );
}
export function Combobox({
  options,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { options: string[] }) {
  const id = useId();
  return (
    <>
      <Input {...props} list={id} />
      <datalist id={id}>
        {options.map((option) => (
          <option key={option} value={option} />
        ))}
      </datalist>
    </>
  );
}
export function FormField({
  label,
  help,
  error,
  required,
  children,
}: {
  label: string;
  help?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="ui-field">
      <label>
        {label}
        {required && <span aria-hidden="true"> *</span>}
        {Children.map(children, (child) =>
          isValidElement<InputHTMLAttributes<HTMLInputElement>>(child) ? (
            <child.type
              {...child.props}
              aria-describedby={help || error ? id : undefined}
              aria-invalid={!!error || undefined}
            />
          ) : (
            child
          ),
        )}
      </label>
      {(help || error) && (
        <p id={id} className={error ? "text-danger" : "text-secondary"}>
          {error || help}
        </p>
      )}
    </div>
  );
}
export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLElement>) {
  return <section className={`ui-card ${className}`} {...props} />;
}
export function PageHeader({
  title,
  description,
  eyebrow,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="app-heading">
      <div>
        {eyebrow && <p className="ui-caption app-heading-eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && (
          <p className="app-heading-description">{description}</p>
        )}
      </div>
      {actions && <div className="app-heading-actions">{actions}</div>}
    </div>
  );
}
export function StatCard({
  label,
  value,
  detail,
  icon,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
  icon?: string;
}) {
  return (
    <Card className="ui-stat">
      <div className="ui-stat-label">
        {label}
        {icon && <Icon name={icon} />}
      </div>
      <p className="ui-stat-value">{value}</p>
      {detail && <p className="text-secondary text-sm">{detail}</p>}
    </Card>
  );
}
export function Badge({
  tone = "neutral",
  className = "",
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: string }) {
  return (
    <span {...props} className={`ui-badge ui-badge--${tone} ${className}`} />
  );
}
export function StatusBadge({ status }: { status: string }) {
  const value = status.toLowerCase().replaceAll("_", " ");
  const tone = ["active", "completed", "succeeded", "ranked"].includes(value)
    ? "success"
    : ["running", "queued", "pending", "pro"].includes(value)
      ? "info"
      : ["failed", "expired"].includes(value)
        ? "danger"
        : ["paused", "completed with errors", "starter"].includes(value)
          ? "warning"
          : "neutral";
  return (
    <Badge tone={tone}>
      {value === "succeeded"
        ? "Completed"
        : value.replace(/^./, (c) => c.toUpperCase())}
    </Badge>
  );
}
export function Table({
  children,
  className = "",
  ...props
}: React.TableHTMLAttributes<HTMLTableElement>) {
  const ref = useRef<HTMLTableElement>(null);
  useEffect(() => {
    const table = ref.current;
    if (!table) return;
    const labels = Array.from(table.tHead?.rows[0]?.cells ?? []).map(
      (cell) => cell.textContent ?? "",
    );
    Array.from(table.tBodies).forEach((body) =>
      Array.from(body.rows).forEach((row) =>
        Array.from(row.cells).forEach((cell, index) =>
          cell.setAttribute("data-label", labels[index] ?? ""),
        ),
      ),
    );
  }, [children]);
  return (
    <div className="ui-table-wrap">
      <table ref={ref} {...props} className={`ui-table ${className}`}>
        {children}
      </table>
    </div>
  );
}
export const DataTable = Table;
export function CursorPagination({
  hasMore,
  loading,
  onNext,
  label = "Load more",
}: {
  hasMore: boolean;
  loading?: boolean;
  onNext: () => void;
  label?: string;
}) {
  return hasMore ? (
    <div className="ui-pagination">
      <Button loading={loading} onClick={onNext}>
        {label}
      </Button>
    </div>
  ) : null;
}
export function Tabs({
  items,
  value,
  onChange,
  label,
}: {
  items: { value: string; label: string }[];
  value: string;
  onChange: (value: string) => void;
  label: string;
}) {
  return (
    <div role="tablist" aria-label={label} className="ui-tabs">
      {items.map((item, index) => (
        <button
          key={item.value}
          role="tab"
          type="button"
          tabIndex={value === item.value ? 0 : -1}
          aria-selected={value === item.value}
          onClick={() => onChange(item.value)}
          onKeyDown={(e) => {
            const next =
              e.key === "ArrowRight"
                ? (index + 1) % items.length
                : e.key === "ArrowLeft"
                  ? (index - 1 + items.length) % items.length
                  : e.key === "Home"
                    ? 0
                    : e.key === "End"
                      ? items.length - 1
                      : -1;
            if (next >= 0) {
              e.preventDefault();
              onChange(items[next].value);
              (
                e.currentTarget.parentElement?.children[next] as HTMLElement
              )?.focus();
            }
          }}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}
export function Dialog({
  open,
  onClose,
  title,
  children,
  drawer = false,
  className = "",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  drawer?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    const previous = document.activeElement as HTMLElement | null;
    if (open && !dialog.open) dialog.showModal();
    else if (!open && dialog.open) dialog.close();
    return () => {
      if (dialog.open) dialog.close();
      if (open && previous?.isConnected) previous.focus();
    };
  }, [open]);
  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={`ui-dialog${drawer ? " ui-drawer" : ""} ${className}`}
      onKeyDown={(e) => {
        if (e.key !== "Tab") return;
        const controls = Array.from(
          e.currentTarget.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex="0"]',
          ),
        ).filter((el) => el.getClientRects().length > 0);
        const first = controls[0],
          last = controls[controls.length - 1];
        if (!first) {
          e.preventDefault();
          return;
        }
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          const box = e.currentTarget.getBoundingClientRect();
          if (
            e.clientX < box.left ||
            e.clientX > box.right ||
            e.clientY < box.top ||
            e.clientY > box.bottom
          )
            onClose();
        }
      }}
    >
      <div className="ui-dialog-header">
        <h2 id={titleId}>{title}</h2>
        <IconButton
          label="Close dialog"
          icon="close"
          variant="ghost"
          type="button"
          onClick={onClose}
        />
      </div>
      {children}
    </dialog>
  );
}
export function Drawer(props: Omit<Parameters<typeof Dialog>[0], "drawer">) {
  return <Dialog {...props} drawer />;
}
export function ConfirmDialog({
  open,
  onClose,
  title,
  description,
  onConfirm,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description: string;
  onConfirm: () => void;
}) {
  return (
    <Dialog open={open} onClose={onClose} title={title}>
      <p>{description}</p>
      <div className="ui-dialog-actions">
        <Button type="button" onClick={onClose}>
          Keep current state
        </Button>
        <Button type="button" variant="danger" onClick={onConfirm}>
          Confirm action
        </Button>
      </div>
    </Dialog>
  );
}
export function DropdownMenu({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDetailsElement>(null);
  return (
    <details
      className="ui-dropdown"
      ref={ref}
      onKeyDown={(e) => {
        if (e.key === "Escape" && ref.current) {
          ref.current.open = false;
          ref.current.querySelector("summary")?.focus();
        }
      }}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget))
          e.currentTarget.open = false;
      }}
    >
      <summary aria-label={label}>
        {label}
        <Icon name="more" />
      </summary>
      <div className="ui-dropdown-content">{children}</div>
    </details>
  );
}
export function Popover({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return <DropdownMenu label={label}>{children}</DropdownMenu>;
}
export function Tooltip({
  text,
  children,
}: {
  text: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <span className="ui-tooltip" tabIndex={0} aria-describedby={id}>
      {children}
      <span id={id} role="tooltip">
        {text}
      </span>
    </span>
  );
}
export function Alert({
  children,
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div role="alert" {...props} className={`ui-alert ${className}`}>
      {children}
    </div>
  );
}
export function FormError({ children }: { children: ReactNode }) {
  return <Alert>{children}</Alert>;
}
export function Spinner() {
  return <span className="ui-spinner" aria-hidden="true" />;
}
export function Skeleton({
  label = "Loading…",
  rows = 3,
}: {
  label?: string;
  rows?: number;
}) {
  return (
    <div role="status" aria-label={label} className="ui-skeleton">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} />
      ))}
    </div>
  );
}
export function EmptyState({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card className="ui-empty">
      <span className="ui-empty-icon">
        <Icon name="folder" />
      </span>
      <h2>{title}</h2>
      <p>{children}</p>
      {action}
    </Card>
  );
}
export function ErrorState({
  retryLabel = "Retry",
  title = "Unable to load this view",
  children,
  onRetry,
}: {
  title?: string;
  children?: ReactNode;
  retryLabel?: string;
  onRetry?: () => void;
}) {
  return (
    <Alert>
      <h2>{title}</h2>
      <p>
        {children ?? "Try again. If the problem continues, return to Overview."}
      </p>
      {onRetry && <Button onClick={onRetry}>{retryLabel}</Button>}
    </Alert>
  );
}
export function Toast({ children }: { children: ReactNode }) {
  const [dismissed, setDismissed] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setDismissed(true), 6000);
    return () => clearTimeout(timer);
  }, []);
  return dismissed ? null : (
    <div role="status" className="ui-toast">
      <Icon name="check" />
      {children}
      <IconButton
        label="Dismiss notification"
        icon="close"
        variant="ghost"
        onClick={() => setDismissed(true)}
      />
    </div>
  );
}
export function UsageMeter({
  label,
  used,
  limit,
  reserved = 0,
}: {
  label: string;
  used: number;
  limit: number;
  reserved?: number;
}) {
  const percentage = limit
    ? Math.min(100, Math.round(((used + reserved) / limit) * 100))
    : 0;
  return (
    <div className="ui-meter">
      <div>
        <span>{label}</span>
        <strong>
          {used.toLocaleString("en-US")} / {limit.toLocaleString("en-US")}
        </strong>
      </div>
      <progress max={100} value={percentage} aria-label={`${label} usage`} />
      <p>
        {percentage}% of allowance
        {reserved > 0 ? ` · ${reserved.toLocaleString("en-US")} reserved` : ""}
      </p>
    </div>
  );
}
