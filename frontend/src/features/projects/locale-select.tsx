import type { SelectHTMLAttributes } from "react";
import { Select } from "@/design-system/ui";
import locales from "./locale-options.json";

// Google Search gl/hl catalogs, retrieved 2026-10-05:
// https://serpapi.com/google-countries.json
// https://serpapi.com/google-languages.json
// Codes follow the API's country and language normalization.
type LocaleSelectProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  "children" | "defaultValue" | "value" | "multiple"
> & { defaultValue: string };

function LocaleSelect({
  options,
  defaultValue,
  ...props
}: LocaleSelectProps & { options: Record<string, string> }) {
  return (
    <Select {...props} defaultValue={defaultValue}>
      {defaultValue && !Object.hasOwn(options, defaultValue) && (
        <option value={defaultValue}>{defaultValue} (current value)</option>
      )}
      {Object.entries(options).map(([code, label]) => (
        <option key={code} value={code}>
          {label} ({code})
        </option>
      ))}
    </Select>
  );
}

export function CountrySelect(props: LocaleSelectProps) {
  return <LocaleSelect {...props} options={locales.countries} />;
}

export function LanguageSelect(props: LocaleSelectProps) {
  return <LocaleSelect {...props} options={locales.languages} />;
}
