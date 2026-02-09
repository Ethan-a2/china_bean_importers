# 6. 模块问题排查（china_bean_importers）

## 6.1 模块出现问题的可能原因

> 这里的“模块”既可以指某个渠道 importer（如 `wechat`/`boc_credit_card`），也可以指框架模块（`importer.py`/`common.py`/`dedup.py`）。

### A) 文件识别失败（identify=False）

- **match_keywords 不匹配**
  - 平台更新了表头/关键字段文案（常见于 App 版本更新）。
  - 账单导出语言/地区不同导致关键字变化。
- **文件扩展名/命名不符合预期**
  - `CsvImporter.identify()` 检查 `"csv" in file.name`（不是严格 `.csv`），可能导致误判/漏判。
  - `PdfImporter.identify()` 使用 `"pdf" in file.name.lower()`。
- **编码问题**
  - CSV 可能不是 utf-8；若 importer 没有覆盖 `self.encoding`，会读失败或关键字匹配失败。
- **异常被吞掉**
  - identify 中 `except BaseException: return False` 会隐藏真实错误（例如解析逻辑抛异常）。

### B) 解析成功但生成交易不完整/错误

- **parse_metadata 解析日期/账户失败**
  - 例如 start/end 未设置，导致 file_date/file_name 等行为异常。
- **extract_rows 提取列错位**
  - CSV 列顺序变更/多了一列/缺了一列。
  - PDF：
    - `column_offsets` 不准确（布局变化/字体变化）。
    - words 的坐标系与预期不一致，导致列判断错。
    - `content_start_keyword/end_keyword` 不再出现，导致有效区域提取失败。
- **金额方向/退款处理错误**
  - 某些渠道“收入/支出”字段语义变化，导致正负号处理反。
- **外币/汇率/手续费/分期**
  - 货币字段缺失或映射不全（`currency_code_map`）。
  - 分期、利息、手续费等需要多 posting 才能表达，但实现未覆盖。

### C) 账户/分类映射不符合预期

- **card_accounts 配置缺失/重复**
  - `find_account_by_card_number` 找不到末四位 -> fallback 到 unknown。
  - 末四位重复时默认取第一个（README 也提示），可能命中错误账户。
- **detail_mappings 规则冲突**
  - 同优先级命中两个不相容账户，`my_warn` 会提示冲突。
  - 关键词过于宽泛导致误命中。
- **黑白名单配置导致过滤不一致**
  - `in_blacklist` 的白名单优先逻辑：白名单命中会直接不过滤。

### D) 去重/后处理导致“看起来错账”

- `dedup.find_wechat_family` 会修改 tags、narration，甚至替换 posting account（退款场景）。
- 若用户的账户命名不同（例如 Expenses:WeChat:FamilyCard 不一致），逻辑可能不触发或误触发。

### E) 环境与依赖问题

- 缺少 `pymupdf`（fitz）导致 PDF importer 不可用。
- 缺少 `pandas/openpyxl` 导致 xlsx 无法解析（会输出 WARNING）。
- beancount 版本不兼容（项目声明 `beancount < 3`）。

## 6.2 模块排查步骤（可操作清单）

### 第 1 步：明确问题类型与最小复现

- 问题属于：
  1) 识别失败（不触发 importer）
  2) 解析失败（抛异常/返回空 entries）
  3) 解析成功但内容不对（日期/金额/账户/标签）
  4) 性能问题（见阶段 3）
- 选一个最小输入文件复现（越小越好，同时能触发问题）。

### 第 2 步：定位是哪一个 importer/模块导致

- 在 `import_config.py` 中**只保留一个 importer**，逐个启用，确认问题归属。
- 若问题仅在多个 importer 同时启用时出现：
  - 优先怀疑：重复交易、dedup 后处理、黑名单/白名单过滤。

### 第 3 步：识别失败（identify）排查

1. **确认文件扩展名与内容**：
   - CSV/PDF 是否与 importer 预期一致。
2. **确认关键字是否存在**：
   - 直接在文件中搜索 match_keywords 对应的字符串（表头/固定字段）。
3. **检查编码**（CSV 常见）：
   - 尝试用不同 encoding 打开文件（utf-8 / gbk 等）。
   - 在 importer 中临时打印/断点确认读到的文本是否正常。
4. **抓真实异常**：
   - identify 里有 `except BaseException: return False`，调试时可临时改为打印异常或重新抛出（调试用，不建议长期保留）。

### 第 4 步：解析/抽取问题排查（extract_rows / generate_tx）

1. **验证 parse_metadata**：
   - start/end、file_account_name 是否设置正确。
2. **打印/抽样检查 rows**：
   - 先只看 `extract_rows()` 的输出是否列对齐、是否漏行。
3. **逐行验证 generate_tx**：
   - 针对一行，确认日期解析、金额解析、payee/narration 字段提取正确。
4. **检查 special cases**：
   - 退款（正负号反转）
   - 手续费/利息
   - 转账（对端账户可能应为内部账户）

### 第 5 步：账户/规则映射问题排查（common.py）

1. **卡号映射**：
   - 输入的 card_number 是否为末四位，且与 `card_accounts` 中一致。
2. **detail_mappings**：
   - 临时只保留一条规则，观察是否命中。
   - 调整 priority/关键词精确度，避免误命中。
3. **unknown fallback**：
   - 如果大量 Unknown：
     - 先确认是否本应由卡号映射命中
     - 再确认是否需要补充 detail mappings 或 category mapping。

### 第 6 步：dedup/后处理问题排查

- 暂时禁用 dedup（如果你的 ingest 流程调用了它），看交易是否恢复。
- 检查 dedup 中硬编码账户名是否与你的账户体系一致。

### 第 7 步：回归验证

- 固定一组样例文件：
  - 小 CSV
  - 单页 PDF
  - 多页 PDF
  - （可选）xlsx
- 每次修改 importer 后比对：
  - 条数
  - 总金额（收入/支出分别汇总）
  - 关键字段（日期、账户、币种）

## 6.3 建议补强的“可观测性”手段（长期）

- 为每个 importer 增加可选 debug 开关：
  - identify 失败原因（缺关键字/编码失败/异常堆栈）
  - parse_metadata 解析结果摘要
  - extract_rows 行数、字段缺失统计
- 给 `match_destination_and_metadata` 增加“命中解释”输出（命中了哪条 mapping）。
