import { plugin, totvibe } from '@totvibe/eslint-config';
import { describe, expect, test } from 'bun:test';

type Config = ReturnType<typeof totvibe>;

const customRuleNames = ['no-inferrable-return-type', 'no-type-predicate', 'no-zod-custom', 'prefer-arrow-functions'];

const hasReactSettings = (config: Config) =>
  config.some(entry => entry.settings !== undefined && 'react' in entry.settings);

const hasRouteRule = (config: Config) =>
  config.some(entry => Array.isArray(entry.files) && entry.files.includes('**/routes/**/*.{ts,tsx}'));

describe('totvibe', () => {
  test('returns a non-empty flat config array', () => {
    expect(totvibe().length).toBeGreaterThan(0);
  });

  test('registers the @totvibe plugin and its rules', () => {
    const config = totvibe();
    const entry = config.find(item => item.plugins !== undefined && '@totvibe' in item.plugins);
    expect(entry).toBeDefined();
    expect(Object.keys(entry?.rules ?? {})).toEqual(customRuleNames.map(name => `@totvibe/${name}`));
  });

  test('React config is opt-in', () => {
    expect(hasReactSettings(totvibe())).toBe(false);
    expect(hasReactSettings(totvibe({ react: true }))).toBe(true);
  });

  test('TanStack route rule is opt-in', () => {
    expect(hasRouteRule(totvibe())).toBe(false);
    expect(hasRouteRule(totvibe({ tanstack: true }))).toBe(true);
  });
});

describe('plugin', () => {
  test('exposes the custom rules', () => {
    expect(Object.keys(plugin.rules).toSorted()).toEqual(customRuleNames.toSorted());
  });
});
