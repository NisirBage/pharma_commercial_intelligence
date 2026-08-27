import { useParams } from "react-router-dom";
import { isKnownAtcClass } from "../../types/api";
import { NotFoundPage } from "../NotFound";

export function ForecastingPage() {
  const { atcClass } = useParams<{ atcClass?: string }>();

  if (atcClass && !isKnownAtcClass(atcClass)) {
    return <NotFoundPage message={`"${atcClass}" is not a recognized ATC class.`} />;
  }

  return (
    <section>
      <h1>Forecasting {atcClass ? `— ${atcClass}` : "— Aggregate"}</h1>
      <p>Scaffolding placeholder — implemented in M7.6.</p>
    </section>
  );
}
