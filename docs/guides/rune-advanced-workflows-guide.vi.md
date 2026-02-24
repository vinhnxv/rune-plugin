# Hướng dẫn Rune (Tiếng Việt): `/rune:arc-hierarchy`, `/rune:arc-issues`, và `/rune:echoes`

Hướng dẫn này bao gồm các workflow nâng cao của Rune dành cho người dùng chuyên sâu:
- `/rune:arc-hierarchy` — thực thi phân rã plan cha/con theo thứ tự.
- `/rune:arc-issues` — thực thi batch dựa trên GitHub Issues.
- `/rune:echoes` — quản lý bộ nhớ agent bền vững.

Các hướng dẫn liên quan:
- [Hướng dẫn arc và batch (arc/arc-batch)](rune-arc-and-batch-guide.vi.md)
- [Hướng dẫn planning (devise/forge/plan-review/inspect)](rune-planning-and-plan-quality-guide.vi.md)
- [Hướng dẫn review và audit (appraise/audit/mend)](rune-code-review-and-audit-guide.vi.md)
- [Hướng dẫn thực thi (strive/goldmask)](rune-work-execution-guide.vi.md)

---

## 1. Chọn lệnh nhanh

| Tình huống | Lệnh khuyến nghị |
|---|---|
| Thực thi plan cha với các plan con theo thứ tự | `/rune:arc-hierarchy plans/parent-plan.md` |
| Xử lý GitHub issues như hàng đợi | `/rune:arc-issues --label "rune:ready"` |
| Xử lý các issue cụ thể | `/rune:arc-issues 42 55 78` |
| Khởi tạo bộ nhớ agent cho dự án | `/rune:echoes init` |
| Xem trạng thái bộ nhớ theo vai trò | `/rune:echoes show` |
| Ghi nhớ vĩnh viễn | `/rune:echoes remember "Luôn dùng UTC timestamps"` |
| Dọn dẹp bộ nhớ cũ | `/rune:echoes prune` |

---

## 2. `/rune:arc-hierarchy` — Thực thi Plan phân cấp

### 2.1 Khi nào dùng

Dùng plan phân cấp khi feature có:
- Nhiều giai đoạn implementation phải chạy theo thứ tự nghiêm ngặt.
- Dependency artifact giữa các giai đoạn (giai đoạn trước tạo type/file cho giai đoạn sau).
- Task quá lớn cho một lần arc nhưng quá liên kết để tách thành plan độc lập.

### 2.2 Quy trình

1. **Lập plan** — chạy `/rune:devise` và chọn "Hierarchical" tại Phase 2.5 (xuất hiện khi complexity >= 0.65).
2. **Kiểm tra** — xem bảng thực thi và ma trận dependency contract của plan cha.
3. **Thực thi** — chạy `/rune:arc-hierarchy plans/parent-plan.md`.
4. **Mỗi plan con** chạy pipeline arc 23 giai đoạn đầy đủ (forge → work → review → mend → test → ship).
5. **Một PR duy nhất** vào main được tạo sau khi tất cả plan con hoàn thành.

### 2.3 Các flag

| Flag | Tác dụng |
|---|---|
| `--resume` | Tiếp tục từ trạng thái bảng thực thi hiện tại |
| `--dry-run` | Hiển thị thứ tự thực thi và contract, thoát mà không chạy |
| `--no-merge` | Truyền `--no-merge` cho mỗi lần chạy arc con |

### 2.4 Contract: requires và provides

Mỗi plan con khai báo những gì nó cần (requires) và cung cấp (provides):

```yaml
# Trong bảng thực thi plan cha
children:
  - name: "01-database-schema"
    provides: [User model, migration files]
  - name: "02-api-endpoints"
    requires: [User model]
    provides: [REST API, OpenAPI spec]
  - name: "03-frontend"
    requires: [REST API]
```

Trước khi chạy mỗi plan con, Rune xác minh tất cả artifact cần thiết đã tồn tại. Sau khi hoàn thành, Rune xác minh tất cả artifact đã hứa đã được tạo.

### 2.5 Xử lý lỗi

| Lỗi | Chiến lược xử lý |
|---|---|
| Thiếu prerequisite | `pause` (mặc định, hỏi user), `self-heal` (thêm task khôi phục), `backtrack` (chạy lại plan cung cấp) |
| Xác minh provides thất bại | Đánh dấu hoàn thành, chạy lại plan con, bỏ qua dependent, hoặc hủy |
| Dependency vòng tròn | Phát hiện và cảnh báo, liệt kê plan con bị block |
| Plan con arc thất bại | Cảnh báo, đề nghị bỏ qua dependent hoặc hủy |

Cấu hình trong talisman:

```yaml
work:
  hierarchy:
    missing_prerequisite: "pause"    # pause | self-heal | backtrack
    max_children: 12
    max_backtracks: 1
```

### 2.6 Hủy

```bash
/rune:cancel-arc-hierarchy
```

Plan con đang thực thi sẽ hoàn thành bình thường. Không có plan con mới nào sẽ bắt đầu.

---

## 3. `/rune:arc-issues` — Thực thi Batch từ GitHub Issues

### 3.1 Khi nào dùng

Dùng arc-issues khi bạn có backlog GitHub issues sẵn sàng để implementation tự động. Mỗi issue trở thành một plan, chạy qua pipeline arc đầy đủ, và tạo PR tự động đóng issue khi merge.

### 3.2 Phương thức input

```bash
# Theo label (phổ biến nhất)
/rune:arc-issues --label "rune:ready"

# Duyệt TẤT CẢ issues khớp
/rune:arc-issues --label "rune:ready" --all

# Từ file hàng đợi
/rune:arc-issues issues-queue.txt

# Số issue cụ thể
/rune:arc-issues 42 55 78
```

### 3.3 Các flag

| Flag | Tác dụng |
|---|---|
| `--label <label>` | Lấy issues mở có label này |
| `--all` | Duyệt tất cả issues khớp (không chỉ trang đầu) |
| `--page-size <N>` | Số issues mỗi trang với `--all` (mặc định: 10) |
| `--limit <N>` | Số issues tối đa (batch đơn, mặc định: 20) |
| `--milestone <name>` | Lọc theo milestone |
| `--no-merge` | Bỏ qua auto-merge trong mỗi lần arc |
| `--dry-run` | Liệt kê issues và thoát mà không chạy |
| `--force` | Bỏ qua quality gate (body < 50 ký tự) |
| `--resume` | Tiếp tục từ file progress |
| `--cleanup-labels` | Xóa label `rune:in-progress` mồ côi (> 2 giờ) |

### 3.4 Vòng đời label

| Label | Ý nghĩa | Hành động |
|---|---|---|
| `rune:ready` | Issue sẵn sàng xử lý | (label kích hoạt — bạn thêm label này) |
| `rune:in-progress` | Đang được Rune xử lý | Chờ hoàn thành |
| `rune:done` | Hoàn thành — PR liên kết qua `Fixes #N` | Issue tự đóng khi PR merge |
| `rune:failed` | Arc thất bại, cần sửa thủ công | Sửa body issue → xóa label → chạy lại |
| `rune:needs-review` | Chất lượng plan thấp hoặc có conflict | Thêm chi tiết → xóa label → chạy lại |

### 3.5 Xử lý mỗi issue

1. Body issue được sanitize và chuyển thành file plan trong `tmp/gh-plans/`.
2. Chất lượng plan được kiểm tra (body >= 50 ký tự, hoặc `--force` để bỏ qua).
3. Pipeline arc 23 giai đoạn đầy đủ chạy (forge → work → review → mend → test → ship → merge).
4. Thành công: PR với `Fixes #{number}`, comment thành công, label `rune:done`.
5. Thất bại: comment lỗi, label `rune:failed`.

### 3.6 Tiếp tục và hủy

```bash
/rune:arc-issues --resume            # Tiếp tục từ batch-progress.json
/rune:cancel-arc-issues              # Dừng sau khi issue hiện tại hoàn thành
```

### 3.7 Dọn dẹp label mồ côi

Nếu phiên crash giữa chừng, issues có thể giữ label `rune:in-progress`:

```bash
/rune:arc-issues --cleanup-labels    # Xóa label trên issues > 2 giờ
```

---

## 4. `/rune:echoes` — Bộ nhớ Agent

### 4.1 Echoes là gì

Rune Echoes là hệ thống bộ nhớ bền vững lưu trong `.claude/echoes/`. Sau các lần review, audit, và implementation, agent lưu lại pattern và bài học. Các phiên sau đọc echoes này để cải thiện chất lượng theo thời gian.

### 4.2 Vòng đời năm tầng

| Tầng | Tên | Thời hạn | Cách hoạt động |
|---|---|---|---|
| Cấu trúc | **Etched** | Vĩnh viễn | Quyết định kiến trúc, tech stack. Không bao giờ tự xóa |
| Do User | **Notes** | Vĩnh viễn | Tạo qua `/rune:echoes remember`. Không bao giờ tự xóa |
| Chiến thuật | **Inscribed** | 90 ngày không tham chiếu | Pattern từ review/audit. Điểm đa yếu tố xóa 20% thấp nhất |
| Agent phát hiện | **Observations** | 60 ngày lần truy cập cuối | Pattern agent phát hiện. Tự thăng lên Inscribed sau 3 lần tham chiếu |
| Phiên | **Traced** | 30 ngày | Quan sát theo phiên. Xóa dựa trên tiện ích |

### 4.3 Các lệnh

```bash
/rune:echoes init                    # Khởi tạo thư mục bộ nhớ cho dự án
/rune:echoes show                    # Hiển thị thống kê theo vai trò
/rune:echoes prune                   # Chấm điểm và lưu trữ entry cũ
/rune:echoes reset                   # Xóa tất cả echoes (có backup)
/rune:echoes remember <text>         # Tạo entry Notes vĩnh viễn
/rune:echoes promote <ref> --category <cat>  # Thăng lên tài liệu Remembrance
/rune:echoes remembrance [category]  # Truy vấn tài liệu Remembrance
/rune:echoes migrate                 # Di chuyển echoes sau khi nâng cấp
```

### 4.4 Lệnh `remember`

```bash
/rune:echoes remember "Luôn dùng UTC cho timestamp trong dự án này"
/rune:echoes remember "Module auth dùng bcrypt, không phải argon2"
```

Tạo entry tầng Notes vĩnh viễn và không bao giờ tự xóa. Dùng cho quy ước dự án, quyết định team, hoặc bất cứ gì bạn muốn agent luôn biết.

### 4.5 Echoes cải thiện workflow thế nào

| Workflow | Cách echoes được dùng |
|---|---|
| `/rune:appraise` | Reviewer đọc phát hiện trước để tránh báo cáo trùng lặp |
| `/rune:audit` | Auditor xây dựng trên kiến thức audit trước |
| `/rune:devise` | Echo Reader agent đưa ra bài học liên quan từ quá khứ |
| `/rune:strive` | Worker đọc pattern implementation từ phiên trước |

### 4.6 Cấu trúc bộ nhớ

```
.claude/echoes/
├── planner/MEMORY.md      # Pattern planning
├── workers/MEMORY.md      # Pattern implementation
├── reviewer/MEMORY.md     # Phát hiện review
├── auditor/MEMORY.md      # Phát hiện audit
├── notes/MEMORY.md        # Bộ nhớ do user tạo
├── observations/MEMORY.md # Pattern agent phát hiện
└── team/MEMORY.md         # Kiến thức liên vai trò
```

Mỗi file MEMORY.md có giới hạn 150 dòng với tự động dọn dẹp.

### 4.7 Remembrance (thăng cấp)

Bài học có độ tin cậy cao có thể được thăng lên tài liệu giải pháp dễ đọc:

```bash
/rune:echoes promote "N+1 query pattern trong UserService" --category performance
```

Entry được thăng trở thành tài liệu có phiên bản trong `docs/solutions/`. Danh mục: `build-errors`, `test-failures`, `runtime-errors`, `configuration`, `performance`, `security`, `architecture`, `tooling`.

### 4.8 Cấu hình

```yaml
# .claude/talisman.yml
echoes:
  version_controlled: false    # Đặt true để track echoes trong git
  decomposition:
    enabled: true              # Phân rã truy vấn cho tìm kiếm
  reranking:
    enabled: true              # Haiku reranking cho kết quả tìm kiếm
  semantic_groups:
    expansion_enabled: true    # Mở rộng nhóm trong tìm kiếm
```

---

## 5. Use Case

### 5.1 Feature lớn với plan con phân rã

```bash
/rune:devise                                              # Chọn "Hierarchical" khi được đề nghị
/rune:arc-hierarchy plans/2026-02-24-feat-auth-plan.md    # Thực thi tất cả plan con theo thứ tự
```

### 5.2 Sprint backlog từ GitHub Issues

```bash
# Gắn label issues sẵn sàng
/rune:arc-issues --label "rune:ready" --dry-run    # Xem trước hàng đợi
/rune:arc-issues --label "rune:ready" --no-merge   # Chạy với gate merge thủ công
```

### 5.3 Xây dựng bộ nhớ dự án từ đầu

```bash
/rune:echoes init                    # Thiết lập thư mục
/rune:echoes remember "Dùng pnpm, không phải npm"
/rune:echoes remember "API responses theo JSON:API spec"
/rune:appraise                       # Review ghi phát hiện vào echoes
/rune:echoes show                    # Kiểm tra đã học được gì
```

### 5.4 Xử lý issues cụ thể

```bash
/rune:arc-issues 42 55 78           # Xử lý ba issues này
/rune:arc-issues --resume           # Tiếp tục nếu bị gián đoạn
```

---

## 6. Xử lý sự cố

| Triệu chứng | Nguyên nhân | Hành động |
|---|---|---|
| Plan con hierarchy thất bại | Dependency phức tạp hoặc lỗi implementation | Kiểm tra log arc con. Dùng `--resume` để thử lại |
| "Circular dependency detected" | Plan con có requires lẫn nhau | Sửa ma trận contract trong plan cha |
| Thiếu prerequisite | Plan con trước không tạo artifact mong đợi | Chọn chiến lược pause/self-heal/backtrack |
| Label `rune:in-progress` bị kẹt | Phiên crash giữa chừng | `/rune:arc-issues --cleanup-labels` |
| Body issue quá ngắn | Body < 50 ký tự không qua quality gate | Thêm chi tiết hoặc dùng `--force` |
| Lỗi `gh` CLI | Chưa cài hoặc chưa xác thực | Cài `gh` và chạy `gh auth login` |
| Echoes không cải thiện kết quả | Bộ nhớ chưa khởi tạo | `/rune:echoes init` trước |
| MEMORY.md quá lớn | Vượt giới hạn 150 dòng | `/rune:echoes prune` để lưu trữ entry cũ |
| Batch dừng sau một issue | File state Stop hook bị xóa | Kiểm tra `.claude/arc-issues-loop.local.md` |

---

## 7. Tham chiếu lệnh nhanh

```bash
# Thực thi phân cấp
/rune:arc-hierarchy plans/parent-plan.md              # Thực thi plan con theo thứ tự
/rune:arc-hierarchy plans/parent-plan.md --dry-run    # Xem trước thứ tự thực thi
/rune:arc-hierarchy plans/parent-plan.md --resume     # Tiếp tục từ checkpoint
/rune:cancel-arc-hierarchy                            # Dừng sau plan con hiện tại

# GitHub Issues batch
/rune:arc-issues --label "rune:ready"                 # Theo label
/rune:arc-issues --label "rune:ready" --all           # Tất cả issues khớp
/rune:arc-issues 42 55 78                             # Issues cụ thể
/rune:arc-issues --dry-run --label "rune:ready"       # Xem trước hàng đợi
/rune:arc-issues --resume                             # Tiếp tục batch
/rune:arc-issues --cleanup-labels                     # Xóa label mồ côi
/rune:cancel-arc-issues                               # Dừng batch

# Bộ nhớ agent
/rune:echoes init                                     # Khởi tạo
/rune:echoes show                                     # Xem trạng thái
/rune:echoes remember "Quy ước hoặc quyết định"      # Bộ nhớ vĩnh viễn
/rune:echoes prune                                    # Lưu trữ entry cũ
/rune:echoes reset                                    # Xóa tất cả (có backup)
```
