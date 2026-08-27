import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Table, type TableColumn } from "./Table";

interface Row {
  id: string;
  atcClass: string;
  demand: number;
}

const columns: TableColumn<Row>[] = [
  { key: "atcClass", header: "ATC Class", render: (row) => row.atcClass },
  { key: "demand", header: "Demand", align: "end", render: (row) => row.demand.toFixed(1) },
];

const rows: Row[] = [
  { id: "1", atcClass: "N02BE", demand: 63005.4 },
  { id: "2", atcClass: "R03", demand: 11608.8 },
];

describe("Table", () => {
  it("renders column headers", () => {
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} />);
    expect(screen.getByRole("columnheader", { name: "ATC Class" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Demand" })).toBeInTheDocument();
  });

  it("renders one row per data item", () => {
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} />);
    expect(screen.getByText("N02BE")).toBeInTheDocument();
    expect(screen.getByText("R03")).toBeInTheDocument();
    expect(screen.getByText("63005.4")).toBeInTheDocument();
  });

  it("shows the empty message when there are no rows", () => {
    render(<Table columns={columns} rows={[]} rowKey={(r) => r.id} emptyMessage="No anomalies detected." />);
    expect(screen.getByText("No anomalies detected.")).toBeInTheDocument();
  });

  it("calls onRowClick when an interactive row is clicked", async () => {
    const onRowClick = vi.fn();
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} onRowClick={onRowClick} />);
    await userEvent.click(screen.getByText("N02BE"));
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it("supports keyboard activation of interactive rows", async () => {
    const onRowClick = vi.fn();
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} onRowClick={onRowClick} />);
    const interactiveRows = screen.getAllByRole("button");
    interactiveRows[0]?.focus();
    await userEvent.keyboard("{Enter}");
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it("does not mark rows as interactive when onRowClick is not provided", () => {
    render(<Table columns={columns} rows={rows} rowKey={(r) => r.id} />);
    expect(screen.queryAllByRole("button")).toHaveLength(0);
  });
});
