import type { $ } from '@zyplux/util/shell';

type ShellOutput = Awaited<ReturnType<typeof $.git.status>>;

const notImplemented = (method: string) => () => {
  throw new Error(`fakeShellOutput.${method} is not implemented`);
};

export const fakeShellOutput = (stdout: string, exitCode = 0): ShellOutput => ({
  arrayBuffer: notImplemented('arrayBuffer'),
  blob: notImplemented('blob'),
  bytes: notImplemented('bytes'),
  exitCode,
  json: notImplemented('json'),
  stderr: Buffer.alloc(0),
  stdout: Buffer.from(stdout),
  text: () => stdout,
});
