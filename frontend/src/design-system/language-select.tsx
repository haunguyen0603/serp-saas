"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useId, useRef } from "react";
import { localePath, publicLocale } from "@/lib/public-locales";
import { siteHref } from "@/lib/site";

const languages = [
  { locale: "en", label: "English", flag: "/flags/us.svg" },
  { locale: "vi", label: "Tiếng Việt", flag: "/flags/vi.svg" },
] as const;

export function LanguageSelect({ path }: { path: string }) {
  const ref = useRef<HTMLDetailsElement>(null);
  const labelId = useId();
  const locale = publicLocale(path);
  const current = languages.find((language) => language.locale === locale)!;
  useEffect(() => {
    function outside(event: PointerEvent) {
      if (
        event.target instanceof Node &&
        !ref.current?.contains(event.target) &&
        ref.current
      )
        ref.current.open = false;
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  return (
    <details
      className="public-language-select ui-dropdown"
      ref={ref}
      onKeyDown={(event) => {
        if (event.key === "Escape" && ref.current?.open) {
          event.preventDefault();
          ref.current.open = false;
          ref.current.querySelector("summary")?.focus();
        }
      }}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget))
          event.currentTarget.open = false;
      }}
    >
      <summary aria-label="Change language" aria-describedby={labelId}>
        <Image
          src={current.flag}
          alt=""
          aria-hidden="true"
          width={22}
          height={15}
        />
        <span id={labelId} lang={current.locale}>
          {current.label}
        </span>
        <svg
          className="language-select-chevron"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </summary>
      <nav
        className="ui-dropdown-content"
        aria-label={locale === "vi" ? "Chọn ngôn ngữ" : "Language options"}
      >
        {languages.map((language) => (
          <Link
            key={language.locale}
            href={siteHref(localePath(path, language.locale))}
            hrefLang={language.locale}
            lang={language.locale}
            aria-current={language.locale === locale ? "page" : undefined}
            onClick={() => {
              if (ref.current) ref.current.open = false;
            }}
          >
            <Image
              src={language.flag}
              alt=""
              aria-hidden="true"
              width={22}
              height={15}
            />
            <span>{language.label}</span>
            {language.locale === locale && (
              <span className="language-select-current" aria-hidden="true">
                ✓
              </span>
            )}
          </Link>
        ))}
      </nav>
    </details>
  );
}
