import { describe, expect, it } from 'bun:test';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as z from 'zod';

const repoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '../..');

const dependencyMap = z.record(z.string(), z.string());

const manifestSchema = z.object({
  dependencies: dependencyMap.optional(),
  devDependencies: dependencyMap.optional(),
  optionalDependencies: dependencyMap.optional(),
  peerDependencies: dependencyMap.optional(),
});

const dependencyKeys = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'] as const;

const collectWorkspaceManifests = () => {
  const paths = [path.join(repoRoot, 'package.json')];
  for (const group of ['packages', 'tests']) {
    for (const name of readdirSync(path.join(repoRoot, group))) {
      const manifestPath = path.join(repoRoot, group, name, 'package.json');
      if (existsSync(manifestPath)) paths.push(manifestPath);
    }
  }
  return paths;
};

const findOffenders = () => {
  const offenders: string[] = [];
  for (const manifestPath of collectWorkspaceManifests()) {
    const raw: unknown = JSON.parse(readFileSync(manifestPath, 'utf8'));
    const manifest = manifestSchema.parse(raw);
    const label = path.relative(repoRoot, manifestPath);
    for (const key of dependencyKeys) {
      const deps = manifest[key];
      if (!deps) continue;
      for (const [name, spec] of Object.entries(deps)) {
        if (!spec.startsWith('catalog:') && !spec.startsWith('workspace:')) {
          offenders.push(`${label} → ${key}.${name} = "${spec}"`);
        }
      }
    }
  }
  return offenders;
};

describe('workspace dependency discipline', () => {
  it('every dependency entry in a workspace package.json uses catalog: or workspace:', () => {
    expect(findOffenders()).toEqual([]);
  });
});
