import { http, readJson } from '@zyplux/util';
import { readFile } from 'node:fs/promises';
import * as z from 'zod';

const PackageJsonSchema = z.object({ version: z.string() });
const GhcrTokenSchema = z.object({ token: z.string() });

export type ReleaseTarget = {
  isPublished: (version: string) => Promise<boolean>;
  label: string;
  readSurface: () => string[];
  readVersion: () => Promise<string>;
  tagPrefix: string;
};

const httpOk = async (url: string) => {
  const response = await fetch(url);
  return response.ok;
};

const MANIFEST_MEDIA_TYPES = [
  'application/vnd.oci.image.index.v1+json',
  'application/vnd.oci.image.manifest.v1+json',
  'application/vnd.docker.distribution.manifest.list.v2+json',
  'application/vnd.docker.distribution.manifest.v2+json',
].join(', ');

const fetchGhcrAuth = async (repo: string) => {
  try {
    return await http.get(`https://ghcr.io/token?scope=repository:${repo}:pull`).json(GhcrTokenSchema);
  } catch {
    return;
  }
};

const ghcrImagePublished = async (repo: string, tag: string) => {
  const auth = await fetchGhcrAuth(repo);
  if (!auth) return false;
  const manifest = await fetch(`https://ghcr.io/v2/${repo}/manifests/${tag}`, {
    headers: {
      Accept: MANIFEST_MEDIA_TYPES,
      Authorization: `Bearer ${auth.token}`,
    },
    method: 'HEAD',
  });
  return manifest.ok;
};

const fromRoot = (path: string) => new URL(`../../../${path}`, import.meta.url);

const readJsonVersion = async (dir: string) => {
  const { version } = await readJson(fromRoot(`${dir}/package.json`), PackageJsonSchema);
  return version;
};

const matchVersion = async (url: URL, pattern: RegExp, label: string) => {
  const text = await readFile(url, 'utf8');
  const version = pattern.exec(text)?.[1];
  if (version === undefined) {
    throw new Error(`could not read ${label}`);
  }
  return version;
};

export const releaseTargets: ReleaseTarget[] = [
  {
    isPublished: async version => httpOk(`https://registry.npmjs.org/@zyplux%2feslint-config/${version}`),
    label: '@zyplux/eslint-config',
    readSurface: () => [
      'packages/eslint-config/package.json',
      'packages/eslint-config/README.md',
      'packages/eslint-config/src',
    ],
    readVersion: async () => readJsonVersion('packages/eslint-config'),
    tagPrefix: 'eslint-config-v',
  },
  {
    isPublished: async version => httpOk(`https://registry.npmjs.org/@zyplux%2ftsconfig/${version}`),
    label: '@zyplux/tsconfig',
    readSurface: () => ['packages/tsconfig'],
    readVersion: async () => readJsonVersion('packages/tsconfig'),
    tagPrefix: 'tsconfig-v',
  },
  {
    isPublished: async version => httpOk(`https://registry.npmjs.org/@zyplux%2futil/${version}`),
    label: '@zyplux/util',
    readSurface: () => ['packages/util/package.json', 'packages/util/README.md', 'packages/util/src'],
    readVersion: async () => readJsonVersion('packages/util'),
    tagPrefix: 'util-v',
  },
  {
    isPublished: async version => httpOk(`https://pypi.org/pypi/zyplux-cerberus/${version}/json`),
    label: 'zyplux-cerberus',
    readSurface: () => ['apps/cerberus/src', 'apps/cerberus/pyproject.toml', 'apps/cerberus/README.md'],
    readVersion: async () =>
      matchVersion(fromRoot('apps/cerberus/pyproject.toml'), /^version = "([^"]+)"/m, 'cerberus version'),
    tagPrefix: 'cerberus-v',
  },
  {
    isPublished: async version => ghcrImagePublished('zyplux/ci', version),
    label: 'ghcr.io/zyplux/ci',
    readSurface: () => ['containers/ci'],
    readVersion: async () =>
      matchVersion(
        fromRoot('containers/ci/Containerfile'),
        /^LABEL org\.opencontainers\.image\.version="([^"]+)"/m,
        'image version',
      ),
    tagPrefix: 'ci-image-v',
  },
];
