# 14. [Requiring a published target's version to be bumped whenever its release surface changes](test_14_release-bumps.py)

## 14.1 reading a repo's release manifest

### 14.1.1 skips repos that publish nothing

### 14.1.2 errors when the release manifest is malformed

## 14.2 reading a target's current version

### 14.2.1 fails when the version file is missing

### 14.2.2 fails when the version file is not valid json

### 14.2.3 fails when no version is found in the version file

### 14.2.4 fails when the declared version is not semver

## 14.3 finding a target's latest published release

### 14.3.1 treats a target with no published tags as not yet released

### 14.3.2 picks the highest semver tag rather than the last one listed

### 14.3.3 errors when the published tags cannot be read

## 14.4 comparing the current version against the latest published release

### 14.4.1 passes when the current version is ahead of the latest published release

### 14.4.2 fails when the current version trails the latest published release

## 14.5 requiring a bump when the release surface changed

### 14.5.1 passes when the release surface is unchanged since the latest release

### 14.5.2 fails and names the required bump when the surface changed without one

### 14.5.3 errors when the surface diff cannot be computed
