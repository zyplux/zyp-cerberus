#!/usr/bin/env bun
import { runCz } from '#cli';

const ARGV_SCRIPT_ARGS_START = 2;
const args = process.argv.slice(ARGV_SCRIPT_ARGS_START);

try {
  await runCz(args);
} catch (error) {
  console.error(`error: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
