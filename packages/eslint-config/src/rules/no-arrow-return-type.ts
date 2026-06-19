import type { TSESTree } from '@typescript-eslint/utils';

import { AST_NODE_TYPES } from '@typescript-eslint/utils';

import { createRule } from '#create-rule';

const getFunctionName = (node: TSESTree.ArrowFunctionExpression) => {
  const parent = node.parent;
  if (parent.type === AST_NODE_TYPES.VariableDeclarator && parent.id.type === AST_NODE_TYPES.Identifier) {
    return parent.id.name;
  }
  return;
};

const ignoredKeys: ReadonlySet<string> = new Set(['loc', 'parent', 'range']);

const childNodes = (node: object) => {
  const entries: ReadonlyMap<string, unknown> = new Map(Object.entries(node));
  const children: object[] = [];
  for (const [key, value] of entries) {
    if (ignoredKeys.has(key)) continue;
    const items: readonly unknown[] = Array.isArray(value) ? value : [value];
    for (const item of items) {
      if (item !== null && typeof item === 'object') children.push(item);
    }
  }
  return children;
};

const hasMatchingNode = (node: object, isMatch: (n: object) => boolean): boolean =>
  isMatch(node) || childNodes(node).some(child => hasMatchingNode(child, isMatch));

const isIdentifierNamed = (node: object, isWanted: (name: string) => boolean) =>
  'type' in node &&
  node.type === AST_NODE_TYPES.Identifier &&
  'name' in node &&
  typeof node.name === 'string' &&
  isWanted(node.name);

const collectTypeParamNames = (node: TSESTree.ArrowFunctionExpression) => {
  const names = new Set<string>();
  if (node.typeParameters) {
    for (const param of node.typeParameters.params) {
      names.add(param.name.name);
    }
  }
  return names;
};

const hasTypeParamReference = (typeNode: TSESTree.TypeNode, typeParamNames: ReadonlySet<string>) =>
  hasMatchingNode(
    typeNode,
    n =>
      'type' in n &&
      n.type === AST_NODE_TYPES.TSTypeReference &&
      'typeName' in n &&
      typeof n.typeName === 'object' &&
      n.typeName !== null &&
      isIdentifierNamed(n.typeName, name => typeParamNames.has(name)),
  );

const isRecursive = (node: TSESTree.ArrowFunctionExpression) => {
  const functionName = getFunctionName(node);
  return (
    functionName !== undefined &&
    hasMatchingNode(node.body, n => isIdentifierNamed(n, candidate => candidate === functionName))
  );
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

const isReExportedAtTopLevel = (node: TSESTree.ArrowFunctionExpression, exportedNames: ReadonlySet<string>) => {
  if (exportedNames.size === 0) return false;
  const declarator = node.parent;
  if (declarator.type !== AST_NODE_TYPES.VariableDeclarator || declarator.id.type !== AST_NODE_TYPES.Identifier) {
    return false;
  }
  return declarator.parent.parent.type === AST_NODE_TYPES.Program && exportedNames.has(declarator.id.name);
};

const isAtModuleBoundary = (node: TSESTree.ArrowFunctionExpression, exportedNames: ReadonlySet<string>) =>
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

export const noArrowReturnType = createRule({
  create: context => {
    let exportedNames: ReadonlySet<string> = new Set();

    const checkArrowFunction = (arrowFn: TSESTree.ArrowFunctionExpression) => {
      const returnAnnotation = arrowFn.returnType;
      if (!returnAnnotation) return;

      const returnAnnotationTypeNode = returnAnnotation.typeAnnotation;

      if (returnAnnotationTypeNode.type === AST_NODE_TYPES.TSTypePredicate) return;

      if (isAtModuleBoundary(arrowFn, exportedNames)) return;

      const typeParamNames = collectTypeParamNames(arrowFn);
      if (typeParamNames.size > 0 && hasTypeParamReference(returnAnnotationTypeNode, typeParamNames)) return;

      if (isRecursive(arrowFn)) return;

      const tokenBefore = context.sourceCode.getTokenBefore(returnAnnotation);
      context.report({
        ...(tokenBefore && {
          fix: fixer => fixer.removeRange([tokenBefore.range[1], returnAnnotation.range[1]]),
        }),
        messageId: 'removeReturnType',
        node: returnAnnotation,
      });
    };

    return {
      ArrowFunctionExpression: checkArrowFunction,
      Program: program => {
        exportedNames = collectExportedNames(program);
      },
    };
  },
  defaultOptions: [],
  meta: {
    docs: {
      description:
        'Disallow explicit return type annotations on non-exported arrow functions; let TypeScript infer them.',
    },
    fixable: 'code',
    messages: {
      removeReturnType:
        'Explicit return type annotation is unnecessary; let TypeScript infer it. (Exported functions are exempt, since `tsc` may need the annotation for declaration-emit portability.)',
    },
    schema: [],
    type: 'suggestion',
  },
  name: 'no-arrow-return-type',
});
