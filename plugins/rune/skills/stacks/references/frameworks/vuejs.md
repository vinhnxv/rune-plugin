# Vue.js 3 Patterns for Rune

## Quick Reference

| Scenario | Pattern | Severity if violated |
|----------|---------|---------------------|
| Options API in new code | Use `<script setup lang="ts">` Composition API | P2 |
| Destructuring reactive object loses reactivity | Use `toRefs()` or `storeToRefs()` | P1 |
| Direct Pinia store state mutation | Mutate via store actions only | P1 |
| Missing `defineEmits` declaration | Add `defineEmits<{ event: [payload] }>()` | P2 |
| `v-html` with user-controlled input | Sanitize with DOMPurify or use text interpolation | P1 |
| Watcher used for derived state | Replace with `computed()` | P2 |
| `v-for` without `:key` | Add unique `:key` binding | P1 |
| Large component imported synchronously | Wrap with `defineAsyncComponent()` | P2 |
| Mutating props directly | Emit events to parent instead | P1 |
| `reactive()` for primitive values | Use `ref()` for primitives | P3 |

## Key Rules

### Rule 1: Composition API (VUE-001)
- BAD: `export default { data() { return { count: 0 } }, methods: { inc() { this.count++ } } }`
- GOOD: `<script setup lang="ts">` with `ref()`, composables, and no `this`
- Detection: `rg "export default \{" --glob "*.vue"` (flag Options API usage)

### Rule 2: Reactivity Correctness (VUE-002)
- BAD: `const { count } = useCounterStore()` (destroys reactivity — `count` is now a plain number)
- GOOD: `const { count } = storeToRefs(useCounterStore())` or `const store = useCounterStore(); store.count`
- BAD: `const { x, y } = reactive({ x: 0, y: 0 })` (same destructuring trap)
- GOOD: `const pos = reactive({ x: 0, y: 0 })` + access as `pos.x`, or `const { x, y } = toRefs(pos)`
- Detection: `rg "const \{.*\} = (use\w+Store|reactive)\(" --glob "*.{vue,ts}"` (review each)

### Rule 3: Pinia State Management (VUE-003)
- BAD: `store.count = 42` (direct state mutation outside action)
- GOOD: define `increment()` action in store, call `store.increment()`
- BAD: `store.$state.items.push(item)` (bypasses action layer)
- GOOD: `store.addItem(item)` via a store action
- Detection: `rg "\bstore\.\w+ =" --glob "*.{vue,ts}"` (flag direct assignments to store properties)

### Rule 4: Component Contracts (VUE-004)
- BAD: No props/emits declaration; relying on `$attrs` for everything
- GOOD: `const props = defineProps<{ label: string; count?: number }>()`
- GOOD: `const emit = defineEmits<{ change: [value: string]; close: [] }>()`
- GOOD (3.3+): `defineSlots<{ default(props: { item: Item }): any }>()`
- GOOD (3.4+): `const model = defineModel<string>()` (replaces modelValue + update:modelValue boilerplate)
- Detection: `rg "defineProps|defineEmits" --glob "*.vue"` (check for TypeScript generic form)

### Rule 5: Performance (VUE-005)
- BAD: Re-rendering expensive list on every parent update with no memoization
- GOOD: `v-memo="[item.id, item.selected]"` on list items whose output only changes when those values change
- GOOD: `v-once` on truly static subtrees
- GOOD: `shallowRef(largeObject)` to avoid deep reactivity tracking on large data
- GOOD: `KeepAlive` wrapping tab panels that are expensive to mount
- Detection: `rg "v-for" --glob "*.vue"` — verify `:key` present and `v-memo` used for expensive rows

### Rule 6: Template Security (VUE-006)
- BAD: `<div v-html="userBio"></div>` where `userBio` comes from an API or user input
- GOOD: `<div>{{ userBio }}</div>` (auto-escaped) or sanitize: `<div v-html="sanitize(userBio)"></div>`
- Note: Vue auto-escapes `{{ }}` expressions — XSS risk only surfaces with `v-html`
- Detection: `rg "v-html" --glob "*.vue"` (review every occurrence for user-controlled data)

## Anti-Patterns

| Anti-Pattern | Why It's Bad | Fix |
|-------------|-------------|-----|
| Options API in new components | Misses composable reuse, worse TypeScript inference | `<script setup lang="ts">` |
| Mutating props directly (`props.x = y`) | One-way data flow violation, Vue warns in dev | Emit event to parent |
| `this` inside `<script setup>` | `setup()` scope has no `this` | Use returned composable values directly |
| `watch` on a value that could be `computed` | Extra re-render, harder to trace | Replace with `computed()` |
| `reactive()` wrapping primitives | `let n = reactive(0)` is invalid; reassignment breaks ref | Use `ref()` for scalars |
| `v-html` with untrusted data | XSS vector — bypasses Vue's auto-escaping | Text interpolation or DOMPurify |
| Missing `:key` on `v-for` | Incorrect patch order, subtle UI bugs | `:key="item.id"` (unique, stable) |

## Performance Patterns

| Pattern | When | Impact |
|---------|------|--------|
| `defineAsyncComponent(() => import('./Heavy.vue'))` | Large or rarely-shown components | Smaller initial bundle |
| `<KeepAlive>` around tab panels | Tabs with expensive setup | Avoids remount on tab switch |
| `shallowRef(bigObj)` / `shallowReactive(bigObj)` | Large objects where only reference changes | Skips deep reactivity tracking |
| `v-once` | Truly static subtrees with no bindings | Skips diffing entirely |
| `v-memo="[dep1, dep2]"` | Expensive list rows, stable identity | Skips re-render unless deps change |
| Virtual scrolling (`vue-virtual-scroller`) | Lists with 500+ items | Constant DOM node count |

## Security Checklist

- [ ] No `v-html` with user-supplied or API-sourced data (sanitize with DOMPurify if unavoidable)
- [ ] CSP headers set on the server (`script-src 'self'`) to block injected scripts
- [ ] Slot content treated as untrusted — validate props passed into slots from external sources
- [ ] API response data validated (Zod/valibot) before binding to reactive state
- [ ] No secrets or tokens stored in Pinia state (persisted to localStorage via plugins)

## Audit Commands

```bash
# Find Options API components (candidates for migration)
rg "export default \{" --glob "*.vue"

# Find v-html usage (review each for XSS risk)
rg "v-html" --glob "*.vue"

# Find missing defineEmits (emits used without declaration)
rg "\$emit\(" --glob "*.vue" | rg -v "defineEmits"

# Find direct store state mutation
rg "\bstore\.\w+ =" --glob "*.{vue,ts,js}"

# Find v-for without :key
rg "v-for" --glob "*.vue" -A1 | rg -v ":key"

# Find reactive() wrapping primitive literals
rg "reactive\((0|''|\"\"|true|false|null)\)" --glob "*.{vue,ts}"

# Find props mutation (direct write to defineProps result)
rg "props\.\w+ =" --glob "*.{vue,ts}"
```
