import React from 'react';
import { X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from '@/components/ui/dialog';
import { cn } from '@/utils';
import { useT } from '@/hooks/useT';

/**
 * Adaptateur shadcn — API historique préservée (isOpen, onClose, title, size,
 * showCloseButton, headerActions). Rendu par ui/dialog (Radix) : portal, focus
 * trap, Escape, scroll-lock et animations gérés par Radix + tailwindcss-animate.
 * Apparence (rounded-3xl, halos banana, hairlines) inchangée.
 */

const modalI18n = {
  zh: { modal: { dialogLabel: '对话框', close: '关闭' } },
  en: { modal: { dialogLabel: 'Dialog', close: 'Close' } },
};

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'wide' | 'full';
  showCloseButton?: boolean;
  headerActions?: React.ReactNode;
}

const sizes = {
  sm: 'max-w-[380px]',
  md: 'max-w-[480px]',
  lg: 'max-w-[640px]',
  xl: 'max-w-[800px]',
  wide: 'max-w-[1120px]',
  full: 'max-w-[calc(100vw-2rem)] sm:max-w-[calc(100vw-4rem)]',
};

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showCloseButton = true,
  headerActions,
}) => {
  const t = useT(modalI18n);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent
        hideClose
        aria-describedby={undefined}
        className={cn(
          // Structure — flex column, pas de padding global (géré par zones)
          'flex flex-col gap-0 p-0 w-full overflow-hidden',
          size === 'full' ? 'max-h-[calc(100vh-2rem)] sm:max-h-[calc(100vh-3rem)]' : 'max-h-[85vh]',
          // 背景和边框
          'bg-white/95 dark:bg-[#1a1a24]/95',
          'backdrop-blur-xl',
          'border border-white/20 dark:border-white/10',
          // 圆角 + 裁剪滚动条
          'rounded-3xl sm:rounded-3xl',
          // 阴影 - 多层次
          'shadow-[0_0_0_1px_rgba(0,0,0,0.03),0_2px_4px_rgba(0,0,0,0.05),0_12px_24px_rgba(0,0,0,0.09)]',
          'dark:shadow-[0_0_0_1px_rgba(255,255,255,0.05),0_2px_4px_rgba(0,0,0,0.2),0_12px_24px_rgba(0,0,0,0.4)]',
          sizes[size]
        )}
      >
        {/* 顶部光晕效果 */}
        <div className="absolute -top-px left-8 right-8 h-px bg-gradient-to-r from-transparent via-banana-400/50 to-transparent" />

        {/* 内部光晕 */}
        <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -left-32 w-64 h-64 bg-banana-400/10 dark:bg-banana-400/5 rounded-full blur-3xl" />
          <div className="absolute -bottom-32 -right-32 w-64 h-64 bg-banana-300/10 dark:bg-banana-300/5 rounded-full blur-3xl" />
        </div>

        {/* 标题栏 — DialogTitle (Radix) remplace le h2, aria-labelledby auto */}
        {title ? (
          <div className="relative flex-shrink-0 px-7 pt-7 pb-5">
            <DialogTitle
              className={cn(
                'font-display text-xl font-semibold text-gray-900 dark:text-foreground-primary tracking-tight',
                showCloseButton || headerActions ? 'pr-24' : ''
              )}
            >
              {title}
            </DialogTitle>
          </div>
        ) : (
          <DialogTitle className="sr-only">{t('modal.dialogLabel')}</DialogTitle>
        )}

        {headerActions && (
          <div
            className={cn(
              'absolute z-20 flex items-center gap-2',
              title ? 'top-5 right-16' : 'top-4 right-14'
            )}
          >
            {headerActions}
          </div>
        )}

        {/* 关闭按钮 */}
        {showCloseButton && (
          <button
            onClick={onClose}
            className={cn(
              'absolute z-20 group',
              'w-9 h-9 flex items-center justify-center',
              'rounded-xl',
              'text-gray-400 dark:text-foreground-tertiary',
              'hover:text-gray-600 dark:hover:text-foreground-secondary',
              'hover:bg-gray-100/80 dark:hover:bg-background-hover',
              'active:scale-95',
              'transition-all duration-150',
              'focus:outline-none focus-visible:ring-2 focus-visible:ring-banana-400/50 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-[#1a1a24]',
              title ? 'top-5 right-5' : 'top-4 right-4'
            )}
            aria-label={t('modal.close')}
          >
            <X
              size={18}
              strokeWidth={2}
              className="transition-transform duration-150 group-hover:scale-110"
            />
          </button>
        )}

        {/* 内容区域 */}
        <div
          className={cn(
            'relative px-7 pb-7 overflow-y-auto flex-1',
            size === 'full' ? 'max-h-[calc(100vh-8rem)]' : 'max-h-[85vh]',
            'scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600',
            title ? '' : 'pt-7'
          )}
        >
          {children}
        </div>

        {/* 底部边框光晕 */}
        <div className="absolute -bottom-px left-8 right-8 h-px bg-gradient-to-r from-transparent via-white/20 dark:via-white/10 to-transparent" />
      </DialogContent>
    </Dialog>
  );
};
