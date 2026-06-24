import type { Linter } from 'eslint';

import { zyplux } from '@zyplux/eslint-config';
import { ESLint } from 'eslint';
import * as z from 'zod';

const severityLevel = { error: 2, off: 0, warn: 1 } as const;
const SeveritySchema = z.union([z.literal(Object.values(severityLevel)), z.enum(['off', 'warn', 'error'])]);

const RuleEntrySchema = z.union([
  SeveritySchema,
  z.tuple([SeveritySchema]).rest(z.unknown()),
]) satisfies z.ZodType<Linter.RuleEntry>;

const ResolvedConfigSchema = z.object({ rules: z.record(z.string(), RuleEntrySchema) });

export const getMergedRule = async (ruleId: string, filePath = 'example.ts'): Promise<Linter.RuleEntry> => {
  const eslint = new ESLint({ overrideConfig: zyplux(), overrideConfigFile: true });
  const resolved: unknown = await eslint.calculateConfigForFile(filePath);
  return ResolvedConfigSchema.parse(resolved).rules[ruleId] ?? 'off';
};
