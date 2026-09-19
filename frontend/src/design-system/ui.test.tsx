import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { expect, it, vi } from "vitest";
import {
  Button,
  FormField,
  Input,
  Select,
  Table,
  Tabs,
  StatusBadge,
  ErrorState,
  UsageMeter,
} from "./ui";

it("uses the shared fixed-height style for select controls", () => {
  render(
    <Select aria-label="Device" defaultValue="desktop">
      <option value="desktop">Desktop</option>
    </Select>,
  );
  expect(screen.getByRole("combobox", { name: "Device" })).toHaveClass(
    "ui-input",
    "ui-select",
  );
});

it("defers destructive work until confirmation and restores trigger focus", () => {
  const action = vi.fn();
  render(
    <Button
      confirmation="This removes the project and keywords."
      onClick={action}
    >
      Delete Project
    </Button>,
  );
  const trigger = screen.getByRole("button", { name: "Delete Project" });
  trigger.focus();
  fireEvent.click(trigger);
  expect(screen.getByRole("dialog", { name: "Confirm action" })).toBeVisible();
  expect(action).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep current state" }));
  expect(action).not.toHaveBeenCalled();
  expect(trigger).toHaveFocus();
  fireEvent.click(trigger);
  fireEvent.click(screen.getByRole("button", { name: "Confirm action" }));
  expect(action).toHaveBeenCalledTimes(1);
  expect(trigger).toHaveFocus();
});
it("dismisses a confirmation on the native Escape cancel event", () => {
  const action = vi.fn();
  render(
    <Button confirmation="Remove it?" onClick={action}>
      Remove
    </Button>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Remove" }));
  fireEvent(
    screen.getByRole("dialog"),
    new Event("cancel", { bubbles: true, cancelable: true }),
  );
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(action).not.toHaveBeenCalled();
});
it("supports keyboard tab selection and roving focus", () => {
  function Example() {
    const [value, setValue] = useState("all");
    return (
      <Tabs
        label="Rankings"
        value={value}
        onChange={setValue}
        items={[
          { value: "all", label: "All" },
          { value: "ranked", label: "Ranked" },
        ]}
      />
    );
  }
  render(<Example />);
  fireEvent.keyDown(screen.getByRole("tab", { name: "All" }), {
    key: "ArrowRight",
  });
  expect(screen.getByRole("tab", { name: "Ranked" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(screen.getByRole("tab", { name: "Ranked" })).toHaveFocus();
});
it("associates validation with the input", () => {
  render(
    <FormField label="Project name" error="Enter a name">
      <Input />
    </FormField>,
  );
  expect(screen.getByLabelText("Project name")).toHaveAttribute(
    "aria-invalid",
    "true",
  );
  expect(screen.getByLabelText("Project name")).toHaveAccessibleDescription(
    "Enter a name",
  );
});
it("keeps mobile table labels and textual statuses", () => {
  render(
    <Table>
      <thead>
        <tr>
          <th>Keyword</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>example</td>
          <td>
            <StatusBadge status="completed_with_errors" />
          </td>
        </tr>
      </tbody>
    </Table>,
  );
  expect(screen.getByText("example")).toHaveAttribute("data-label", "Keyword");
  expect(screen.getByText("Completed with errors")).toBeVisible();
});
it("offers retry without discarding the error message", () => {
  const retry = vi.fn();
  render(<ErrorState onRetry={retry}>Connection interrupted</ErrorState>);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(retry).toHaveBeenCalledOnce();
  expect(screen.getByRole("alert")).toHaveTextContent("Connection interrupted");
});
it("includes reserved usage in the progress without changing committed usage", () => {
  render(
    <UsageMeter label="Desktop checks" used={20} reserved={10} limit={100} />,
  );
  expect(screen.getByRole("progressbar")).toHaveAttribute("value", "30");
  expect(screen.getByText("20 / 100")).toBeVisible();
});
