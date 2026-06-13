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
import { Input } from "@/components/ui/input";
import { useRegister } from "@/hooks/useAuth";
import { isApiError } from "@/api/client";

const PERKS = [
  "AI-powered prospect discovery from Google Maps, Twitter, Threads",
  "Automatic lead scoring with pain-point analysis",
  "Personalized outreach with human-in-the-loop approval",
];

export function RegisterPage() {
  const navigate = useNavigate();
  const register = useRegister();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      toast.error("Password must be at least 8 characters");
      return;
    }
    try {
      await register.mutateAsync({ email, password, full_name: fullName });
      toast.success("Account created! Please sign in.");
      navigate("/login");
    } catch (error) {
      if (isApiError(error)) {
        const detail = error.response?.data?.detail;
        const message =
          typeof detail === "string" ? detail : "Could not create account";
        toast.error(message);
      } else {
        toast.error("Network error. Please try again.");
      }
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
                <div className="space-y-2">
                  <label
                    htmlFor="full_name"
                    className="text-sm font-medium leading-none"
                  >
                    Full name
                  </label>
                  <Input
                    id="full_name"
                    placeholder="Your name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    autoComplete="name"
                    autoFocus
                    disabled={register.isPending}
                    className="h-10"
                  />
                </div>
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
                    disabled={register.isPending}
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
                    placeholder="Min 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    disabled={register.isPending}
                    className="h-10"
                  />
                  <p className="text-xs text-muted-foreground">
                    At least 8 characters. Use a mix of letters, numbers, and
                    symbols for a stronger password.
                  </p>
                </div>
              </CardContent>
              <CardFooter className="flex flex-col space-y-4 pt-2">
                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={register.isPending}
                >
                  {register.isPending ? (
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
