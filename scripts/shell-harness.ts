const readTrimmed = async (output: Promise<string>) => {
  const text = await output;
  return text.trim();
};

const gh = {
  pr: {
    create: async (base: string, title: string) =>
      Bun.$`gh pr create --base ${base} --title ${title} --body ${''} --draft`,
    isDraft: async () => (await readTrimmed(Bun.$`gh pr view --json isDraft --jq .isDraft`.text())) === 'true',
    merge: async () => Bun.$`gh pr merge --squash --delete-branch`,
    mergeAuto: async () => Bun.$`gh pr merge --auto --squash --delete-branch`,
    mergeState: async () => readTrimmed(Bun.$`gh pr view --json mergeStateStatus --jq .mergeStateStatus`.text()),
    ready: async () => Bun.$`gh pr ready`,
    state: async (branch: string) =>
      readTrimmed(Bun.$`gh pr list --head ${branch} --state all --json state --jq ${'.[0].state // ""'}`.text()),
    url: async () => readTrimmed(Bun.$`gh pr view --json url --jq .url`.text()),
  },
  release: {
    create: async (tag: string, options: { target: string }) =>
      Bun.$`gh release create ${tag} --target ${options.target} --title ${tag} --generate-notes`,
    exists: async (tag: string) =>
      (await readTrimmed(Bun.$`gh release list --json tagName --jq ${`any(.[]; .tagName == "${tag}")`}`.text())) ===
      'true',
  },
  run: {
    find: async (options: { event: string; headSha: string; knownIds: string[]; workflow: string }) => {
      const query = `[.[] | select(.headSha=="${options.headSha}")] | .[].databaseId`;
      const listed = await readTrimmed(
        Bun.$`gh run list --workflow=${options.workflow} --event=${options.event} --json databaseId,headSha --jq ${query}`.text(),
      );
      const ids = listed ? listed.split('\n') : [];
      return ids.find(id => !options.knownIds.includes(id));
    },
    ids: async (options: { event: string; workflow: string }) => {
      const listed = await readTrimmed(
        Bun.$`gh run list --workflow=${options.workflow} --event=${options.event} --json databaseId --jq ${'.[].databaseId'}`.text(),
      );
      return listed ? listed.split('\n') : [];
    },
    watch: async (runId: string) => Bun.$`gh run watch ${runId} --exit-status`,
  },
};

const git = {
  checkout: async (ref: string) => Bun.$`git checkout ${ref}`,
  clone: async (url: string, dest: string, ref: string) =>
    Bun.$`git clone ${ref ? ['--shallow-exclude', ref] : ['--depth', '1']} --single-branch ${url} ${dest}`,
  currentBranch: async () => readTrimmed(Bun.$`git rev-parse --abbrev-ref HEAD`.text()),
  deleteBranch: async (branch: string) => Bun.$`git branch -D ${branch}`,
  fetch: async (remote: string, branch: string) => Bun.$`git fetch ${remote} ${branch}`,
  pull: async () => Bun.$`git pull --ff-only`,
  push: async (remote: string, branch: string) => Bun.$`git push -u ${remote} ${branch}`,
  revParse: async (rev: string) => readTrimmed(Bun.$`git rev-parse ${rev}`.text()),
  status: async () => readTrimmed(Bun.$`git status --porcelain`.text()),
};

export const $ = Object.assign(Bun.$, { gh, git });
