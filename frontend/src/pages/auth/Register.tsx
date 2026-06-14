import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles, ArrowRight, Check } from "lucide-react";
import { toast } from "react-hot-toast";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { FormField, Input } from "@/components/ui/input";
import { useRegister } from "@/hooks/useAuth";
import { isApiError } from "@/api/client";
import { formatApiError, formatFieldError } from "@/lib/formatError";
import { useT } from "@/i18n";

const PERKS = [
  "Penemuan prospek bertenaga AI dari Google Maps, Twitter, Threads",
  "Penilaian prospek otomatis dengan analisis masalah",
  "Outreach yang dipersonalisasi dengan persetujuan manusia",
];

export function RegisterPage() {
  const t = useT();
  const navigate = useNavigate();
  const register = useRegister();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<{
    fullName?: string;
    email?: string;
    password?: string;
  }>({});
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFieldErrors({});
    // Client-side validation
    const errs: typeof fieldErrors = {};
    if (!fullName.trim()) {
      errs.fullName = formatFieldError("fullName", "required");
    }
    if (!email.trim()) {
      errs.email = formatFieldError("email", "required");
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errs.email = formatFieldError("email", "invalid");
    }
    if (!password) {
      errs.password = formatFieldError("password", "required");
    } else if (password.length < 8) {
      errs.password = formatFieldError("password", "tooShort", { min: 8 });
    }
    if (Object.keys(errs).length > 0) {
      setFieldErrors(errs);
      return;
    }
    setSubmitting(true);
    try {
      await register.mutateAsync({ email, password, full_name: fullName });
      toast.success(t.auth.accountCreated);
      navigate("/login");
    } catch (error) {
      if (isApiError(error)) {
        toast.error(formatApiError(error));
      } else {
        toast.error(t.auth.networkError);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-5">
      {/* Left — branding panel (mirrors Login) */}
      <div className="hidden lg:flex lg:col-span-2 relative overflow-hidden bg-gradient-to-br from-violet-600 via-indigo-600 to-violet-700 p-12 flex-col justify-between text-white">
        {/* Decorative gradient orbs */}
        <div className="absolute top-0 right-0 h-[500px] w-[500px] bg-violet-400/30 rounded-full blur-3xl -translate-y-1/4 translate-x-1/4" />
        <div className="absolute bottom-0 left-0 h-[400px] w-[400px] bg-indigo-400/30 rounded-full blur-3xl translate-y-1/4 -translate-x-1/4" />
        <div className="absolute top-1/2 left-1/2 h-72 w-72 bg-fuchsia-400/20 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />

        <div className="relative z-10">
          <Link to="/dashboard" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-lg bg-white/10 backdrop-blur flex items-center justify-center transition-transform duration-200 group-hover:scale-105">
              <Sparkles className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold">ClientFinder</span>
          </Link>

          <div className="mt-20 max-w-md">
            <h1 className="text-4xl font-bold leading-tight tracking-tight">
              Start finding clients on autopilot.
            </h1>
            <p className="text-violet-100 mt-5 text-lg leading-relaxed">
              Create your account in 30 seconds. Let our AI agents discover
              and qualify your next client within a week.
            </p>

            <div className="mt-10 space-y-3 text-sm text-violet-100/90">
              {PERKS.map((perk) => (
                <div key={perk} className="flex items-center gap-2.5">
                  <div className="h-5 w-5 rounded-full bg-white/15 flex items-center justify-center flex-shrink-0">
                    <Check className="h-3 w-3" strokeWidth={3} />
                  </div>
                  {perk}
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="relative z-10 text-violet-200/70 text-xs">
          © 2026 ClientFinder · v0.1.0
        </p>
      </div>

      {/* Right — form (mirrors Login) */}
      <div className="lg:col-span-3 flex items-center justify-center p-6 bg-background relative">
        <div className="absolute inset-0 bg-grid-pattern opacity-30 pointer-events-none" />

        <div className="relative w-full max-w-md">
          {/* Mobile logo (visible only on small screens) */}
          <div className="flex lg:hidden items-center gap-2 mb-8 justify-center">
            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold">ClientFinder</span>
          </div>

          <Card className="border-0 shadow-none bg-transparent">
            <CardHeader className="space-y-2">
              <CardTitle className="text-2xl tracking-tight">
                Create your account
              </CardTitle>
              <CardDescription>
                First user automatically becomes the workspace owner
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4 pt-4">
                <FormField
                  label={t.auth.fullName}
                  required
                  error={fieldErrors.fullName}
                >
                  <Input
                    placeholder="Nama Anda"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    autoComplete="name"
                    autoFocus
                    disabled={submitting}
                    className="h-10"
                  />
                </FormField>
                <FormField
                  label={t.auth.email}
                  required
                  error={fieldErrors.email}
                >
                  <Input
                    type="email"
                    placeholder="anda@contoh.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    disabled={submitting}
                    className="h-10"
                  />
                </FormField>
                <FormField
                  label={t.auth.password}
                  required
                  hint="Minimal 8 karakter"
                  error={fieldErrors.password}
                >
                  <Input
                    type="password"
                    placeholder="Min 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    disabled={submitting}
                    className="h-10"
                  />
                </FormField>
              </CardContent>
              <CardFooter className="flex flex-col space-y-4 pt-2">
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={register.isPending}
                >
                  {submitting ? (
                    "Creating account…"
                  ) : (
                    <>
                      Create account
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground text-center">
                  Already have an account?{" "}
                  <Link
                    to="/login"
                    className="text-primary font-medium hover:underline"
                  >
                    Sign in
                  </Link>
                </p>
              </CardFooter>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
