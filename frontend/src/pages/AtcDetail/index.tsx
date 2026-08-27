import { useParams } from "react-router-dom";
import { isKnownAtcClass } from "../../types/api";
import { NotFoundPage } from "../NotFound";

export function AtcDetailPage() {
  const { atcClass } = useParams<{ atcClass: string }>();

  if (!atcClass || !isKnownAtcClass(atcClass)) {
    return <NotFoundPage message={`"${atcClass}" is not a recognized ATC class.`} />;
  }

  return (
    <section>
      <h1>ATC Detail — {atcClass}</h1>
      <p>Scaffolding placeholder — implemented in M7.5.</p>
    </section>
  );
}
