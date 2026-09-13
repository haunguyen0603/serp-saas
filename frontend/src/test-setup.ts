import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

// jsdom has no native dialog implementation; browser tests exercise focus trapping.
HTMLDialogElement.prototype.showModal = function () {
  this.open = true;
  this.querySelector<HTMLElement>("button, input, a")?.focus();
};
HTMLDialogElement.prototype.close = function () {
  this.open = false;
};
