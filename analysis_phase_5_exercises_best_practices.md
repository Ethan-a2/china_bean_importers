# 5. 练习题目与最佳实践（china_bean_importers）

## 5.1 入门路径与练习题目

### 入门路径（建议顺序）

1. **跑通最小闭环**
   - 阅读 README 的“使用方法”。
   - 复制 `config.example.py -> config.py`（放到你的账本项目目录）。
   - 修改 `import_config.py` 只启用一个最熟悉的渠道（例如 `wechat`）。
   - 准备 1 个小的账单样例文件，运行 ingest 并确认生成 entries。

2. **理解 Importer 生命周期**
   - 重点阅读：`china_bean_importers/importer.py`：
     - `identify()` 做了什么
     - `extract()` 如何遍历行并生成交易

3. **掌握配置映射**
   - 阅读：`china_bean_importers/common.py` + `config.example.py`。
   - 学会：
     - `unknown_*_account` 的意义
     - `detail_mappings` 的规则与优先级

4. **扩展到 PDF/信用卡账单**
   - 在 `config.py` 加入 `pdf_passwords`（如果需要）。
   - 启用一个 PDF importer，理解 `open_pdf` 与 `PdfImporter/PdfTableImporter`。

5. **读懂/改造一个具体 importer 子包**
   - 选一个你常用渠道的 importer 文件，理解其：
     - match_keywords
     - parse_metadata
     - extract_rows / generate_tx 的实现

### 练习题目（从易到难）

1. **配置练习：Unknown 归类优化**
   - 目标：将 Unknown 交易比例从 X% 降到 Y%。
   - 做法：
     - 统计哪些 narration/payee 最常出现
     - 为其添加 `detail_mappings`

2. **规则练习：实现“AND”匹配**
   - 在 `detail_mappings` 中写 2 条规则：
     - 一条 `match_logic="OR"`
     - 一条 `match_logic="AND"`
   - 用同一笔交易分别验证命中情况。

3. **冲突练习：priority 与层级账户冲突**
   - 配置两条会同时命中的规则：
     - `Expenses:Food`
     - `Expenses:Food:Delivery`
   - 设置相同 priority，观察系统如何选择更“深”的账户；
   - 再调整 priority，观察选择行为变化。

4. **代码练习：写一个最小 CsvImporter 子类**
   - 创建一个新的 importer（例如 `china_bean_importers/demo_csv/`）：
     - `match_keywords` 匹配自定义表头
     - `extract_rows()` 解析 csv（可偷懒：用 `self.content` 直接 split 逗号）
     - `generate_tx()` 生成最基础的 Transaction（日期、金额、两个 posting）

5. **代码练习：优化 PdfImporter 的列定位算法（挑战）**
   - 当前是对 `column_offsets` 线性扫描，复杂度 `O(W*C)`。
   - 目标：改成二分查找列位置，将其降到 `O(W*logC)`。
   - 要求：保持输出 rows 与现有逻辑一致（写一个基准对比脚本）。

6. **集成练习：做一个“后处理器”**
   - 模仿 `dedup.find_wechat_family()`，实现一个简单规则：
     - 对 narration 包含“手续费”的交易追加 tag `fee`
     - 对金额为正且 narration 包含“退款”追加 tag `refund`

## 5.2 最佳实践

### A) 开发与扩展

- **优先复用基类**：
  - CSV 类账单优先继承 `CsvImporter`/`CsvOrXlsxImporter`
  - PDF 优先选择 `PdfTableImporter`（如果表格结构稳定），否则用 `PdfImporter`（更可控）
- **identify 轻量化**：
  - 避免在 identify 阶段做“全量解析”；能用少量行/页判断就不要读全文件。
  - 对 xlsx 特别重要：避免 `read_excel()` 作为“仅识别”动作。
- **字段缺失的容错**：
  - 金额/日期字段可能为空或格式变化；使用 `my_assert/my_warn`（或统一异常策略）清晰提示行号与原始行内容。
- **输出一致性**：
  - 对同类交易统一 narration/payee 规范，便于用户后续编写规则。
  - 元数据 key 命名保持稳定，避免频繁变更影响用户账本。

### B) 配置与使用

- **把配置放在用户账本仓库，不要放进 importer 仓库**：
  - 避免泄露个人账单信息、账号、PDF 密码。
- **逐步细化 detail_mappings**：
  - 先从高频商户开始；
  - 关键词尽量具体，减少误命中。
  - 使用 priority 解决冲突，避免多个规则“抢同一笔交易”。
- **卡号映射最小化**：
  - 只记录末四位（项目本身也是这样设计的），减少敏感信息暴露。

### C) 维护与质量

- **测试数据脱敏策略**：
  - 用合成样例或彻底脱敏后的账单片段；
  - 尽量保留格式特征（表头、列顺序、日期/金额格式）。
- **回归测试维度**：
  - 交易条数
  - 金额方向（支出/收入）
  - 日期解析
  - 账户映射命中率（Unknown 比例）
- **性能基线**：
  - 针对 PDF/XLSX 建议保留一组基准文件并记录耗时；
  - 任何修改 PDF 解析逻辑都跑一遍基准。
