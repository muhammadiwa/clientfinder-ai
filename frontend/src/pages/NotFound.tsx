import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n/id";

export function NotFoundPage() {
  const t = useT();
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="text-center">
        <h1 className="text-7xl font-bold text-slate-900">404</h1>
        <p className="mt-4 text-lg text-slate-600">{t.notFound.title}</p>
        <p className="mt-2 text-sm text-slate-400">{t.notFound.description}</p>
        <div className="mt-6">
          <Button asChild>
            <Link to="/dashboard">{t.notFound.goHome}</Link>
          </Button>
        </div>
      </div>
    </div>
  );
}
