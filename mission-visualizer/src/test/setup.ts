import '@testing-library/jest-dom'

// Polyfill ResizeObserver for jsdom
global.ResizeObserver = class ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};
