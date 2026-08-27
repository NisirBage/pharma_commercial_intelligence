import { Link } from "react-router-dom";

interface NotFoundPageProps {
  message?: string;
}

export function NotFoundPage({ message }: NotFoundPageProps) {
  return (
    <section>
      <h1>Not found</h1>
      <p>{message ?? "The page you're looking for doesn't exist."}</p>
      <Link to="/">Return to Overview</Link>
    </section>
  );
}
