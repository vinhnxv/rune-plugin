# Paginated Fetch

Fetches ALL PR comments to tmp files using GraphQL cursor pagination and REST pagination. Avoids loading everything into agent context at once.

**Inputs**: `prNumber`, `owner`, `repo`, `outputDir`
**Outputs**: `review-threads.json`, `issue-comments.json`, `review-comments.json` in `outputDir`
**Preconditions**: `gh` CLI authenticated, PR exists, `outputDir` created

## Phase 3a: Fetch Review Threads via GraphQL

```
# CRITICAL: Use $endCursor (not $cursor) for gh --paginate compatibility
Bash("GH_PROMPT_DISABLED=1 gh api graphql --paginate -f query='
query(\$endCursor: String) {
  repository(owner: \"${owner}\", name: \"${repo}\") {
    pullRequest(number: ${prNumber}) {
      reviewThreads(first: 100, after: \$endCursor) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 10) {
            nodes {
              id
              databaseId
              author { login }
              body
              path
              line
              url
              createdAt
              updatedAt
            }
          }
        }
      }
    }
  }
}' > '${outputDir}/review-threads.json'")
```

## Phase 3b: Fetch Issue Comments (REST, paginated)

```
# Bot summary comments live on the issue (PR) itself
Bash("GH_PROMPT_DISABLED=1 gh api --paginate 'repos/${owner}/${repo}/issues/${prNumber}/comments?per_page=100' > '${outputDir}/issue-comments.json'")
```

## Phase 3c: Fetch PR Review Comments (REST, paginated)

```
# Inline bot comments on specific code lines
Bash("GH_PROMPT_DISABLED=1 gh api --paginate 'repos/${owner}/${repo}/pulls/${prNumber}/comments?per_page=100' > '${outputDir}/review-comments.json'")
```
