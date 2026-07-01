# 6. [Shallow-cloning a reference repo](6-clone-reference-repo.test.ts)

## 6.1 building the clone url and destination

### 6.1.1 builds a github url and destination from an owner/name shorthand

### 6.1.2 uses a full url as-is and derives the destination from it

### 6.1.3 derives the destination from a git@ ssh url, stripping the .git suffix

### 6.1.4 passes the ref as a branch flag when given, omits it otherwise

## 6.2 re-cloning over an existing destination

### 6.2.1 prompts for confirmation and removes the existing destination before cloning
