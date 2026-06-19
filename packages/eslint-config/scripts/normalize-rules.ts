const ROOT_DIR_PLACEHOLDER = '<rootDir>';

export const normalizeRules = (config: unknown): unknown => {
  if (typeof config !== 'object' || config === null || !('languageOptions' in config)) {
    return config;
  }
  const { languageOptions } = config;
  if (typeof languageOptions !== 'object' || languageOptions === null || !('parserOptions' in languageOptions)) {
    return config;
  }
  const { parserOptions } = languageOptions;
  if (
    typeof parserOptions === 'object' &&
    parserOptions !== null &&
    'tsconfigRootDir' in parserOptions &&
    typeof parserOptions.tsconfigRootDir === 'string'
  ) {
    parserOptions.tsconfigRootDir = ROOT_DIR_PLACEHOLDER;
  }
  return config;
};
