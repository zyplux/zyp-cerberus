# 6. [Wrapping git and gh behind a typed shell harness](6-shell.test.ts)

## 6.1 translating flag objects into CLI arguments

### 6.1.1 omits a false boolean flag entirely

## 6.2 building git subcommands

### 6.2.1 builds git %s argv from its arguments and flags

## 6.3 building gh subcommands

### 6.3.1 builds gh %s argv from its arguments and flags

## 6.4 reading trimmed command output

### 6.4.1 awaits a command and trims its text output

## 6.5 invoking the shell function directly

### 6.5.1 forwards a direct call to the underlying Bun.$ tagged template

## 6.6 omitting optional flags falls back to defaults

### 6.6.1 omits any flags when %s is called without them

### 6.6.2 builds the same show toplevel argv when git.showToplevel is called without a cwd
