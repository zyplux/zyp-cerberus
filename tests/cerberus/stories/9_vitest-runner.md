# 9. [Requiring vitest as the sole test runner for TypeScript](test_9_vitest-runner.py)

## 9.1 scoping the check to repos with test tooling to configure

### 9.1.1 skips repos with no package json

## 9.2 requiring the package json test script to invoke vitest instead of bun

### 9.2.1 fails when the test script runs bun test directly

### 9.2.2 allows a bun filter script

### 9.2.3 allows a bun run test script

## 9.3 requiring test files to import from vitest instead of bun test

### 9.3.1 fails when a test file imports from bun test

### 9.3.2 ignores bun test imports inside vendored node modules files

## 9.4 passing repos that use vitest throughout

### 9.4.1 passes when the test script and test files both use vitest
