# 3. 性能瓶颈分析与调试（china_bean_importers）

## 3.1 潜在性能瓶颈

> 假设用户一次性导入大量账单文件（多页 PDF、长时间跨度 CSV、多个渠道同时启用），性能问题最可能集中在“文件解析/抽取”与“匹配规则遍历”两类。

### 瓶颈 1：PDF 解析与表格抽取（最可能）

涉及代码：`china_bean_importers/importer.py` 中 `PdfImporter.identify()`、`PdfImporter.extract_rows()`、`PdfTableImporter.identify()/extract_rows()`。

理由：

- `fitz.open()` + `page.get_text("words")`/`page.get_text("text")` 需要对每页进行文本布局解析，通常是 CPU 密集型。
- `PdfImporter.identify()` 为了关键字匹配会构建：
  - `self.content`（words 列表）
  - `self.full_content`（text 拼接的大字符串）
  对多页 PDF 可能会复制大量文本，增加内存峰值和 GC 压力。
- `PdfImporter.extract_rows()` 对每个 word 都需要确定所在列：
  - 当前实现是对 `column_offsets` 线性扫描：若列数为 `C`、word 数为 `W`，开销 `O(W*C)`。
- `PdfTableImporter` 依赖 `page.find_tables()`；表格检测通常比纯文本抽取更耗时，且对页数/复杂布局敏感。

### 瓶颈 2：XLSX 解析（可选依赖但成本高）

涉及代码：`CsvOrXlsxImporter.identify()`。

理由：

- `pandas.read_excel()` 会把整个表加载成 DataFrame，再转 csv 字符串；对于大文件非常耗内存与时间。
- 该逻辑发生在 `identify()` 阶段：意味着“仅为了识别文件”就可能付出完整解析成本（尤其当 match_keywords 失败时，成本浪费更明显）。

### 瓶颈 3：规则匹配（detail mappings）在大规模数据下放大

涉及代码：`china_bean_importers/common.py`：`match_destination_and_metadata()` + `BillDetailMapping.match()`。

理由：

- 每条交易都遍历 `detail_mappings`；当用户配置大量规则（M 很大）且账单行数 N 很大，整体成本约 `O(N*M*K)`。
- 关键词匹配使用 `substring in text`，在长字符串上反复扫描也会放大。

### 瓶颈 4：CSV 读取与预处理（低概率，但在超大文件时可能）

涉及代码：`CsvImporter.identify()` / `CsvOrXlsxImporter.identify()`。

理由：

- 识别阶段会 `f.read()` 读入整个文件并 `splitlines()`；大文件会导致一次性内存占用高。
- 同时对每行 `.strip()` 并过滤空行，属于额外线性扫描。

### 瓶颈 5：dedup 后处理（场景化）

涉及代码：`china_bean_importers/dedup.py`。

理由：

- `find_wechat_family()` 需要多次遍历 `new_entries_list` 并构造两个 defaultdict；整体是 `O(E)` 级别（E 为 entries 数量）。
- 一般不会是主瓶颈，但在“多渠道 + 大量 entries”时会叠加。

## 3.2 调试与排查步骤

### 0) 明确问题与度量指标

- 先回答：慢在哪里？
  - **identify 阶段慢**（扫描文件识别 importer）
  - **extract 阶段慢**（生成 entries）
  - **postprocess/dedup 慢**
- 统一指标：
  - 总耗时
  - 单文件耗时（按文件类型/页数/大小分组）
  - 内存峰值（特别是 PDF/XLSX）

### 1) 从用户侧最小化复现

1. 选取 1~3 个“最慢”的文件（通常是多页 PDF 或大 xlsx）。
2. 只启用一个 importer（避免多个 identify 反复解析同一文件）。
3. 确认性能问题可复现。

### 2) 建立剖析入口（profiling harness）

建议做法（不改代码也可）：

- 用 `python -m cProfile -o prof.out ...` 对运行 ingest 的入口脚本做 profile。
- 如果 ingest 流程复杂，不易定位到单 importer：
  - 写一个小脚本直接调用某个 Importer 的 `identify()` + `extract()` 对单文件进行基准。

> 目标：确定热点函数是 `fitz`、`find_tables()`、`read_excel()`、还是 `match_destination_and_metadata()`。

### 3) 快速判别：identify 成本是否过高

检查点：

- `CsvImporter.identify()` 会读取整个文件：
  - 若只是为了识别，考虑改为“读取前 N 行”就足够（仅作为建议，不在本阶段改代码）。
- `CsvOrXlsxImporter.identify()` 对 xlsx 直接 `read_excel()`：
  - 如果慢在 identify，则应优先优化：
    - 只读少量行/列（例如 `nrows`）
    - 或先用文件名/扩展名/简单特征过滤

### 4) 针对 PDF：分层定位

1. 计时 `fitz.open()` + 解密：
   - 如果慢，可能是加密 PDF 的尝试密码较多或 PDF 本身很大。
2. 计时每页：
   - `page.get_text("words")`
   - `page.get_text("text")`
   - `page.find_tables()`
3. 计时 `extract_rows()`：
   - 对 `PdfImporter` 重点看列定位循环 `for i, off in enumerate(self.column_offsets)` 是否占比高。

### 5) 针对规则匹配：缩小 M

1. 临时将 `detail_mappings` 缩到 0，观察整体耗时变化。
2. 若明显改善：
   - 统计 mapping 数量 M 与每笔交易的匹配次数。
   - 检查是否存在大量“非常通用”的关键词（命中率高导致 metadata/tags 合并开销上升）。
3. 优化方向（建议）：
   - 预索引：将关键词 -> mappings 建立倒排索引，减少每条交易遍历的 M。
   - 引入正则/分组优先级，减少无效匹配。

### 6) 内存与大对象排查

- PDF：`self.full_content` 大字符串拼接、`self.content` words 列表。
- XLSX：DataFrame + csv 字符串。

建议：

- 用 `tracemalloc` 看大对象来源；
- 或在 Linux 下用 `/usr/bin/time -v`（最大驻留集）对比不同文件。

### 7) 回归验证

- 选定基准数据集（几类典型文件 + 大文件）。
- 每次优化后，验证：
  - 识别正确性（identify 不误判）
  - 交易数量一致（或差异可解释）
  - 账务语义不退化（账户/金额/日期）。

## 3.3 常见“看起来像性能问题”的非性能原因（排查提醒）

- 多个 importer 同时启用、且对同一文件都做了重解析（identify 阶段每个 importer 都尝试读全文/解析 PDF）。
- 某个 importer 的 `match_keywords` 过于宽泛，导致大量文件都被尝试 parse_metadata。
- 依赖缺失导致反复 ImportError/Warning（日志量大也会拖慢）。
