# Issue Creation — Full Algorithm

Create a GitHub or Linear issue from a plan file.

**Trigger**: User selects "Create issue" from plan presentation menu.
**Inputs**: plan title (string), plan path (string), talisman/CLAUDE.md config
**Outputs**: Issue URL displayed to user

## Algorithm

1. **Detect tracker** from CLAUDE.md or talisman.yml (`project_tracker: github` or `project_tracker: linear`)

2. **GitHub**:
   ```javascript
   // CDX-003 MITIGATION (P1): Validate and sanitize title/path before shell interpolation
   // to prevent command injection via crafted plan titles or filenames.
   const SAFE_IDENTIFIER_PATTERN = /^[a-zA-Z0-9 ._\-:()]+$/
   const SAFE_PATH_PATTERN = /^[a-zA-Z0-9._\-\/]+$/

   if (!SAFE_IDENTIFIER_PATTERN.test(title)) throw new Error('Unsafe characters in issue title')
   if (!SAFE_PATH_PATTERN.test(path) || path.includes('..')) throw new Error('Unsafe characters in plan path')

   // Use -- to separate flags from positional args, write title to temp file to avoid shell expansion
   Write('tmp/.issue-title.txt', `${type}: ${title}`)
   Bash(`gh issue create --title "$(< tmp/.issue-title.txt)" --body-file -- "plans/${path}"`)
   ```

3. **Linear**:
   ```javascript
   // CDX-003: Same validation applies to Linear CLI
   if (!SAFE_IDENTIFIER_PATTERN.test(title)) throw new Error('Unsafe characters in issue title')
   if (!SAFE_PATH_PATTERN.test(path) || path.includes('..')) throw new Error('Unsafe characters in plan path')

   Write('tmp/.issue-title.txt', title)
   Bash(`linear issue create --title "$(< tmp/.issue-title.txt)" --description - < "plans/${path}"`)
   ```

4. **No tracker configured**: Ask user and suggest adding `project_tracker: github` to CLAUDE.md.

5. **After creation**: Display issue URL, offer to proceed to /rune:work.
