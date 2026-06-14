import { forwardRef, useId, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import { Label } from "@/components/ui/input";

/**
 * FormField — single source of truth for form inputs.
 *
 * Combines:
 * - Label (auto-generated id pairing via useId, so
 *   htmlFor + id are always correct)
 * - Input (or any custom input)
 * - Optional hint text (below the input)
 * - Optional inline error (rose-600, replaces hint)
 * - Required indicator (red asterisk)
 *
 * A11y:
 * - Label is associated with the input via htmlFor + id
 * - Error message has aria-describedby on the input
 * - aria-invalid="true" when error is present
 * - Use forwardRef so react-hook-form can attach ref
 *
 * Usage:
 *   <FormField label="Email" error={errors.email?.message} required>
 *     <Input type="email" {...register("email")} />
 *   </FormField>
 */
export interface FormFieldProps {
  label: string;
  hint?: string;
  error?: string | null | undefined;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export const FormField = forwardRef<HTMLDivElement, FormFieldProps>(
  ({ label, hint, error, required, children, className }, ref) => {
    const generatedId = useId();
    const fieldId = `field-${generatedId}`;
    const hintId = hint ? `${fieldId}-hint` : undefined;
    const errorId = error ? `${fieldId}-error` : undefined;

    return (
      <div ref={ref} className={cn("space-y-1.5", className)}>
        <Label
          htmlFor={fieldId}
          className="flex items-center gap-1"
        >
          {label}
          {required && (
            <span className="text-rose-500" aria-label="wajib diisi">
              *
            </span>
          )}
        </Label>
        {/* The child input is cloned with our id + aria attrs.
            We don't import the child so any input component
            (Input, Textarea, Combobox) can be used. */}
        <FieldChild id={fieldId} aria-describedby={cn(hintId, errorId)} aria-invalid={error ? "true" : undefined}>
          {children}
        </FieldChild>
        {error ? (
          <p
            id={errorId}
            role="alert"
            className="text-xs text-rose-600 flex items-center gap-1.5"
          >
            <span className="inline-block h-1 w-1 rounded-full bg-rose-500" />
            {error}
          </p>
        ) : hint ? (
          <p
            id={hintId}
            className="text-xs text-muted-foreground"
          >
            {hint}
          </p>
        ) : null}
      </div>
    );
  },
);
FormField.displayName = "FormField";

/**
 * FieldChild — clones the single child element with
 * generated id + a11y attributes.
 */
import { Children, cloneElement, isValidElement } from "react";
import type { ReactElement } from "react";

interface FieldChildProps {
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: "true" | undefined;
  children: ReactNode;
}

function FieldChild({ id, children, ...a11y }: FieldChildProps) {
  const child = Children.only(children);
  if (!isValidElement(child)) return <>{child}</>;
  // Cast to any because we know Input/Textarea accept these props
  // but TS can't infer the dynamic element type
  return cloneElement(child as ReactElement<Record<string, unknown>>, {
    id,
    ...a11y,
  });
}
