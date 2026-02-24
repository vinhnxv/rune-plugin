# Hướng dẫn nâng cao Rune: Xử lý sự cố và Tối ưu

Chẩn đoán lỗi thường gặp, giảm chi phí token, và tối ưu workflow đa agent của Rune.

Hướng dẫn liên quan:
- [Bắt đầu nhanh](rune-getting-started.vi.md)
- [Hướng dẫn cấu hình Talisman](rune-talisman-deep-dive-guide.vi.md)
- [Hướng dẫn custom agent](rune-custom-agents-and-extensions-guide.vi.md)
- [Hướng dẫn arc và batch](rune-arc-and-batch-guide.vi.md)

---

## 1. Các lỗi thường gặp

### 1.1 Agent Teams chưa bật

**Triệu chứng**: Lệnh `/rune:*` thất bại với "Agent Teams not available".

**Sửa**: Thêm vào `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Khởi động lại Claude Code sau khi lưu.

### 1.2 Bash timeout kill ward checks

**Triệu chứng**: Ward commands (lint, test) bị kill giữa chừng. Lỗi "Command timed out after 120000ms".

**Sửa**: Tăng timeout trong `.claude/settings.json`:

```json
{
  "env": {
    "BASH_DEFAULT_TIMEOUT_MS": "600000",
    "BASH_MAX_TIMEOUT_MS": "3600000"
  }
}
```

**Nguyên nhân**: Timeout Bash mặc định là 2 phút. Hầu hết test suite cần lâu hơn.

### 1.3 Team cũ chặn workflow mới

**Triệu chứng**: TeamCreate thất bại với "team already exists".

**Sửa**: Hook `session-team-hygiene.sh` tự dọn team cũ khi bắt đầu session. TLC-001 tự dọn team quá 30 phút. Khởi động lại session nếu cần.

### 1.4 Freshness gate chặn arc

**Triệu chứng**: `/rune:arc` từ chối chạy với lỗi "Plan is STALE".

**Sửa**:
1. **Nhanh**: Thêm `--skip-freshness`
2. **Đúng cách**: Tạo lại plan bằng `/rune:devise`
3. **Điều chỉnh**: Hạ `plan.freshness.block_threshold` trong talisman

### 1.5 Hook chặn lệnh (ZSH-001, POLL-001, v.v.)

| Mã hook | Chặn gì | Lý do |
|---------|---------|-------|
| ZSH-001 | `status=` trong bash | `status` là read-only trong zsh |
| POLL-001 | `sleep N && echo check` | Phải dùng TaskList để monitor |
| SEC-001 | Write tools khi review | Review agent phải read-only |
| ATE-1 | `Task` không có `team_name` | Phải dùng `team_name` trong Rune workflow |

**Sửa**: Các hook này tồn tại vì đúng đắn. Điều chỉnh lệnh theo pattern được enforce.

### 1.6 Teammate idle sớm

**Triệu chứng**: Ash ngừng phản hồi trước khi hoàn thành review.

**Nguyên nhân**:
- Context window hết (quá nhiều file)
- SDK heartbeat timeout (5 phút hardcoded)
- Agent crash hoặc hết token

**Sửa**:
1. Giảm `context_budget` cho Ash đó
2. Kiểm tra `tmp/reviews/{id}/ash-outputs/` cho output chưa hoàn thành
3. Chạy lại review — task cũ tự được giải phóng sau 10 phút

### 1.7 Arc pipeline bị treo

**Triệu chứng**: Arc dường như bị kẹt ở một phase.

**Chẩn đoán**:
1. Kiểm tra `.claude/arc/{id}/checkpoint.json`
2. Kiểm tra `TaskList` cho task bị kẹt
3. Kiểm tra timeout của phase trong talisman

**Sửa**: Dùng `/rune:cancel-arc`, sau đó `/rune:arc plans/... --resume`.

---

## 2. Kỹ thuật Debug

### 2.1 Bật trace logging

```bash
export RUNE_TRACE=1
```

Traces ghi vào `/tmp/rune-hook-trace.log`.

### 2.2 Kiểm tra arc checkpoint

```bash
cat .claude/arc/*/checkpoint.json | python3 -m json.tool
```

### 2.3 Kiểm tra signal files

```bash
ls tmp/.rune-signals/*/
```

### 2.4 Xem ash outputs

Mỗi Ash viết output vào `tmp/reviews/{id}/ash-outputs/{ash-name}.md`. So sánh output để hiểu:
- Ash nào được triệu hồi và tại sao
- Mỗi Ash tìm thấy gì
- Seal markers có mặt không

### 2.5 Xem inscription contract

```bash
cat tmp/reviews/*/inscription.json | python3 -m json.tool
```

### 2.6 Verbose mode

```bash
claude --debug
```

---

## 3. Chiến lược tối ưu Token

### 3.1 Hệ số chi phí theo workflow

| Workflow | Team size | Hệ số | Thời gian |
|----------|----------|-------|-----------|
| `/rune:appraise` | 5-7 Ashes | 3-5x | 3-10 phút |
| `/rune:appraise --deep` | 12-18 Ashes | 8-15x | 10-20 phút |
| `/rune:devise` | 3-7 agents | 3-5x | 5-15 phút |
| `/rune:devise --quick` | 2-3 agents | 1.5-2x | 2-5 phút |
| `/rune:strive` | 2-4 workers | 2-4x | 10-30 phút |
| `/rune:arc` (đầy đủ) | thay đổi | 10-30x | 30-90 phút |

### 3.2 Giảm phạm vi review

| Chiến lược | Cách làm | Tiết kiệm |
|-----------|---------|-----------|
| PR nhỏ hơn | Giữ dưới 20 file | Tránh chunked review |
| Skip patterns | Thêm file generated/vendor vào `rune-gaze.skip_patterns` | Loại file không cần thiết |
| Giảm max_ashes | `settings.max_ashes: 5` | Ít teammate hơn |
| Tắt Ash không cần | `defaults.disable_ashes: ["veil-piercer"]` | Bớt 1 Ash |

### 3.3 Giảm phạm vi planning

| Chiến lược | Cách làm | Tiết kiệm |
|-----------|---------|-----------|
| Chế độ `--quick` | `/rune:devise --quick` | Bỏ brainstorm + forge |
| Goldmask basic | `goldmask.devise.depth: "basic"` | 2 agent thay vì 6 |
| Tắt arena | `solution_arena.enabled: false` | Không đánh giá cạnh tranh |
| Tắt elicitation | `elicitation.enabled: false` | Không structured reasoning |

### 3.4 Giảm phạm vi arc

| Chiến lược | Cách làm | Tiết kiệm |
|-----------|---------|-----------|
| `--no-forge` | Bỏ forge enrichment | Tiết kiệm 15 phút + agents |
| `--no-test` | Bỏ test phase | Tiết kiệm test |
| Convergence nhẹ | `arc_convergence_tier_override: "light"` | Max 2 review-mend cycles |
| Tắt Codex | `codex.disabled: true` | Không cross-model verification |

### 3.5 Chọn workflow tiết kiệm

| Nhu cầu | Tuỳ chọn rẻ nhất | Chi phí |
|---------|-----------------|---------|
| Feedback nhanh | `/rune:appraise` (standard) | ~3-5x |
| Plan feature đơn giản | `/rune:devise --quick` | ~1.5-2x |
| Implement có chất lượng | `/rune:strive` riêng (không arc) | ~2-4x |
| Pipeline đầy đủ | `/rune:arc` với `--no-forge` | ~8-20x |
| Chất lượng tối đa | `/rune:arc` (đầy đủ, deep review) | ~15-30x |

---

## 4. Tinh chỉnh hiệu suất

### 4.1 Tối ưu worker song song

```yaml
work:
  max_workers: 3
```

| Kích cỡ dự án | Workers khuyến nghị | Lý do |
|--------------|-------------------|-------|
| Nhỏ (< 10 tasks) | 2 | Tránh xung đột file |
| Trung bình (10-20) | 3 | Song song tốt |
| Lớn (20+) | 4-5 | Throughput tối đa |

**Cảnh báo**: Nhiều worker = nhiều rủi ro xung đột file.

### 4.2 Điều chỉnh timeout phase

```yaml
arc:
  timeouts:
    work: 2400000       # 40 phút cho implementation lớn
    code_review: 1200000  # 20 phút cho deep review
    test: 2400000        # 40 phút khi E2E chậm
```

### 4.3 Audit tăng dần cho codebase lớn

Codebase 500+ file nên dùng incremental audit:

```bash
/rune:audit --incremental
```

---

## 5. Quản lý Session

### 5.1 Cách ly session

Mỗi session Rune theo dõi workflow qua state files với `config_dir`, `owner_pid`, và `session_id`. Các session khác nhau không can thiệp lẫn nhau.

### 5.2 Tiếp tục sau gián đoạn

```bash
# Arc pipeline
/rune:arc plans/my-plan.md --resume

# Arc batch
/rune:arc-batch plans/*.md --resume
```

### 5.3 Dọn dẹp sau workflow

```bash
/rune:rest
```

Xoá artifact `tmp/` nhưng giữ Rune Echoes (`.claude/echoes/`).

### 5.4 Teammate không persistent

Teammate KHÔNG sống sót qua session resume. Sau `/resume`:
- Tất cả teammate được coi là đã chết
- Team cũ tự dọn dẹp
- Khởi động lại workflow từ checkpoint nếu cần

---

## 6. Công thức xử lý sự cố

### "Arc tiêu tốn quá nhiều token"

1. Dùng `--no-forge` bỏ enrichment
2. `review.arc_convergence_tier_override: "light"` — ít review-mend cycles
3. `codex.disabled: true` — tắt cross-model
4. `work.max_workers: 2` — giảm worker

### "Review cứ tìm issue cũ (pre-existing)"

1. Bật diff-scope: `review.diff_scope.enabled: true` (mặc định)
2. `review.diff_scope.tag_pre_existing: true` (mặc định)
3. Mend tự bỏ pre-existing P2/P3 — chỉ P1 luôn được fix

### "Custom Ash không được triệu hồi"

1. Kiểm tra `trigger.extensions` khớp file thay đổi
2. Kiểm tra `trigger.paths` khớp đường dẫn
3. Xác nhận `settings.max_ashes` không quá thấp
4. Kiểm tra `workflows` gồm workflow đang chạy

### "Forge enrichment quá chậm"

1. Dùng `--quick` với `/rune:devise`
2. Hạ `forge.max_total_agents: 4`
3. Tăng `forge.threshold: 0.50`

### "Test thất bại trong arc Phase 7.7"

1. Test failure là WARN — không dừng pipeline
2. Kiểm tra `testing.service.startup_command`
3. Tăng `testing.tiers.*.timeout_ms`
4. Tắt tier: `testing.tiers.e2e.enabled: false`

---

## 7. Checklist kiểm tra sức khoẻ

- [ ] Agent Teams đã bật trong `.claude/settings.json`
- [ ] `BASH_DEFAULT_TIMEOUT_MS` >= 600000
- [ ] `BASH_MAX_TIMEOUT_MS` >= 3600000
- [ ] Ward commands hoàn thành trong bash timeout
- [ ] `talisman.yml` là YAML hợp lệ
- [ ] Custom Ash prefix có trong `dedup_hierarchy`
- [ ] Custom Ash agent tồn tại ở source path khai báo
- [ ] `skip_patterns` không loại file bạn muốn review
- [ ] `max_ashes` đủ lớn cho built-in + custom
- [ ] `gh` CLI đã cài và xác thực (cho arc ship/merge)
- [ ] Không có thư mục team orphan (`ls ~/.claude/teams/`)
- [ ] Không có state file cũ (`ls tmp/.rune-*.json`)
