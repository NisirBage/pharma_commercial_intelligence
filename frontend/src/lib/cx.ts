/** Minimal classnames joiner — avoids a `clsx`/`classnames` dependency
 * for a need this small (M7.3 Sec. 2: no unnecessary dependencies). */
export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}
