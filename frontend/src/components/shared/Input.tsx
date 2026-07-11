import React from 'react';
import { Input as UiInput } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/utils';

/** Adaptateur shadcn — API historique préservée (label, error). Rendu ui/input + ui/label. */

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  className,
  ...props
}) => {
  return (
    <div className="w-full">
      {label && (
        <Label className="block text-sm font-medium text-gray-700 dark:text-foreground-secondary mb-2">
          {label}
        </Label>
      )}
      <UiInput
        className={cn(
          'h-10 px-4 rounded-lg text-base border-gray-200 dark:border-border-primary bg-white dark:bg-background-secondary',
          'placeholder:text-gray-400 dark:placeholder:text-gray-500 transition-all',
          'text-gray-900 dark:text-foreground-primary',
          error && 'border-red-500 focus-visible:ring-red-500',
          className
        )}
        {...props}
      />
      {error && (
        <p className="mt-1 text-sm text-red-500">{error}</p>
      )}
    </div>
  );
};
