import type { TSESTree } from '@typescript-eslint/utils';
import type * as ts from 'typescript';

import { isTypeAnyType, isTypeUnknownType } from '@typescript-eslint/type-utils';
import { AST_NODE_TYPES, ESLintUtils } from '@typescript-eslint/utils';

import { createRule } from '#create-rule';

const ignoredKeys = new Set<string>(['loc', 'parent', 'range']);

const childNodes = (node: object) => {
  const children: object[] = [];
  for (const [key, value] of Object.entries(node)) {
    if (ignoredKeys.has(key)) continue;
    const items: unknown[] = Array.isArray(value) ? value : [value];
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

const getArrowName = ({ parent }: TSESTree.ArrowFunctionExpression) => {
  if (parent.type === AST_NODE_TYPES.VariableDeclarator && parent.id.type === AST_NODE_TYPES.Identifier) {
    return parent.id.name;
  }
  return;
};

const isRecursiveArrow = (arrow: TSESTree.ArrowFunctionExpression) => {
  const name = getArrowName(arrow);
  return name !== undefined && hasMatchingNode(arrow.body, n => isIdentifierNamed(n, candidate => candidate === name));
};

const collectTypeParamNames = (declaration: TSESTree.TSTypeParameterDeclaration | undefined) => {
  const names = new Set<string>();
  const params = declaration?.params ?? [];
  for (const param of params) {
    names.add(param.name.name);
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

const declarationContainers = new Set<TSESTree.Node['type']>([
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

const hasExportedAncestor = ({ parent }: TSESTree.Node): boolean => {
  if (!parent) return false;
  if (
    parent.type === AST_NODE_TYPES.ExportNamedDeclaration ||
    parent.type === AST_NODE_TYPES.ExportDefaultDeclaration
  ) {
    return true;
  }
  return declarationContainers.has(parent.type) && hasExportedAncestor(parent);
};

const isTopLevel = ({ parent }: TSESTree.Node) => parent?.type === AST_NODE_TYPES.Program;

const isArrowAtModuleBoundary = (arrow: TSESTree.ArrowFunctionExpression, exportedNames: ReadonlySet<string>) => {
  if (hasExportedAncestor(arrow)) return true;
  const { parent } = arrow;
  return (
    parent.type === AST_NODE_TYPES.VariableDeclarator &&
    parent.id.type === AST_NODE_TYPES.Identifier &&
    isTopLevel(parent.parent) &&
    exportedNames.has(parent.id.name)
  );
};

const isDeclaratorAtModuleBoundary = (declarator: TSESTree.VariableDeclarator, exportedNames: ReadonlySet<string>) => {
  if (hasExportedAncestor(declarator)) return true;
  return (
    declarator.id.type === AST_NODE_TYPES.Identifier &&
    isTopLevel(declarator.parent) &&
    exportedNames.has(declarator.id.name)
  );
};

const collectExportedNames = ({ body }: TSESTree.Program) => {
  const names = new Set<string>();
  for (const statement of body) {
    if (statement.type !== AST_NODE_TYPES.ExportNamedDeclaration || statement.source) continue;
    for (const specifier of statement.specifiers) {
      names.add(specifier.local.name);
    }
  }
  return names;
};

const selfDeterminedInitializers = new Set<TSESTree.Node['type']>([
  AST_NODE_TYPES.BinaryExpression,
  AST_NODE_TYPES.Identifier,
  AST_NODE_TYPES.MemberExpression,
  AST_NODE_TYPES.TemplateLiteral,
  AST_NODE_TYPES.UnaryExpression,
]);

const annotatedIdentifierParam = (param: TSESTree.Parameter) => {
  const binding = param.type === AST_NODE_TYPES.AssignmentPattern ? param.left : param;
  return binding.type === AST_NODE_TYPES.Identifier && binding.typeAnnotation ? binding : undefined;
};

const isInferableType = (type: ts.Type) => !isTypeAnyType(type) && !isTypeUnknownType(type);

const isSelfReferentialContextualParam = ({ valueDeclaration }: ts.Symbol, ownParameters: ReadonlySet<ts.Node>) =>
  valueDeclaration !== undefined && ownParameters.has(valueDeclaration);

export const noTypeAnnotations = createRule({
  create: context => {
    const services = ESLintUtils.getParserServices(context);
    const checker = services.program.getTypeChecker();
    let exportedNames: ReadonlySet<string> = new Set();

    const reportRedundant = (annotation: TSESTree.TSTypeAnnotation, messageId: 'removeParamType' | 'removeVarType') => {
      context.report({
        fix: fixer => fixer.removeRange(annotation.range),
        messageId,
        node: annotation,
      });
    };

    const checkReturnType = (arrow: TSESTree.ArrowFunctionExpression) => {
      const returnAnnotation = arrow.returnType;
      if (!returnAnnotation) return;
      if (returnAnnotation.typeAnnotation.type === AST_NODE_TYPES.TSTypePredicate) return;
      if (isArrowAtModuleBoundary(arrow, exportedNames)) return;

      const typeParamNames = collectTypeParamNames(arrow.typeParameters);
      if (typeParamNames.size > 0 && hasTypeParamReference(returnAnnotation.typeAnnotation, typeParamNames)) return;

      if (isRecursiveArrow(arrow)) return;

      const tokenBefore = context.sourceCode.getTokenBefore(returnAnnotation);
      context.report({
        ...(tokenBefore && {
          fix: fixer => fixer.removeRange([tokenBefore.range[1], returnAnnotation.range[1]]),
        }),
        messageId: 'removeReturnType',
        node: returnAnnotation,
      });
    };

    const isContextualParamInferredFromCallback = (arrow: TSESTree.ArrowFunctionExpression, paramIndex: number) => {
      const { parent } = arrow;
      if (parent.type !== AST_NODE_TYPES.CallExpression && parent.type !== AST_NODE_TYPES.NewExpression) return false;
      const isConstruct = parent.type === AST_NODE_TYPES.NewExpression;

      const argIndex = parent.arguments.indexOf(arrow);
      if (argIndex === -1) return false;

      const calleeType = services.getTypeAtLocation(parent.callee);
      const calleeSignatures = isConstruct ? calleeType.getConstructSignatures() : calleeType.getCallSignatures();

      return calleeSignatures.some(signature => {
        const { typeParameters } = signature;
        if (!typeParameters || typeParameters.length === 0) return false;

        const calleeParam = signature.parameters[argIndex];
        if (!calleeParam?.valueDeclaration) return false;

        const callbackType = checker.getTypeOfSymbolAtLocation(calleeParam, calleeParam.valueDeclaration);
        const callbackParam = callbackType.getCallSignatures()[0]?.parameters[paramIndex];
        if (!callbackParam?.valueDeclaration) return false;

        const callbackParamType = checker.getTypeOfSymbolAtLocation(callbackParam, callbackParam.valueDeclaration);
        return new Set<ts.Type>(typeParameters).has(callbackParamType);
      });
    };

    const checkParams = (arrow: TSESTree.ArrowFunctionExpression) => {
      if (isArrowAtModuleBoundary(arrow, exportedNames)) return;

      const tsArrow = services.esTreeNodeToTSNodeMap.get(arrow);
      const contextualType = checker.getContextualType(tsArrow);
      if (!contextualType) return;

      const signatures = contextualType.getCallSignatures();
      if (signatures.length !== 1) return;
      const signature = signatures[0];
      if (!signature) return;

      const ownParameters = new Set<ts.Node>(tsArrow.parameters);

      for (const [index, param] of arrow.params.entries()) {
        const binding = annotatedIdentifierParam(param);
        if (!binding?.typeAnnotation) continue;

        const contextualParam = signature.parameters[index];
        if (!contextualParam) continue;
        if (isSelfReferentialContextualParam(contextualParam, ownParameters)) continue;
        if (isContextualParamInferredFromCallback(arrow, index)) continue;

        const contextualParamType = checker.getTypeOfSymbolAtLocation(contextualParam, tsArrow);
        const annotatedType = services.getTypeAtLocation(binding);
        if (annotatedType !== contextualParamType || !isInferableType(annotatedType)) continue;

        reportRedundant(binding.typeAnnotation, 'removeParamType');
      }
    };

    const checkInferredFromInitializer = (
      annotatedNode: TSESTree.Node,
      annotation: TSESTree.TSTypeAnnotation | undefined,
      initializer: null | TSESTree.Expression,
    ) => {
      if (!annotation || !initializer || !selfDeterminedInitializers.has(initializer.type)) return;
      if (initializer.type === AST_NODE_TYPES.Identifier && initializer.name === 'undefined') return;

      const annotatedType = services.getTypeAtLocation(annotatedNode);
      const initializerType = services.getTypeAtLocation(initializer);
      if (annotatedType !== initializerType || !isInferableType(annotatedType)) return;

      reportRedundant(annotation, 'removeVarType');
    };

    const checkVariable = (declarator: TSESTree.VariableDeclarator) => {
      if (declarator.id.type !== AST_NODE_TYPES.Identifier) return;
      if (isDeclaratorAtModuleBoundary(declarator, exportedNames)) return;
      checkInferredFromInitializer(declarator.id, declarator.id.typeAnnotation, declarator.init);
    };

    const checkProperty = (property: TSESTree.PropertyDefinition) => {
      if (property.computed || property.key.type !== AST_NODE_TYPES.Identifier) return;
      if (hasExportedAncestor(property)) return;
      checkInferredFromInitializer(property.key, property.typeAnnotation, property.value);
    };

    return {
      ArrowFunctionExpression: arrow => {
        checkReturnType(arrow);
        checkParams(arrow);
      },
      Program: program => {
        exportedNames = collectExportedNames(program);
      },
      PropertyDefinition: checkProperty,
      VariableDeclarator: checkVariable,
    };
  },
  defaultOptions: [],
  meta: {
    docs: {
      description:
        'Disallow type annotations that only restate a type TypeScript already infers, and remove them. Covers three positions, each exempt at a module boundary (exported declarations, whose annotations may be load-bearing for declaration emit): (1) arrow-function return types — like `no-arrow-return-type`, skipping type predicates, generic returns, and recursive arrows; (2) arrow parameters whose type is fixed by a contextual function type that is independent of the annotation (callbacks such as `arr.map((x: number) => …)` and `const f: (a: T) => … = (a: T) => …`), where removal is type-preserving by contravariance — a parameter without a contextual type, or one that widens past it, keeps its annotation, as does one whose contextual type merely echoes the annotation: a self-referential type (an arrow whose own inferred type is fed back through generic inference, e.g. a property of an `Object.assign` source object) or a generic higher-order function that infers its own type parameter from the callback parameter (`pipe<A>(f: (a: A) => void)` called with `(x: number) => …`), since removing those collapses the parameter to `any`/`unknown`; (3) `const`/`let`/class-property declarations whose annotation matches the type inferred from a self-determined initializer (identifier, member access, template literal, unary or binary expression). Call/`new`/object/array/arrow initializers are deliberately left alone: their inferred type can depend on the annotation (generic inference, contextual typing), so removing it could silently change the type.',
    },
    fixable: 'code',
    messages: {
      removeParamType:
        'Parameter type annotation is redundant; its type is already fixed by the contextual function type. Let TypeScript infer it. (Parameters with no contextual type, and exported functions, are exempt.)',
      removeReturnType:
        'Explicit return type annotation is unnecessary; let TypeScript infer it. (Exported functions are exempt, since `tsc` may need the annotation for declaration-emit portability.)',
      removeVarType:
        'Type annotation is redundant; it restates the type already inferred from the initializer. Let TypeScript infer it. (Exported declarations are exempt, since `tsc` may need the annotation for declaration-emit portability.)',
    },
    schema: [],
    type: 'suggestion',
  },
  name: 'no-type-annotations',
});
