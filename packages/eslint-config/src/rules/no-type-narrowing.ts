import type { TSESLint, TSESTree } from '@typescript-eslint/utils';

import { AST_NODE_TYPES, ESLintUtils } from '@typescript-eslint/utils';
import * as ts from 'typescript';

import { createRule } from '#create-rule';

type FunctionNode = TSESTree.ArrowFunctionExpression | TSESTree.FunctionDeclaration | TSESTree.FunctionExpression;

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

const getFunctionName = (fn: FunctionNode) => {
  if ('id' in fn && fn.id) return fn.id.name;
  const { parent } = fn;
  if (parent.type === AST_NODE_TYPES.VariableDeclarator && parent.id.type === AST_NODE_TYPES.Identifier) {
    return parent.id.name;
  }
  if ('key' in parent && 'computed' in parent && !parent.computed && parent.key.type === AST_NODE_TYPES.Identifier) {
    return parent.key.name;
  }
  return;
};

const isRecursiveFunction = (fn: FunctionNode) => {
  const name = getFunctionName(fn);
  return name !== undefined && hasMatchingNode(fn.body, n => isIdentifierNamed(n, candidate => candidate === name));
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

const isNestedFunctionNode = (node: ts.Node) =>
  ts.isFunctionDeclaration(node) ||
  ts.isFunctionExpression(node) ||
  ts.isArrowFunction(node) ||
  ts.isMethodDeclaration(node) ||
  ts.isGetAccessorDeclaration(node) ||
  ts.isSetAccessorDeclaration(node) ||
  ts.isConstructorDeclaration(node);

const collectReturnExpressions = (node: ts.Node, found: ts.Expression[]) => {
  node.forEachChild(child => {
    if (isNestedFunctionNode(child)) return;
    if (ts.isReturnStatement(child) && child.expression) found.push(child.expression);
    collectReturnExpressions(child, found);
  });
};

const hasFixedFields = (annotationType: ts.Type) =>
  annotationType.getProperties().length > 0 && !annotationType.getStringIndexType();

const isNamedField = (member: ts.Symbol) => !member.getName().startsWith('__');

const findHiddenMembers = (annotationType: ts.Type, valueTypes: readonly ts.Type[]) => {
  const [first, ...rest] = valueTypes;
  if (!first) return [];
  const hidden: string[] = [];
  for (const member of first.getProperties()) {
    const name = member.getName();
    if (!isNamedField(member) || annotationType.getProperty(name)) continue;
    if (rest.every(valueType => valueType.getProperty(name))) hidden.push(name);
  }
  return hidden;
};

type NarrowingReport = {
  annotationNode: TSESTree.TSTypeAnnotation;
  annotationType: ts.Type;
  fix: TSESLint.ReportFixFunction;
  messageId: 'narrowReturnType' | 'narrowVarType';
  valueTypes: readonly ts.Type[];
};

export const noTypeNarrowing = createRule({
  create: context => {
    const services = ESLintUtils.getParserServices(context);
    const checker = services.program.getTypeChecker();

    const reportNarrowing = ({ annotationNode, annotationType, fix, messageId, valueTypes }: NarrowingReport) => {
      if (!hasFixedFields(annotationType)) return;
      const hidden = findHiddenMembers(annotationType, valueTypes);
      if (hidden.length === 0) return;

      context.report({
        data: { members: hidden.join(', ') },
        messageId,
        node: annotationNode,
        suggest: [{ fix, messageId: 'removeAnnotation' }],
      });
    };

    const collectReturnedTypes = (fn: FunctionNode) => {
      const { body } = fn;
      if (body.type !== AST_NODE_TYPES.BlockStatement) return [services.getTypeAtLocation(body)];
      const expressions: ts.Expression[] = [];
      collectReturnExpressions(services.esTreeNodeToTSNodeMap.get(body), expressions);
      return expressions.map(expression => checker.getTypeAtLocation(expression));
    };

    const checkFunctionReturn = (fn: FunctionNode) => {
      const returnAnnotation = fn.returnType;
      if (!returnAnnotation) return;
      if (returnAnnotation.typeAnnotation.type === AST_NODE_TYPES.TSTypePredicate) return;
      if (fn.async || ('generator' in fn && fn.generator)) return;

      const typeParamNames = collectTypeParamNames(fn.typeParameters);
      if (typeParamNames.size > 0 && hasTypeParamReference(returnAnnotation.typeAnnotation, typeParamNames)) return;
      if (isRecursiveFunction(fn)) return;

      const tokenBefore = context.sourceCode.getTokenBefore(returnAnnotation);
      if (!tokenBefore) return;

      const signature = checker.getSignatureFromDeclaration(services.esTreeNodeToTSNodeMap.get(fn));
      if (!signature) return;

      const valueTypes = collectReturnedTypes(fn);
      if (valueTypes.length === 0) return;

      reportNarrowing({
        annotationNode: returnAnnotation,
        annotationType: signature.getReturnType(),
        fix: fixer => fixer.removeRange([tokenBefore.range[1], returnAnnotation.range[1]]),
        messageId: 'narrowReturnType',
        valueTypes,
      });
    };

    const checkVariable = (declarator: TSESTree.VariableDeclarator) => {
      if (declarator.id.type !== AST_NODE_TYPES.Identifier) return;
      const annotation = declarator.id.typeAnnotation;
      if (!annotation || !declarator.init) return;

      const [variable] = context.sourceCode.getDeclaredVariables(declarator);
      const wasReassigned =
        variable?.references.some(reference => reference.isWrite() && reference.identifier !== declarator.id) ?? false;
      if (wasReassigned) return;

      reportNarrowing({
        annotationNode: annotation,
        annotationType: services.getTypeAtLocation(declarator.id),
        fix: fixer => fixer.removeRange(annotation.range),
        messageId: 'narrowVarType',
        valueTypes: [services.getTypeAtLocation(declarator.init)],
      });
    };

    return {
      ArrowFunctionExpression: checkFunctionReturn,
      FunctionDeclaration: checkFunctionReturn,
      FunctionExpression: checkFunctionReturn,
      VariableDeclarator: checkVariable,
    };
  },
  defaultOptions: [],
  meta: {
    docs: {
      description:
        "Disallow type annotations that narrow a value to a supertype hiding members the value actually has, and suggest removing them. Such an annotation silently discards information at that boundary — `(): { a: number } => objWith3Fields` exposes one field of three, and `const s: ReadonlySet<string> = new Set(...)` types a mutable Set as if it were readonly. Covers (1) function return types — arrow (concise and block bodies), function, and method — comparing the annotation against the members common to every `return`; and (2) `const`/`let` declarations. This applies everywhere, including exported declarations: narrowing discards information regardless of visibility, so there is no module-boundary excuse — when a narrower public type is genuinely intended, return or assign a value that has only those members, or express the constraint with `satisfies`. Skipped: type predicates; recursive functions (whose annotation prevents an implicit-any TS7023); generic returns that reference a type parameter; async and generator functions (their body type is the resolved/yielded value, not the declared wrapper); and a reassigned `let` (the wider type may be required by a later assignment). Only annotations that hide a member are reported, so an index-signature ('open dictionary') type, erasure to `any`/`unknown`/`{}`, and literal widening (`number` for `5`) never are — while narrowing through any named type, including a base class, an interface, or a readonly collection view such as `ReadonlySet` or `readonly T[]`, is reported (the readonly fiction can be dropped, or expressed with `satisfies` or a genuinely immutable value). The fix is a suggestion, not an autofix, since removing the annotation widens the exposed type.",
    },
    hasSuggestions: true,
    messages: {
      narrowReturnType:
        'This return type hides member(s) the returned value has: {{members}}. Narrowing discards information — remove the annotation to expose the full inferred type, or return a value that genuinely has only these members.',
      narrowVarType:
        'This type annotation hides member(s) the value has: {{members}}. Narrowing discards information — remove the annotation to keep the full inferred type, or assign a value that genuinely has only these members.',
      removeAnnotation: 'Remove the narrowing annotation and keep the full inferred type.',
    },
    schema: [],
    type: 'suggestion',
  },
  name: 'no-type-narrowing',
});
