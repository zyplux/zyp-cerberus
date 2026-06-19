import type { Linter } from 'eslint';

import { zyplux } from '@zyplux/eslint-config';
import { ESLint } from 'eslint';
import * as z from 'zod';

const severityLevel = { error: 2, off: 0, warn: 1 } as const;
const severity = z.union([z.literal(Object.values(severityLevel)), z.enum(['off', 'warn', 'error'])]);

const ruleEntry: z.ZodType<Linter.RuleEntry> = z.union([severity, z.tuple([severity]).rest(z.unknown())]);

const resolvedConfig = z.object({ rules: z.record(z.string(), ruleEntry) });

export const getMergedRule = async (ruleId: string, filePath = 'example.ts'): Promise<Linter.RuleEntry> => {
  const eslint = new ESLint({ overrideConfig: zyplux(), overrideConfigFile: true });
  const resolved: unknown = await eslint.calculateConfigForFile(filePath);
  return resolvedConfig.parse(resolved).rules[ruleId] ?? 'off';
};
