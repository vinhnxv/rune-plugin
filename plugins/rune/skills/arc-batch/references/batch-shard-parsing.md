# Shard Group Detection (v1.66.0+)

Separates shard plans from regular plans, groups by feature prefix, sorts by shard number,
detects gaps, and optionally excludes parent plans (shattered: true).
Extracted from SKILL.md Phase 0 in v1.110.0 for context reduction.

**Consumers**: SKILL.md Phase 0 (after initial plan list construction)
**Inputs**: `planPaths` (array), `args` (string with flags), `talisman` (parsed config)
**Outputs**: Reordered `planPaths` array, `shardGroups` Map for Phase 3 progress file

## Skip Conditions

Shard detection is skipped when ANY of:
- `--no-shard-sort` flag
- `--resume` mode
- `planPaths.length <= 1`
- `talisman.arc.sharding.enabled === false`
- `talisman.arc.sharding.auto_sort === false`

## Algorithm

```javascript
const noShardSort = args.includes('--no-shard-sort')
// readTalismanSection: "arc"
const arc = readTalismanSection("arc")
const shardConfig = arc?.sharding ?? {}
const shardEnabled = shardConfig.enabled !== false  // default: true (PS-007 FIX: honor master enabled flag)
const autoSort = shardConfig.auto_sort !== false  // default: true
const excludeParent = shardConfig.exclude_parent !== false  // default: true

if (!noShardSort && shardEnabled && autoSort && !resumeMode && planPaths.length > 1) {
  // Separate shard plans from regular plans
  const shardPlans = []
  const regularPlans = []
  const parentPlansToExclude = []

  for (const path of planPaths) {
    const shardMatch = path.match(/-shard-(\d+)-/)
    if (shardMatch) {
      shardPlans.push({
        path,
        shardNum: parseInt(shardMatch[1]),
        // Extract feature prefix: everything before "-shard-N-{phase}-plan.md"
        // Consistent regex with Task 1.1 and parse-plan.md
        featurePrefix: path.replace(/-shard-\d+-[^-]+-plan\.md$/, '')
      })
    } else {
      regularPlans.push(path)
    }
  }

  // F-004 FIX: Declare shardGroups in outer scope to avoid block-scoping fragility
  let shardGroups = new Map()

  if (shardPlans.length > 0) {
    // Check for parent plans in regularPlans (auto-exclude if shattered: true)
    const filteredRegular = []
    if (excludeParent) {
      for (const path of regularPlans) {
        try {
          const content = Read(path)
          const frontmatter = extractYamlFrontmatter(content)
          if (frontmatter?.shattered === true) {
            parentPlansToExclude.push(path)
            continue
          }
        } catch (e) {
          // Can't read — keep it
        }
        filteredRegular.push(path)
      }
    } else {
      filteredRegular.push(...regularPlans)
    }

    if (parentPlansToExclude.length > 0) {
      warn(`Auto-excluded ${parentPlansToExclude.length} parent plan(s) (shattered: true):`)
      for (const p of parentPlansToExclude) {
        warn(`  - ${p}`)
      }
    }

    // Group shards by feature prefix
    shardGroups = new Map()  // reset (outer-scope let)
    for (const shard of shardPlans) {
      if (!shardGroups.has(shard.featurePrefix)) {
        shardGroups.set(shard.featurePrefix, [])
      }
      shardGroups.get(shard.featurePrefix).push(shard)
    }

    // Sort each group by shard number
    for (const [prefix, shards] of shardGroups) {
      shards.sort((a, b) => a.shardNum - b.shardNum)
    }

    // Detect missing shards within groups
    for (const [prefix, shards] of shardGroups) {
      const nums = shards.map(s => s.shardNum)
      if (nums.length === 0) continue  // F-002 FIX: guard against Math.max() = -Infinity
      const maxNum = Math.max(...nums)
      const missing = []
      for (let i = 1; i <= maxNum; i++) {
        if (!nums.includes(i)) missing.push(i)
      }
      if (missing.length > 0) {
        warn(`Shard group "${prefix.replace(/.*\//, '')}" has gaps: missing shard(s) ${missing.join(', ')}`)
      }
    }

    // Rebuild plan paths: regular plans first, then shard groups in order
    planPaths = [
      ...filteredRegular,
      ...Array.from(shardGroups.values()).flat().map(s => s.path)
    ]

    log(`Shard-aware ordering: ${filteredRegular.length} regular + ${shardPlans.length} shard plans across ${shardGroups.size} group(s)`)
    if (parentPlansToExclude.length > 0) {
      log(`Excluded ${parentPlansToExclude.length} parent plan(s)`)
    }
  }
}
```
