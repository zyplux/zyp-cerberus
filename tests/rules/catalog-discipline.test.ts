import { readJsonSync } from '@zyplux/util';
import { existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import * as z from 'zod';

const repoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), '../..');

const DependencyMapSchema = z.record(z.string(), z.string());

const ManifestSchema = z.object({
  dependencies: DependencyMapSchema.optional(),
  devDependencies: DependencyMapSchema.optional(),
  optionalDependencies: DependencyMapSchema.optional(),
  peerDependencies: DependencyMapSchema.optional(),
});

const dependencyKeys = ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'] as const;

const collectWorkspaceManifests = () => {
  const paths = [path.join(repoRoot, 'package.json')];
  for (const group of ['packages', 'tests']) {
    const names = readdirSync(path.join(repoRoot, group));
    for (const name of names) {
      const manifestPath = path.join(repoRoot, group, name, 'package.json');
      if (existsSync(manifestPath)) paths.push(manifestPath);
    }
  }
  return paths;
};

const manifestOffenders = (manifestPath: string) => {
  const manifest = readJsonSync(manifestPath, ManifestSchema);
  const label = path.relative(repoRoot, manifestPath);
  const offenders: string[] = [];
  for (const key of dependencyKeys) {
    const deps = manifest[key];
    if (!deps) continue;
    for (const [name, spec] of Object.entries(deps)) {
      if (!spec.startsWith('catalog:') && !spec.startsWith('workspace:')) {
        offenders.push(`${label} → ${key}.${name} = "${spec}"`);
      }
    }
  }
  return offenders;
};

const findOffenders = () => collectWorkspaceManifests().flatMap(manifestPath => manifestOffenders(manifestPath));

describe('workspace dependency discipline', () => {
  it('every dependency entry in a workspace package.json uses catalog: or workspace:', () => {
    expect(findOffenders()).toEqual([]);
  });
});
