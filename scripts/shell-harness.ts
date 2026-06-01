export const ensure = (condition: boolean, message: string) => {
  if (!condition) {
    throw new Error(message);
  }
};

const readTrimmed = async (output: Promise<string>) => {
  const text = await output;
  return text.trim();
};

export const poll = async <T>(probe: () => Promise<T | undefined>, attempts: number, intervalMs: number) => {
  for (let attempt = 0; attempt < attempts; attempt++) {
    const found = await probe();
    if (found !== undefined) {
      return found;
    }
    await Bun.sleep(intervalMs);
  }
  return;
};

const bun = {
  pm: {
    view: (spec: string) => readTrimmed(Bun.$`bun pm view ${spec}`.nothrow().text()),
  },
};

const gh = {
  pr: {
    create: (base: string, title: string) => Bun.$`gh pr create --base ${base} --title ${title} --body ${''} --draft`,
    isDraft: async () =>
      (await readTrimmed(Bun.$`gh pr view --json isDraft --jq .isDraft`.nothrow().text())) === 'true',
    merge: () => Bun.$`gh pr merge --auto --squash --delete-branch`.nothrow(),
    ready: () => Bun.$`gh pr ready`.nothrow(),
    state: () => readTrimmed(Bun.$`gh pr view --json state --jq .state`.nothrow().text()),
    url: () => readTrimmed(Bun.$`gh pr view --json url --jq .url`.nothrow().text()),
  },
  release: {
    create: (tag: string, options: { target: string }) =>
      Bun.$`gh release create ${tag} --target ${options.target} --title ${tag} --generate-notes`,
    view: async (tag: string) => {
      const result = await Bun.$`gh release view ${tag}`.quiet().nothrow();
      return result.exitCode === 0;
    },
  },
  run: {
    find: async (options: { event: string; headSha: string; workflow: string }) => {
      const query = `[.[] | select(.headSha=="${options.headSha}")][0].databaseId`;
      const id = await readTrimmed(
        Bun.$`gh run list --workflow=${options.workflow} --event=${options.event} --json databaseId,headSha --jq ${query}`
          .nothrow()
          .text(),
      );
      return id && id !== 'null' ? id : undefined;
    },
    watch: (runId: string) => Bun.$`gh run watch ${runId} --exit-status`,
  },
};

const git = {
  checkout: (ref: string) => Bun.$`git checkout ${ref}`,
  currentBranch: () => readTrimmed(Bun.$`git rev-parse --abbrev-ref HEAD`.text()),
  deleteBranch: (branch: string) => Bun.$`git branch -D ${branch}`,
  fetch: (remote: string, branch: string) => Bun.$`git fetch --quiet ${remote} ${branch}`,
  pull: () => Bun.$`git pull --ff-only`,
  push: (remote: string, branch: string) => Bun.$`git push -u ${remote} ${branch}`,
  revParse: (rev: string) => readTrimmed(Bun.$`git rev-parse ${rev}`.text()),
  status: () => readTrimmed(Bun.$`git status --porcelain`.text()),
};

export const $ = Object.assign(Bun.$, { bun, gh, git });
