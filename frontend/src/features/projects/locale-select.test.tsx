import { fireEvent, render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { CountrySelect, LanguageSelect } from "./locale-select";

function view(defaultValue?: string) {
  render(
    <form aria-label="Locales">
      <CountrySelect name="country" required defaultValue={defaultValue} />
      <LanguageSelect name="language" required />
      <button type="submit">Save</button>
    </form>,
  );
  return screen.getByRole("form", { name: "Locales" }) as HTMLFormElement;
}

it("starts empty and submits only selected codes, not search text", () => {
  const form = view();
  const country = screen.getByRole("combobox", { name: "Country" });
  const language = screen.getByRole("combobox", { name: "Language" });
  expect(country).toHaveAttribute("placeholder", "Select country");
  expect(language).toHaveAttribute("placeholder", "Select language");
  expect(new FormData(form).get("country")).toBe("");
  expect(form.checkValidity()).toBe(false);
  fireEvent.change(country, { target: { value: "vietnam" } });
  expect(new FormData(form).get("country")).toBe("");
  expect(country).toBeInvalid();
  fireEvent.click(screen.getByRole("option", { name: "Vietnam (VN)" }));
  expect(country).toHaveValue("Vietnam (VN)");
  expect(country).toBeValid();
  expect(country).toHaveAttribute("aria-expanded", "false");
  fireEvent.change(language, { target: { value: "VI" } });
  fireEvent.click(screen.getByRole("option", { name: "Vietnamese (vi)" }));
  expect(form.checkValidity()).toBe(true);
  expect(Object.fromEntries(new FormData(form))).toEqual({
    country: "VN",
    language: "vi",
  });
});

it("filters names without accents and rejects unmatched free text", () => {
  const form = view();
  const country = screen.getByRole("combobox", { name: "Country" });
  fireEvent.change(country, { target: { value: "VIỆTNAM" } });
  expect(screen.getByRole("option", { name: "Vietnam (VN)" })).toBeVisible();
  fireEvent.change(country, { target: { value: "not a country" } });
  expect(screen.getByRole("status")).toHaveTextContent("No matches found.");
  expect(screen.queryByRole("option")).not.toBeInTheDocument();
  fireEvent.keyDown(country, { key: "Enter" });
  expect(new FormData(form).get("country")).toBe("");
  expect(country).toBeInvalid();
});

it("supports keyboard selection and Escape restores the last selection", () => {
  const form = view("VN");
  const country = screen.getByRole("combobox", { name: "Country" });
  fireEvent.focus(country);
  fireEvent.keyDown(country, { key: "Enter" });
  expect(new FormData(form).get("country")).toBe("VN");
  fireEvent.change(country, { target: { value: "United Kingdom" } });
  const list = screen.getByRole("listbox", { name: "Country" });
  expect(within(list).getAllByRole("option")).toHaveLength(2);
  fireEvent.keyDown(country, { key: "ArrowDown" });
  expect(
    document.getElementById(country.getAttribute("aria-activedescendant")!),
  ).toHaveTextContent("United Kingdom (GB)");
  fireEvent.keyDown(country, { key: "Enter" });
  expect(country).toHaveValue("United Kingdom (GB)");
  expect(new FormData(form).get("country")).toBe("GB");
  fireEvent.change(country, { target: { value: "Vietnam" } });
  fireEvent.keyDown(country, { key: "Escape" });
  expect(country).toHaveValue("United Kingdom (GB)");
  expect(new FormData(form).get("country")).toBe("GB");
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
});

it("closes on outside interaction or leaving the field and ignores IME Enter", () => {
  view();
  const country = screen.getByRole("combobox", { name: "Country" });
  fireEvent.change(country, { target: { value: "Vietnam" } });
  fireEvent.keyDown(country, { key: "Enter", isComposing: true });
  expect(country).toHaveValue("Vietnam");
  expect(screen.getByRole("listbox")).toBeVisible();
  fireEvent.pointerDown(screen.getByRole("button", { name: "Save" }));
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  fireEvent.focus(country);
  fireEvent.blur(country, {
    relatedTarget: screen.getByRole("combobox", { name: "Language" }),
  });
  expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
});
