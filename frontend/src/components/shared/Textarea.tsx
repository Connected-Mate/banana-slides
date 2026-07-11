import React from 'react';
import { Textarea as UiTextarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { cn } from '@/utils';

/** Adaptateur shadcn — API historique préservée (label, error, ref, memo). Rendu ui/textarea + ui/label. */

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
}

const TextareaComponent = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({
  label,
  error,
  className,
  ...props
}, ref) => {
  return (
    <div className="w-full">
      {label && (
        <Label className="block text-sm font-medium text-gray-700 dark:text-foreground-secondary mb-2">
          {label}
        </Label>
      )}
      <UiTextarea
        ref={ref}
        className={cn(
          'min-h-[120px] px-4 py-3 rounded-lg text-base border-gray-200 dark:border-border-primary bg-white dark:bg-background-secondary',
          'placeholder:text-gray-400 dark:placeholder:text-gray-500 transition-all resize-y',
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
});

TextareaComponent.displayName = 'Textarea';

// 使用 memo 包装，避免父组件频繁重渲染时影响输入框
export const Textarea = React.memo(TextareaComponent);
