# M6.5A design system

The authenticated application uses a light workspace theme defined in `frontend/src/design-system/tokens.css`. Existing public pages keep their previous appearance. The system is adopted by Projects, Keywords, Tracked Sites, Rankings, batch/schedule controls, Billing, account settings and Admin.

## Tokens and hierarchy

Semantic colors cover canvas, surface, muted surface, borders, primary/secondary/muted text, brand, success, warning, danger and information. Tailwind's `@theme inline` maps utility names to `--ds-*` variables. Shared components own their base appearance; feature utilities express layout rather than duplicating control styles.

Typography uses the existing system sans stack, 14px workspace body, 13px labels, 12px captions, responsive 26–32px page headings, 19px section headings and tabular numeric metrics. Spacing follows 4/8/12/16/24/32/48/64px. Radii are 6/10/16px with restrained card/dialog shadows. Status badges always include text.

## Shared API

`ui.tsx` owns Button (primary/secondary/ghost/danger; small/medium/large; loading/disabled), IconButton, Input, Select, Textarea, Checkbox, Radio, Switch, native datalist Combobox, FormField, FormError, Card, StatCard, Badge, StatusBadge, Table/DataTable, CursorPagination, Tabs, DropdownMenu, Popover, Tooltip, Dialog, ConfirmDialog, Drawer, Toast, Alert, Skeleton, Spinner, EmptyState, ErrorState and UsageMeter. The small inline SVG icon family uses consistent stroke widths; icon actions have accessible labels.

Primary actions use one brand-colored control per workflow; secondary work uses neutral controls, destructive actions use danger. Button `confirmation` defers its click callback until confirmation. Form submission needing confirmation uses an explicit ConfirmDialog with a captured payload (Admin replacement). Native form validation remains intact. Field errors stay visible; transient success messages announce politely and can be dismissed.

Native modal dialogs provide background inertness and browser focus trapping. Escape and close buttons dismiss; focus returns to the opening control. Tests polyfill only jsdom's missing native methods; real Chrome verification checks focus containment. Tabs support arrows, Home and End. Dropdowns use native details/summary and normal tab navigation, with Escape dismissal. FormField associates help/error text through aria-describedby.

## Responsive composition

The desktop shell has a fixed sidebar and context topbar. At 800px and below, navigation moves into a modal drawer. Content remains fluid with reduced gutters; cards collapse into columns. Below 600px, tables become labeled records using header-derived data-label attributes while retaining semantic table elements. Long content wraps, actions remain visible, and mobile buttons have at least 44px height. Reduced-motion preferences disable decorative animation. Usage progress includes committed plus reserved checks, with separate counts retained.

## Ownership and extension

Add reusable behavior to the design-system folder and product behavior to its feature folder. Keep query keys/API mutations in features. Use ErrorState for recoverable fetch failures, Skeleton for loading, EmptyState with a next step for no data, and persistent Alert for validation/entitlement errors. Never replace backend authorization with visual hiding. Do not expose provider routing, cloud configuration or credentials in customer screens.

Dark mode is intentionally deferred; this milestone supplies one consistent light application theme. Native controls and browser date/time rendering can vary by operating system. Formal assistive-technology certification is outside the executed checks; see the verification report for measured coverage.
