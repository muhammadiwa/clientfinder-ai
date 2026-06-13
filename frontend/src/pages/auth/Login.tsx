import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";
import { Sparkles, ArrowRight } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { useLogin } from "@/hooks/useAuth";
import { isApiError } from "@/api/client";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useLogin();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login.mutateAsync({ email, password });
      toast.success("Welcome back!");
      navigate(from, { replace: true });
    } catch (error) {
      if (isApiError(error)) {
        const detail = error.response?.data?.detail;
        const message =
          typeof detail === "string" ? detail : "Invalid email or password";
        toast.error(message);
      } else {
        toast.error("Network error. Please try again.");
      }
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-5">
      {/* Left — branding panel */}
      <div className="hidden lg:flex lg:col-span-2 relative overflow-hidden bg-gradient-to-br from-violet-600 via-indigo-600 to-violet-700 p-12 flex-col justify-between text-white">
        {/* Decorative gradient orbs */}
        <div className="absolute top-0 right-0 h-[500px] w-[500px] bg-violet-400/30 rounded-full blur-3xl -translate-y-1/4 translate-x-1/4" />
        <div className="absolute bottom-0 left-0 h-[400px] w-[400px] bg-indigo-400/30 rounded-full blur-3xl translate-y-1/4 -translate-x-1/4" />
        <div className="absolute top-1/2 left-1/2 h-72 w-72 bg-fuchsia-400/20 rounded-full blur-3xl -translate-x-1/2 -translate-y-1/2" />

        <div className="relative z-10">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-lg bg-white/10 backdrop-blur flex items-center justify-center">
              <Sparkles className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold">ClientFinder</span>
          </div>

          <div className="mt-20 max-w-md">
            <h1 className="text-4xl font-bold leading-tight tracking-tight">
              Find your next client in minutes, not weeks.
            </h1>
            <p className="text-violet-100 mt-5 text-lg leading-relaxed">
              AI-powered lead generation built for Indonesian freelance
              developers. Discover UMKM that need software, score them
              automatically, and reach out at scale.
            </p>

            <div className="mt-10 space-y-3 text-sm text-violet-100/90">
              {[
                "Google Maps + Twitter + Threads prospecting",
                "Auto-scored leads with pain-point analysis",
                "Personalized outreach with human approval",
              ].map((item) => (
                <div key={item} className="flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-full bg-white/60" />
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>

        <p className="relative z-10 text-violet-200/70 text-xs">
          © 2026 ClientFinder · v0.1.0
        </p>
      </div>

      {/* Right — form */}
      <div className="lg:col-span-3 flex items-center justify-center p-6 bg-background relative">
        {/* Subtle grid pattern bg */}
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
                Welcome back
              </CardTitle>
              <CardDescription>
                Sign in to continue your lead generation
              </CardDescription>
            </CardHeader>
            <form onSubmit={handleSubmit}>
              <CardContent className="space-y-4 pt-4">
                <div className="space-y-2">
                  <label
                    htmlFor="email"
                    className="text-sm font-medium leading-none"
                  >
                    Email
                  </label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    autoFocus
                    disabled={login.isPending}
                    className="h-10"
                  />
                </div>
                <div className="space-y-2">
                  <label
                    htmlFor="password"
                    className="text-sm font-medium leading-none"
                  >
                    Password
                  </label>
                  <Input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                    disabled={login.isPending}
                    className="h-10"
                  />
                </div>
              </CardContent>
              <CardFooter className="flex flex-col space-y-4 pt-2">
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={login.isPending}
                >
                  {login.isPending ? (
                    "Signing in..."
                  ) : (
                    <>
                      Sign in
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground text-center">
                  No account?{" "}
                  <Link
                    to="/register"
                    className="text-primary font-medium hover:underline"
                  >
                    Create one
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
