import React, { useState, useCallback } from 'react';
import { AlertTriangle } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from './Button';
import { cn } from '@/utils';

/**
 * Adaptateur shadcn — API historique préservée. Rendu par ui/alert-dialog
 * (Radix AlertDialog : role=alertdialog, focus trap, pas de fermeture au clic
 * extérieur — sémantique correcte pour une confirmation). Boutons = shared/Button.
 */

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (checkboxValue?: boolean) => void;
  title?: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning' | 'info';
  checkboxLabel?: string;
  checkboxDefaultChecked?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  variant = 'warning',
  checkboxLabel,
  checkboxDefaultChecked = false,
}) => {
  const [checkboxChecked, setCheckboxChecked] = useState(checkboxDefaultChecked);

  const handleConfirm = () => {
    onConfirm(checkboxLabel ? checkboxChecked : undefined);
    onClose();
  };

  const variantStyles = {
    danger: 'text-red-600 dark:text-red-400',
    warning: 'text-yellow-600 dark:text-yellow-400',
    info: 'text-blue-600 dark:text-blue-400',
  };

  return (
    <AlertDialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <AlertDialogContent
        className={cn(
          'max-w-[380px] gap-0 p-7',
          'bg-white/95 dark:bg-[#1a1a24]/95 backdrop-blur-xl',
          'border border-white/20 dark:border-white/10',
          'rounded-3xl sm:rounded-3xl',
          'shadow-[0_0_0_1px_rgba(0,0,0,0.03),0_2px_4px_rgba(0,0,0,0.05),0_12px_24px_rgba(0,0,0,0.09)]',
          'dark:shadow-[0_0_0_1px_rgba(255,255,255,0.05),0_2px_4px_rgba(0,0,0,0.2),0_12px_24px_rgba(0,0,0,0.4)]'
        )}
      >
        <AlertDialogHeader className="pb-5">
          <AlertDialogTitle className="font-display text-xl font-semibold text-gray-900 dark:text-foreground-primary tracking-tight">
            {title}
          </AlertDialogTitle>
        </AlertDialogHeader>
        <div className="space-y-4">
          <div className="flex items-start gap-4">
            <AlertTriangle
              size={24}
              className={`flex-shrink-0 mt-0.5 ${variantStyles[variant]}`}
            />
            <AlertDialogDescription className="text-base text-gray-700 dark:text-foreground-secondary flex-1">
              {message}
            </AlertDialogDescription>
          </div>
          {checkboxLabel && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={checkboxChecked}
                onChange={(e) => setCheckboxChecked(e.target.checked)}
                className="w-4 h-4 rounded border-gray-300 dark:border-border-hover"
              />
              <span className="text-sm text-gray-700 dark:text-foreground-secondary">{checkboxLabel}</span>
            </label>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <Button variant="ghost" onClick={onClose}>
              {cancelText}
            </Button>
            <Button
              variant={variant === 'danger' ? 'primary' : 'secondary'}
              onClick={handleConfirm}
            >
              {confirmText}
            </Button>
          </div>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
};

// Hook for easy confirmation dialogs
export const useConfirm = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState<{
    message: string;
    title?: string;
    confirmText?: string;
    cancelText?: string;
    variant?: 'danger' | 'warning' | 'info';
    checkboxLabel?: string;
    checkboxDefaultChecked?: boolean;
    onConfirm: (checkboxValue?: boolean) => void;
  } | null>(null);

  const confirm = useCallback(
    (
      message: string,
      onConfirm: (checkboxValue?: boolean) => void,
      options?: {
        title?: string;
        confirmText?: string;
        cancelText?: string;
        variant?: 'danger' | 'warning' | 'info';
        checkboxLabel?: string;
        checkboxDefaultChecked?: boolean;
      }
    ) => {
      setConfig({
        message,
        onConfirm,
        title: options?.title,
        confirmText: options?.confirmText,
        cancelText: options?.cancelText,
        variant: options?.variant || 'warning',
        checkboxLabel: options?.checkboxLabel,
        checkboxDefaultChecked: options?.checkboxDefaultChecked,
      });
      setIsOpen(true);
    },
    []
  );

  const close = useCallback(() => {
    setIsOpen(false);
    setConfig(null);
  }, []);

  const handleConfirm = useCallback((checkboxValue?: boolean) => {
    if (config?.onConfirm) {
      config.onConfirm(checkboxValue);
    }
    close();
  }, [config, close]);

  return {
    confirm,
    ConfirmDialog: config ? (
      <ConfirmDialog
        isOpen={isOpen}
        onClose={close}
        onConfirm={handleConfirm}
        message={config.message}
        title={config.title}
        confirmText={config.confirmText}
        cancelText={config.cancelText}
        variant={config.variant}
        checkboxLabel={config.checkboxLabel}
        checkboxDefaultChecked={config.checkboxDefaultChecked}
      />
    ) : null,
  };
};
