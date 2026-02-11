# 詞彙驗證邏輯完整指南

## 📋 目錄
1. [驗證規則總覽](#驗證規則總覽)
2. [Replace Words 驗證](#replace-words-驗證)
3. [Special Words 驗證](#special-words-驗證)
4. [批次處理邏輯](#批次處理邏輯)
5. [前端警告顯示](#前端警告顯示)
6. [常見場景處理](#常見場景處理)

---

## 驗證規則總覽

### 核心設計原則

1. **語義正規化**: Replace Word 的 Target 應該成為 Special Word
2. **防止邏輯衝突**: Source 不能同時是 Special Word
3. **防止鏈式替換**: 不允許 A→B→C 的替換鏈
4. **冪等性**: 重複批准不會出錯，不會重複新增

### Conflicts vs Warnings

| 類型 | 視覺 | 是否阻止批准 | 用途 |
|------|------|-------------|------|
| **Conflict** | 🔴 紅色 | ✅ 是 | 邏輯錯誤，必須修正 |
| **Warning** | 🟡 黃色 | ❌ 否 | 提醒注意，可以批准 |

---

## Replace Words 驗證

### 驗證規則（3 個 Conflicts + 2 個 Warnings）

#### ❌ Conflicts（阻止批准）

| 規則 | 檢查內容 | 範例 | 原因 |
|------|---------|------|------|
| **same_word** | Source = Target | 草 → 草 | 無意義的替換 |
| **source_in_special_words** | Source 是 Special Word | hololive* → Hololive | 邏輯衝突：保留 vs 替換 |
| **source_in_target_words** | Source 是其他 Replace 的 Target | 艸† → wwww | 防止鏈式替換 |

#### ⚠️ Warnings（不阻止批准）

| 規則 | 檢查內容 | 範例 | 說明 |
|------|---------|------|------|
| **source_already_exists** | Source 已存在但 Target 不同 | 草→艸 改為 草→wwww | 更新操作 |
| **duplicate_pending** | Pending 中重複 | 重複的 草→艸 | 提醒重複 |

**符號**: `*` = 在 special_words, `†` = 是其他 replace 的 target

### 批准後行為

```python
existing = db.query(ReplaceWord).filter(
    ReplaceWord.source_word == pending.source_word
).first()

if existing:
    existing.target_word = pending.target_word  # 更新
    existing.updated_at = func.now()
else:
    new_word = ReplaceWord(...)  # 新增
    db.add(new_word)
```

**行為**:
- 新詞彙: 新增記錄
- 已存在: 更新 target_word
- 相同記錄: 冪等（無動作）

---

## Special Words 驗證

### 驗證規則（1 個 Conflict + 2 個 Warnings）

#### ❌ Conflicts（阻止批准）

| 規則 | 檢查內容 | 範例 | 原因 |
|------|---------|------|------|
| **word_in_source_words** | 詞彙是 Replace Word 的 Source | 草† → 不能是 Special | 邏輯衝突：要替換 vs 要保留 |

**符號**: `†` = 是 replace_word 的 source

#### ⚠️ Warnings（不阻止批准）

| 規則 | 檢查內容 | 範例 | 說明 |
|------|---------|------|------|
| **word_already_exists** | 詞彙已存在於 special_words | hololive（重複） | 冪等設計，跳過不重複新增 |
| **duplicate_pending** | Pending 中重複 | 重複的 hololive | 提醒重複 |

### 重要改動

#### ✅ 已移除的規則（之前是 Conflict）
- ~~**word_in_target_words**~~: Target 可以是 Special Word（語義正規化設計）

#### ✅ 已移除的警告
- ~~**target_in_special_words**~~ (Replace Words): Target 是 Special Word 是正常設計，不需警告

### 批准後行為

```python
existing = db.query(SpecialWord).filter(
    SpecialWord.word == pending.word
).first()

if not existing:
    new_word = SpecialWord(word=pending.word)
    db.add(new_word)  # 只在不存在時新增
# 已存在則跳過（冪等）
```

**行為**:
- 新詞彙: 新增記錄
- 已存在: 跳過不重複新增

---

## 批次處理邏輯

### 核心邏輯

```python
validations = batch_validate_xxx(db, ids)

approved = 0
failed = 0
errors = []

for word_id in ids:
    validation = validations.get(word_id, {})
    
    # 關鍵：只檢查 valid，不檢查 warnings
    if not validation.get('valid', False):
        failed += 1
        errors.append(...)
        continue  # 跳過，繼續下一個
    
    # 批准邏輯
    pending.status = 'approved'
    # ... 更新/新增 ...
    approved += 1

db.commit()  # 一次性提交全部

return {
    "success": True,
    "approved": approved,
    "failed": failed,
    "errors": errors
}
```

### 失敗行為

#### ✅ 驗證失敗（不影響其他）

```
批次: [ID 1, ID 2, ID 3]
- ID 1: valid = True → ✅ 批准
- ID 2: valid = False → ❌ continue（跳過）
- ID 3: valid = True → ✅ 批准

結果:
✅ approved = 2
❌ failed = 1
✅ success = true
```

#### ❌ 數據庫異常（全部失敗）

```
批次: [ID 1, ID 2, ID 3]
- ID 1: ✅ 處理完成
- ID 2: 💥 IntegrityError
- except → db.rollback()

結果:
❌ 全部回滾
💥 HTTP 500
```

### 失敗類型對比

| 失敗類型 | 行為 | 其他記錄 |
|---------|------|---------|
| **驗證失敗** | continue 跳過 | ✅ 不影響 |
| **找不到 Pending** | continue 跳過 | ✅ 不影響 |
| **數據庫異常** | rollback() | ❌ 全部撤銷 |

**結論**: Warnings 不影響批次批准，只有 Conflicts 會阻止單個詞彙的批准

---

## 前端警告顯示

### ValidationResultModal 組件

```javascript
const ValidationResultModal = ({ 
    isOpen, 
    isValid, 
    conflicts,
    warnings = [],  // 新增
    onClose 
}) => {
    // 顯示邏輯
    if (isValid) {
        // ✅ 驗證通過
        if (warnings.length > 0) {
            // 顯示黃色警告區塊
        }
    } else {
        // ❌ 驗證失敗
        // 顯示紅色衝突區塊
    }
}
```

### 已更新的組件

所有使用 ValidationResultModal 的組件都已更新：
1. ✅ SpecialWordsReview.jsx
2. ✅ AddSpecialWordForm.jsx
3. ✅ ReplaceWordsReview.jsx
4. ✅ AddReplaceWordForm.jsx

### UI 顯示

```
✅ 驗證通過
未發現衝突，此詞彙可以安全批准。

⚠️ 但有以下提示：
┌─────────────────────────────────┐
│ ⚠️ word_already_exists:         │
│    word 'hololive' 已存在於     │
│    special_words 中             │
└─────────────────────────────────┘
ℹ️ 這些警告不會阻止批准，但請確認是否符合預期
```

---

## 常見場景處理

### 場景 1: Replace Target 成為 Special Word（正常設計）✅

```
設置: 
- Replace: 草 → 艸, 糙 → 艸, 操 → 艸
- Special: 艸

驗證結果:
✅ Replace Words: valid = True, warnings = []
✅ Special Words: valid = True, warnings = []

目的: 詞頻正規化
結果: 詞頻統計「艸」= 所有變體總和
```

### 場景 2: 詞彙已存在（冪等設計）✅

#### Special Words
```
現有: hololive 在 special_words
檢查: hololive

驗證結果:
✅ valid = True
⚠️ warnings = [word_already_exists]

批准後:
- 不重複新增
- Pending 標記為 approved
```

#### Replace Words
```
現有: 草 → 艸
檢查: 草 → wwww

驗證結果:
✅ valid = True
⚠️ warnings = [source_already_exists]

批准後:
- 更新 target: 艸 → wwww
- Pending 標記為 approved
```

### 場景 3: Source 是 Special Word（衝突）❌

```
設置:
- Special: hololive
- Replace: hololive → Hololive

驗證結果:
❌ valid = False
❌ conflicts = [source_in_special_words]

原因: 邏輯衝突
- Special Word = 要保留
- Replace Source = 要替換
```

### 場景 4: 鏈式替換（衝突）❌

```
現有: A → B
新增: B → C

驗證結果:
❌ valid = False
❌ conflicts = [source_in_target_words]

原因: 防止 A→B→C 的複雜鏈條

正確做法:
- A → C
- B → C（直接設置）
```

### 場景 5: 批次中有失敗項（部分成功）✅

```
批次: [
    ID 1: 草 → 艸 (valid = True)
    ID 2: 草 → 草 (valid = False, same_word)
    ID 3: 糙 → 艸 (valid = True)
]

結果:
✅ approved = 2 (ID 1, 3)
❌ failed = 1 (ID 2)
⚠️ errors = [{id: 2, error: "same_word"}]

行為: ID 2 被跳過，不影響 ID 1 和 ID 3
```

### 場景 6: Word Discovery 批次處理（大幅改善）✅

```
Word Discovery 生成:
- 100 個 pending_replace_words
- 50 個 target 自動加入 pending_special_words

批次批准 Special Words:

修改前:
- 50 個 target 會失敗（word_in_target_words）
- 需手動處理

修改後:
- 全部可以成功批准 ✅
- 批次效率大幅提升
```

---

## 快速參考表

### Replace Words 驗證

| 情況 | Source | Target | 結果 | 前端 |
|------|--------|--------|------|------|
| 相同詞 | 草 | 草 | ❌ Conflict | 🔴 |
| Source 是 Special | hololive* | Hololive | ❌ Conflict | 🔴 |
| Source 是其他 Target | 艸† | wwww | ❌ Conflict | 🔴 |
| Source 已存在 | 草‡ | wwww | ⚠️ Warning | 🟡 |
| Target 是 Special | 草 | 艸* | ✅ 無警告 | ✅ |
| Pending 重複 | 草 | 艸 | ⚠️ Warning | 🟡 |
| 正常 | 草 | 艸 | ✅ 通過 | ✅ |

### Special Words 驗證

| 情況 | 詞彙 | 結果 | 前端 |
|------|------|------|------|
| 是 Replace Source | 草† | ❌ Conflict | 🔴 |
| 是 Replace Target | 艸‡ | ✅ 無警告 | ✅ |
| 已存在 | hololive* | ⚠️ Warning | 🟡 |
| Pending 重複 | hololive | ⚠️ Warning | 🟡 |
| 正常 | hololive | ✅ 通過 | ✅ |

**符號**: 
- `*` = 在 special_words
- `†` = 是 replace_word 的 source  
- `‡` = 是 replace_word 的 target

---

## 測試驗證

### 後端測試（15/15 通過）✅

```bash
===== 15 passed, 10 warnings in 3.16s =====
```

**測試覆蓋**:
- ✅ Replace Word 所有驗證規則
- ✅ Special Word 所有驗證規則
- ✅ 批次驗證功能
- ✅ Target 可以是 Special Word
- ✅ 已存在詞彙為 warning

### 前端組件（4/4 更新）✅

所有使用 ValidationResultModal 的組件已更新支持 warnings 顯示。

---

## 總結

### 核心改動

1. ✅ **移除「Target 不能是 Special Word」衝突** - 允許語義正規化
2. ✅ **移除「Target 是 Special Word」警告** - 這是正常設計
3. ✅ **保持「已存在」為 Warning** - 維持冪等性
4. ✅ **前端支持 Warnings 顯示** - 黃色警告區塊

### 影響

| 影響範圍 | 結果 |
|---------|------|
| **Special Words 批次成功率** | ✅ 大幅提升 |
| **Replace Words 警告** | ✅ 減少不必要警告 |
| **批次處理邏輯** | ✅ 無破壞性影響 |
| **前端顯示** | ✅ 新增警告支持 |
| **冪等性** | ✅ 保持正常 |
| **測試覆蓋** | ✅ 100% 通過 |

### 部署狀態

**健康度**: ✅ **非常健康**

**風險評估**: 🟢 **零風險**

**建議**: 可立即部署 ✅

---

## 修改檔案清單

### 後端（2 個）
- `app/services/validation.py`
- `tests/test_validation.py`

### 前端（5 個）
- `ValidationResultModal.jsx`
- `SpecialWordsReview.jsx`
- `AddSpecialWordForm.jsx`
- `AddReplaceWordForm.jsx`
- `ReplaceWordsReview.jsx`

**總計**: 7 個檔案修改 ✅
