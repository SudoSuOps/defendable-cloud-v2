import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <p className="font-mono text-sm uppercase tracking-widest text-honey-300">404</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-paper">This page isn't in the trail.</h1>
      <Link to="/" className="mt-6 rounded-md bg-honey-300 px-5 py-2.5 text-sm font-semibold text-ink hover:bg-honey-200">
        Back to the vault
      </Link>
    </div>
  );
}
