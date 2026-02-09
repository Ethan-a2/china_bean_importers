# 2. 项目目标、演进与关键特性（china_bean_importers）

## 2.1 项目目标与演进

### 项目目标

- **短期目标（当前形态）**
  - 为中国用户常见资金渠道提供 **Beancount ingest Importer**，将账单文件（CSV/PDF/EML/等）转换为可导入的 Beancount 交易记录。
  - 通过配置完成：
    - 账户映射（资产/负债账户、卡号末四位自动匹配等）
    - 分类/对手/描述到目标账户、标签、元数据的映射（`detail_mappings`）
    - 处理 PDF 加密、格式差异等现实问题。

- **长期目标（合理推断）**
  - 覆盖更多渠道与更多导出格式（不同银行不同版本的 PDF/HTML/Excel）。
  - 降低用户手工配置成本（更智能的分类、默认规则、交互式配置生成）。
  - 提升导入质量（更强去重、更高准确率、更多元数据保留、可追溯性）。
  - 可能的“兼容性升级”：README 提到 **不支持 Beancount 3+**，长期可能需要适配新版本 ingest API。

### 演进路径与版本迭代策略（建议式推断）

- **以“渠道/格式”为主线的迭代**
  1. 新增 importer（新渠道）
  2. 同渠道新增格式支持（csv/txt/pdf/eml/xlsx）
  3. 识别/解析鲁棒性增强（字段缺失、换行、编码、表格提取误差）
  4. 输出语义增强（更多 metadata/tags、外币支持、手续费/退款/分期等特殊交易）

- **以“框架能力”为主线的迭代**
  - 对 `importer.py` 的基类抽象加强（减少每个渠道重复代码）。
  - 对通用映射/规则引擎（`BillDetailMapping`）扩展更丰富的匹配方式（正则、权重、多字段）。
  - 将 `dedup.py` 的特定逻辑沉淀为可复用的后处理 pipeline。

## 2.2 核心组件、关键特性与核心功能

### 核心组件

- **Importer 框架基类（`china_bean_importers/importer.py`）**
  - `BaseImporter`：统一抽取流程（模板方法）。
  - `CsvImporter` / `CsvOrXlsxImporter`：处理文本表格或 xlsx。
  - `PdfImporter` / `PdfTableImporter`：处理 PDF 的文本抽取/表格识别。

- **匹配与工具库（`china_bean_importers/common.py`）**
  - `BillDetailMapping`：配置驱动的“描述/对手 -> 账户/标签/元数据”规则。
  - `match_destination_and_metadata`：规则合并与冲突处理。
  - `open_pdf`：PDF 解密与打开。
  - `find_account_by_card_number`：卡号末四位到资产/负债账户的映射。

- **后处理去重/修正（`china_bean_importers/dedup.py`）**
  - 针对微信“亲属卡”/“财付通”重复记录做标记或重写标签/叙述。

- **用户侧集成（`import_config.py` + `config.py`）**
  - `CONFIG=[Importer(config), ...]` 注册启用的 importer。
  - `config` 提供所有 importer 的行为参数。

### 关键特性与核心功能

- **多来源账单导入**：微信、支付宝、各家银行卡/信用卡、校园卡、HSBC HK 等（见 README 列表）。
- **多格式支持**：
  - CSV/TXT（归入文本表格）
  - PDF（文本抽取 + 表格提取）
  - EML（常用于信用卡邮件账单；具体解析在各 importer 子包中）
  - XLSX（可选）
- **配置驱动的账户/分类映射**：
  - `category_mapping`（示例：交通出行 -> Expenses:Travel）
  - `detail_mappings`（更细粒度匹配：京东/饿了么等）
- **卡号末四位自动匹配**：
  - 通过 `card_accounts` 将末四位映射到 beancount 账户路径。
- **加密 PDF 自动尝试解密**：
  - `open_pdf` 逐个尝试 `pdf_passwords`。
- **跨渠道重复交易处理（部分场景）**：
  - `dedup.find_wechat_family` 针对亲属卡与财付通/微信支付之间的重复与语义修正。

### 核心算法与复杂度分析

#### A) `BaseImporter.extract()`（行到交易的模板）

- 逻辑：
  - `extract_rows()` 得到行列表
  - 对每行 `generate_tx(row, i, file)`
  - `filter(None, ...)` 过滤掉无法生成交易的行
- 复杂度：
  - 设行数为 `N`，单行生成交易平均成本为 `G`：
    - 时间：`O(N * G)`
    - 空间：输出 entries `O(N)`（以及临时列表/生成器开销）

#### B) `match_destination_and_metadata(config, desc, payee)`（规则合并）

- 逻辑：遍历 `detail_mappings` 列表，对每个 mapping 执行关键词匹配，然后按优先级/账户层级合并结果。
- 复杂度：
  - 设 mapping 数量为 `M`，每个 mapping 的关键词数量平均为 `K`：
    - 最坏时间：`O(M * K)`（包含 narration 与 payee 两组匹配；常数略大）
    - 空间：合并 metadata/tags 的集合，`O(T + Meta)`（T 为标签数量）

#### C) `PdfImporter.extract_rows()`（基于 words 的列定位与行拼接）

- 逻辑：遍历 `page.get_text("words")` 得到的 word 列表，基于 `column_offsets` 推断列，基于 `(y0, last_col)` 判断拼接/换行/新行。
- 复杂度：
  - 设总 word 数为 `W`，列数为 `C`：
    - 当前实现对每个 word 会遍历列偏移以确定列：`O(W * C)`
    - 空间：累积 entries/parts，`O(W)`（近似与输出字符量相关）

> 备注：这一段在性能章节会进一步讨论优化空间（例如二分查找列偏移、预计算等）。

## 2.3 关键用例

### 用例 1：用户将微信账单导入 Beancount

1. 用户在微信导出账单 CSV（README 描述了导出路径）。
2. 将 CSV 放入 ingest 扫描目录。
3. 在用户项目中：
   - 复制 `config.example.py -> config.py` 并填写账户映射、unknown account、detail mappings 等。
   - 在 `import_config.py` 中注册 `wechat.Importer(config)`。
4. 运行 beancount ingest：
   - Importer `identify()` 识别 CSV
   - `extract()` 抽取并生成交易
5. 用户在 Beancount 中审阅生成的交易并入账。

### 用例 2：导入带密码的银行卡流水 PDF

1. 用户从银行 App 导出 PDF，记录解密密码。
2. 将密码加入 `config["pdf_passwords"]`。
3. 启用相应 bank importer。
4. 运行 ingest：
   - `open_pdf` 逐个尝试密码
   - 解密成功后解析表格并生成交易。

### 用例 3：为“京东/外卖”等商户自动分类

1. 用户在 `detail_mappings` 中加入规则，如：
   - narration 包含“京东” -> `Expenses:JD`
   - payee 包含“饿了么” -> `Expenses:Food:Delivery`
2. Importer 生成交易时调用 `match_destination_and_metadata`：
   - 设置对端账户、附加 tags、写入 metadata（如 `platform`）。
3. 用户在账本中获得自动分类后的交易，减少手工改账。
