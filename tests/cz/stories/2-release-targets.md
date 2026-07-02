# 2. [Discovering and resolving release targets](2-release-targets.test.ts)

## 2.1 loading release targets from the manifest

### 2.1.1 loads every target declared in the manifest

### 2.1.2 reads each target version from its json and regex sources

## 2.2 reading a version whose regex does not match its source file

### 2.2.1 rejects reading a version whose regex does not match the file

## 2.3 checking whether the ghcr image target is published

### 2.3.1 treats a failed registry auth handshake as not published
