# 2. [Discovering and resolving release targets](2-release-targets.test.ts)

## 2.1 loading release targets from the manifest

### 2.1.1 loads every target declared in the manifest

### 2.1.2 exposes each target kind and directory

## 2.2 reading a target version from its source file

### 2.2.1 reads a version from json and regex sources

## 2.3 resolving a release tag to its target

### 2.3.1 resolves a release tag to its target and version

### 2.3.2 rejects a tag no target owns

### 2.3.3 rejects a tag whose version does not match the manifest

## 2.4 reading a version whose regex does not match its source file

### 2.4.1 rejects reading a version whose regex does not match the file

## 2.5 checking whether the ghcr image target is published

### 2.5.1 treats a failed registry auth handshake as not published
