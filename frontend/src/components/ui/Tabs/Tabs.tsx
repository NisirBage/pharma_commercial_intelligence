import type { KeyboardEvent, ReactNode } from "react";
import { useRef } from "react";
import { cx } from "../../../lib/cx";
import styles from "./Tabs.module.css";

export interface TabItem {
  value: string;
  label: string;
  icon?: ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  ariaLabel: string;
}

/** Generic, fully-controlled tabs — the component itself has no opinion
 * about labels or routing. Pages drive `value`/`onChange` from wherever
 * makes sense (e.g. a URL query param via useSearchParams — see M7.5),
 * so this component never hardcodes "Trends"/"ATC"/etc. (M7.3 Sec. 10). */
export function Tabs({ items, value, onChange, ariaLabel }: TabsProps) {
  const tabRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const currentIndex = items.findIndex((item) => item.value === value);
    if (currentIndex === -1) return;

    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % items.length;
    else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + items.length) % items.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = items.length - 1;

    if (nextIndex !== null) {
      event.preventDefault();
      const nextItem = items[nextIndex];
      if (!nextItem) return;
      onChange(nextItem.value);
      tabRefs.current[nextItem.value]?.focus();
    }
  }

  return (
    <div role="tablist" aria-label={ariaLabel} className={styles.tabList} onKeyDown={handleKeyDown}>
      {items.map((item) => {
        const selected = item.value === value;
        return (
          <button
            key={item.value}
            ref={(el) => {
              tabRefs.current[item.value] = el;
            }}
            id={`tab-${item.value}`}
            role="tab"
            type="button"
            aria-selected={selected}
            aria-controls={`tabpanel-${item.value}`}
            tabIndex={selected ? 0 : -1}
            className={cx(styles.tab, selected && styles.selected)}
            onClick={() => onChange(item.value)}
          >
            {item.icon && (
              <span className={styles.icon} aria-hidden="true">
                {item.icon}
              </span>
            )}
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
