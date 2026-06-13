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
    <div className="min-h-screen flex items-center justify-center bg-brand-gradient-soft p-4 relative">
      <div className="absolute inset-0 bg-grid-pattern opacity-40 pointer-events-none" />

      <div className="absolute top-0 right-0 h-96 w-96 bg-violet-300/30 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
      <div className="absolute bottom-0 left-0 h-96 w-96 bg-indigo-300/30 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />

      <Card className="relative w-full max-w-2xl border-0 shadow-xl">
        <CardHeader className="text-center space-y-3 pb-2">
          <div className="mx-auto h-12 w-12 rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center text-white shadow-glow-sm">
            <Sparkles className="h-6 w-6" />
          </div>
          <div>
            <CardTitle className="text-2xl tracking-tight">
              Create your account
            </CardTitle>
            <CardDescription className="mt-1">
              First user automatically becomes the workspace owner
            </CardDescription>
          </div>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6 pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Full name</label>
                <Input
                  placeholder="Your name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  disabled={register.isPending}
                  className="h-10"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={register.isPending}
                  className="h-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <Input
                type="password"
                placeholder="Min 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                disabled={register.isPending}
                className="h-10"
              />
              <p className="text-xs text-muted-foreground">
                At least 8 characters. Use a mix of letters, numbers, and
                symbols for a stronger password.
              </p>
            </div>

            <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                What you get
              </p>
              {PERKS.map((perk) => (
                <div
                  key={perk}
                  className="flex items-start gap-2 text-sm"
                >
                  <div className="h-4 w-4 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <Check className="h-2.5 w-2.5" strokeWidth={4} />
                  </div>
                  <span className="text-foreground">{perk}</span>
                </div>
              ))}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-3 pt-2">
            <Button
              type="submit"
              className="w-full"
              size="lg"
              disabled={register.isPending}
            >
              {register.isPending ? (
                "Creating account..."
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
  );
}
