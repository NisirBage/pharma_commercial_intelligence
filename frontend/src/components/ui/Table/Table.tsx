import type { KeyboardEvent, ReactNode } from "react";
import { cx } from "../../../lib/cx";
import styles from "./Table.module.css";

export interface TableColumn<T> {
  key: string;
  header: string;
  align?: "start" | "end";
  width?: string;
  render: (row: T) => ReactNode;
}

export interface TableProps<T> {
  columns: TableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  density?: "compact" | "default";
  stickyHeader?: boolean;
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  caption?: string;
}

/** A lightweight enterprise table — no data-grid dependency. Wide content
 * scrolls within its own container (never the page body), per M7.3
 * Sec. 9/22. */
export function Table<T>({
  columns,
  rows,
  rowKey,
  density = "default",
  stickyHeader = false,
  onRowClick,
  emptyMessage = "No data available.",
  caption,
}: TableProps<T>) {
  function handleRowKeyDown(event: KeyboardEvent<HTMLTableRowElement>, row: T) {
    if (!onRowClick) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onRowClick(row);
    }
  }

  return (
    <div className={styles.scrollContainer}>
      <table className={cx(styles.table, density === "compact" && styles.compact)}>
        {caption && <caption className="visually-hidden">{caption}</caption>}
        <thead className={cx(stickyHeader && styles.stickyHeader)}>
          <tr>
            {columns.map((col) => (
              <th key={col.key} scope="col" style={col.width ? { width: col.width } : undefined} className={col.align === "end" ? styles.alignEnd : undefined}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className={styles.emptyCell}>
                {emptyMessage}
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={cx(onRowClick && styles.interactiveRow)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={onRowClick ? (event) => handleRowKeyDown(event, row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? "button" : undefined}
              >
                {columns.map((col) => (
                  <td key={col.key} className={col.align === "end" ? styles.alignEnd : undefined}>
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
