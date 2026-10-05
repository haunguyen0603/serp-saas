"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import locales from "./locale-options.json";

// Google Search gl/hl catalogs, retrieved 2026-10-05:
// https://serpapi.com/google-countries.json
// https://serpapi.com/google-languages.json
// Codes follow the API's country and language normalization.
type LocaleSelectProps = {
  name: string;
  defaultValue?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
};

function searchable(value: string) {
  return value.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase().trim();
}

function LocaleSelect({
  options,
  defaultValue = "",
  name,
  required,
  disabled,
  className = "",
  label,
  placeholder,
}: LocaleSelectProps & {
  options: Record<string, string>;
  label: string;
  placeholder: string;
}) {
  const id = useId();
  const listId = `${id}-options`;
  const fieldRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const lastSelection = useRef(defaultValue);
  const titleFor = (value: string) =>
    value
      ? `${options[value] ?? value} (${options[value] ? value : "current value"})`
      : "";
  const [code, setCode] = useState(defaultValue);
  const [text, setText] = useState(titleFor(defaultValue));
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [above, setAbove] = useState(false);
  const [popupHeight, setPopupHeight] = useState(240);
  const choices = useMemo(() => {
    const entries = Object.entries(options);
    if (defaultValue && !Object.hasOwn(options, defaultValue))
      entries.unshift([defaultValue, defaultValue]);
    return entries.map(([value, title]) => ({
      value,
      title: `${title} (${Object.hasOwn(options, value) ? value : "current value"})`,
      search: searchable(`${title} ${value}`),
    }));
  }, [options, defaultValue]);
  const query = code && text === titleFor(code) ? "" : searchable(text);
  const matches = choices.filter((choice) => choice.search.includes(query));

  useEffect(() => {
    inputRef.current?.setCustomValidity(
      required && !code ? `Select a ${label.toLowerCase()} from the list.` : "",
    );
  }, [code, required, label]);

  useEffect(() => {
    if (!open) return;
    function position() {
      const bounds = inputRef.current?.getBoundingClientRect();
      if (!bounds) return;
      const viewport = window.visualViewport;
      const top = viewport?.offsetTop ?? 0;
      const bottom = top + (viewport?.height ?? window.innerHeight);
      const below = bottom - bounds.bottom;
      const spaceAbove = bounds.top - top;
      const placeAbove = below < 200 && spaceAbove > below;
      setAbove(placeAbove);
      setPopupHeight(
        Math.max(80, Math.min(240, (placeAbove ? spaceAbove : below) - 8)),
      );
    }
    function outside(event: PointerEvent) {
      if (!fieldRef.current?.contains(event.target as Node)) setOpen(false);
    }
    position();
    document.addEventListener("pointerdown", outside);
    window.addEventListener("resize", position);
    window.addEventListener("scroll", position, true);
    window.visualViewport?.addEventListener("resize", position);
    window.visualViewport?.addEventListener("scroll", position);
    return () => {
      document.removeEventListener("pointerdown", outside);
      window.removeEventListener("resize", position);
      window.removeEventListener("scroll", position, true);
      window.visualViewport?.removeEventListener("resize", position);
      window.visualViewport?.removeEventListener("scroll", position);
    };
  }, [open]);

  useEffect(() => {
    if (open && active >= 0)
      listRef.current?.children[active]?.scrollIntoView?.({ block: "nearest" });
  }, [active, open, query]);

  function choose(value: string) {
    lastSelection.current = value;
    setCode(value);
    setText(titleFor(value));
    setOpen(false);
    setActive(-1);
    inputRef.current?.setCustomValidity("");
  }

  return (
    <div className="locale-field" ref={fieldRef}>
      <label htmlFor={id}>{label}</label>
      <div className="locale-control">
        <input
          ref={inputRef}
          id={id}
          className={`ui-input locale-search ${className}`}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          aria-activedescendant={
            open && matches[active] ? `${listId}-${active}` : undefined
          }
          placeholder={placeholder}
          value={text}
          required={required}
          disabled={disabled}
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
          onFocus={(event) => {
            setOpen(true);
            setActive(-1);
            event.currentTarget.select();
          }}
          onClick={() => setOpen(true)}
          onChange={(event) => {
            setText(event.target.value);
            setCode("");
            setOpen(true);
            setActive(0);
          }}
          onBlur={(event) => {
            if (!fieldRef.current?.contains(event.relatedTarget as Node))
              setOpen(false);
          }}
          onKeyDown={(event) => {
            if (event.nativeEvent.isComposing) return;
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
              event.preventDefault();
              setOpen(true);
              setActive((previous) => {
                if (!open || previous < 0)
                  return event.key === "ArrowDown" ? 0 : matches.length - 1;
                return Math.max(
                  0,
                  Math.min(
                    matches.length - 1,
                    previous + (event.key === "ArrowDown" ? 1 : -1),
                  ),
                );
              });
            } else if (event.key === "Enter" && open) {
              event.preventDefault();
              if (matches[active]) choose(matches[active].value);
            } else if (event.key === "Escape" && open) {
              event.preventDefault();
              setCode(lastSelection.current);
              setText(titleFor(lastSelection.current));
              setOpen(false);
              setActive(-1);
            }
          }}
        />
        <span className="locale-chevron" aria-hidden="true">
          ⌄
        </span>
        {open && (
          <div
            ref={listRef}
            id={listId}
            role="listbox"
            aria-label={label}
            className={`locale-options${above ? " locale-options-above" : ""}`}
            style={{ maxHeight: popupHeight }}
          >
            {matches.map((choice, index) => (
              <button
                type="button"
                role="option"
                id={`${listId}-${index}`}
                key={choice.value}
                tabIndex={-1}
                aria-selected={
                  active >= 0 ? active === index : code === choice.value
                }
                className="locale-option"
                onPointerDown={(event) => event.preventDefault()}
                onClick={() => choose(choice.value)}
              >
                {choice.title}
              </button>
            ))}
            {matches.length === 0 && (
              <p className="locale-no-matches" role="status">
                No matches found.
              </p>
            )}
          </div>
        )}
      </div>
      <input type="hidden" name={name} value={code} disabled={disabled} />
      {required && <span className="locale-required">Required</span>}
    </div>
  );
}

export function CountrySelect(props: LocaleSelectProps) {
  return (
    <LocaleSelect
      {...props}
      options={locales.countries}
      label="Country"
      placeholder="Select country"
    />
  );
}

export function LanguageSelect(props: LocaleSelectProps) {
  return (
    <LocaleSelect
      {...props}
      options={locales.languages}
      label="Language"
      placeholder="Select language"
    />
  );
}
