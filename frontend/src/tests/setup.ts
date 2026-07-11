/**
 * Vitest 测试环境设置文件
 * 
 * 配置测试所需的全局设置和模拟
 */

import '@testing-library/jest-dom'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// 每个测试后清理
afterEach(() => {
  cleanup()
})

// Mock matchMedia（某些组件需要）
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

// Mock scrollTo
window.scrollTo = vi.fn()

// Radix UI primitives (Dialog/Switch/Select/DropdownMenu) rely on Pointer
// Capture + scrollIntoView, which jsdom does not implement. Stub them so the
// shadcn-backed shared components render/interact in tests.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = vi.fn(() => false) as never
}
if (!Element.prototype.setPointerCapture) {
  Element.prototype.setPointerCapture = vi.fn() as never
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = vi.fn() as never
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn() as never
}

// Mock fetch (可以在具体测试中覆盖)
global.fetch = vi.fn()

// Mock localStorage/sessionStorage for utility tests
const storageMock = () => {
  const store = new Map<string, string>()
  return {
    getItem: vi.fn((key: string) => store.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store.set(key, String(value))
    }),
    removeItem: vi.fn((key: string) => {
      store.delete(key)
    }),
    clear: vi.fn(() => {
      store.clear()
    }),
    key: vi.fn((index: number) => Array.from(store.keys())[index] ?? null),
    get length() {
      return store.size
    },
  }
}

Object.defineProperty(window, 'localStorage', {
  writable: true,
  value: storageMock(),
})

Object.defineProperty(window, 'sessionStorage', {
  writable: true,
  value: storageMock(),
})
