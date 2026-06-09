import type { TSESTree } from '@typescript-eslint/utils';

import { AST_NODE_TYPES } from '@typescript-eslint/utils';

import { createRule } from '#create-rule';

type FunctionWithReturnType =
  | TSESTree.ArrowFunctionExpression
  | TSESTree.FunctionDeclaration
  | TSESTree.FunctionExpression;

const getFunctionName = (node: FunctionWithReturnType) => {
  if (
    (node.type === AST_NODE_TYPES.FunctionDeclaration || node.type === AST_NODE_TYPES.FunctionExpression) &&
    node.id
  ) {
    return node.id.name;
  }
  const parent = node.parent;
  if (parent.type === AST_NODE_TYPES.VariableDeclarator && parent.id.type === AST_NODE_TYPES.Identifier) {
    return parent.id.name;
  }
  return;
};

const traverse = (node: object, visit: (n: object) => boolean): boolean => {
  if (visit(node)) return true;
  const entries: ReadonlyMap<string, unknown> = new Map(Object.entries(node));
  for (const [key, value] of entries) {
    if (key === 'parent' || key === 'loc' || key === 'range') continue;
    const items: readonly unknown[] = Array.isArray(value) ? value : [value];
    for (const item of items) {
      if (item === null || typeof item !== 'object') continue;
      if (traverse(item, visit)) return true;
    }
  }
  return false;
};

const bodyReferencesIdentifier = (body: TSESTree.Node, name: string) =>
  traverse(body, n => {
    if (!('type' in n) || n.type !== AST_NODE_TYPES.Identifier) return false;
    if (!('name' in n) || typeof n.name !== 'string') return false;
    return n.name === name;
  });

const collectTypeParamNames = (node: FunctionWithReturnType) => {
  const names = new Set<string>();
  if (node.typeParameters) {
    for (const param of node.typeParameters.params) {
      names.add(param.name.name);
    }
  }
  return names;
};

const returnTypeReferencesAny = (typeNode: TSESTree.Node, names: Set<string>) => {
  if (names.size === 0) return false;
  return traverse(typeNode, n => {
    if (!('type' in n) || n.type !== AST_NODE_TYPES.TSTypeReference) return false;
    if (!('typeName' in n) || n.typeName === null || typeof n.typeName !== 'object') return false;
    if (!('type' in n.typeName) || n.typeName.type !== AST_NODE_TYPES.Identifier) return false;
    if (!('name' in n.typeName) || typeof n.typeName.name !== 'string') return false;
    return names.has(n.typeName.name);
  });
};

const declarationContainers: ReadonlySet<TSESTree.Node['type']> = new Set([
  AST_NODE_TYPES.AccessorProperty,
  AST_NODE_TYPES.ArrayExpression,
  AST_NODE_TYPES.ClassBody,
  AST_NODE_TYPES.ClassDeclaration,
  AST_NODE_TYPES.ClassExpression,
  AST_NODE_TYPES.MethodDefinition,
  AST_NODE_TYPES.ObjectExpression,
  AST_NODE_TYPES.Property,
  AST_NODE_TYPES.PropertyDefinition,
  AST_NODE_TYPES.VariableDeclaration,
  AST_NODE_TYPES.VariableDeclarator,
]);

const hasExportedAncestor = (node: TSESTree.Node): boolean => {
  const parent = node.parent;
  if (!parent) return false;
  if (
    parent.type === AST_NODE_TYPES.ExportNamedDeclaration ||
    parent.type === AST_NODE_TYPES.ExportDefaultDeclaration
  ) {
    return true;
  }
  return declarationContainers.has(parent.type) && hasExportedAncestor(parent);
};

const isReExportedAtTopLevel = (node: FunctionWithReturnType, exportedNames: ReadonlySet<string>) => {
  if (exportedNames.size === 0) return false;
  if (node.type === AST_NODE_TYPES.FunctionDeclaration) {
    return node.parent.type === AST_NODE_TYPES.Program && node.id !== null && exportedNames.has(node.id.name);
  }
  const declarator = node.parent;
  if (declarator.type !== AST_NODE_TYPES.VariableDeclarator || declarator.id.type !== AST_NODE_TYPES.Identifier) {
    return false;
  }
  return declarator.parent.parent.type === AST_NODE_TYPES.Program && exportedNames.has(declarator.id.name);
};

const isAtModuleBoundary = (node: FunctionWithReturnType, exportedNames: ReadonlySet<string>) =>
  hasExportedAncestor(node) || isReExportedAtTopLevel(node, exportedNames);

const collectExportedNames = (program: TSESTree.Program) => {
  const names = new Set<string>();
  for (const statement of program.body) {
    if (statement.type !== AST_NODE_TYPES.ExportNamedDeclaration) continue;
    if (statement.source) continue;
    for (const specifier of statement.specifiers) {
      names.add(specifier.local.name);
    }
  }
  return names;
};

export const noInferrableReturnType = createRule({
  create: context => {
    let exportedNames: ReadonlySet<string> = new Set();

    const checkFunction = (node: FunctionWithReturnType) => {
      const returnTypeNode = node.returnType;
      if (!returnTypeNode) return;

      if (returnTypeNode.typeAnnotation.type === AST_NODE_TYPES.TSTypePredicate) return;

      const typeParamNames = collectTypeParamNames(node);
      if (returnTypeReferencesAny(returnTypeNode.typeAnnotation, typeParamNames)) return;

      const functionName = getFunctionName(node);
      if (functionName && bodyReferencesIdentifier(node.body, functionName)) return;

      if (isAtModuleBoundary(node, exportedNames)) return;

      const tokenBefore = context.sourceCode.getTokenBefore(returnTypeNode);
      context.report({
        ...(tokenBefore && {
          fix: fixer => fixer.removeRange([tokenBefore.range[1], returnTypeNode.range[1]]),
        }),
        messageId: 'removeReturnType',
        node: returnTypeNode,
      });
    };

    return {
      ArrowFunctionExpression: checkFunction,
      FunctionDeclaration: checkFunction,
      FunctionExpression: checkFunction,
      Program: program => {
        exportedNames = collectExportedNames(program);
      },
    };
  },
  defaultOptions: [],
  meta: {
    docs: {
      description: 'Disallow explicit return type annotations on non-exported functions; let TypeScript infer them.',
    },
    fixable: 'code',
    messages: {
      removeReturnType:
        'Explicit return type annotation is unnecessary; let TypeScript infer it. (Exported functions are exempt, since `tsc` may need the annotation for declaration-emit portability.)',
    },
    schema: [],
    type: 'suggestion',
  },
  name: 'no-inferrable-return-type',
});
