import { AlertTriangle, CheckCircle2, Clock, HelpCircle, XCircle } from "lucide-react";
import { Badge, type BadgeVariant } from "../Badge/Badge";

export type Status = "healthy" | "warning" | "error" | "available" | "unavailable" | "pending";

const STATUS_CONFIG: Record<Status, { label: string; variant: BadgeVariant; Icon: typeof CheckCircle2 }> = {
  healthy: { label: "Healthy", variant: "success", Icon: CheckCircle2 },
  available: { label: "Available", variant: "success", Icon: CheckCircle2 },
  warning: { label: "Warning", variant: "warning", Icon: AlertTriangle },
  error: { label: "Error", variant: "danger", Icon: XCircle },
  unavailable: { label: "Unavailable", variant: "danger", Icon: XCircle },
  pending: { label: "Pending", variant: "neutral", Icon: Clock },
};

export interface StatusBadgeProps {
  status: Status;
  /** Overrides the default label text while keeping the status's icon/color. */
  label?: string;
}

/** Status is never communicated by color alone — every StatusBadge pairs
 * an icon with text (M7.3 Sec. 8/23). */
export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, variant: "neutral" as BadgeVariant, Icon: HelpCircle };
  const { Icon } = config;
  return (
    <Badge variant={config.variant}>
      <Icon size={12} aria-hidden="true" />
      {label ?? config.label}
    </Badge>
  );
}
