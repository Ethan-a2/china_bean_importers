# 4. 文档建议（china_bean_importers）

## 4.1 Wiki 文档建议（面向使用者 + 贡献者）

### A) 快速开始（Quick Start）

- 安装方式：PyPI / editable install
- 最小可运行示例：
  - `cp config.example.py config.py`
  - `import_config.py` 示例
  - 执行 ingest 的命令示例（若项目 README 未给出，可在 wiki 补充常见 beancount ingest 用法）
- 常见文件组织建议：账单目录结构、命名规范、如何批量导入。

### B) 配置指南（Config Reference）

- `config` 的完整 schema：
  - `importers` 下每个子 importer 的字段说明
  - `card_accounts` 结构与示例
  - `pdf_passwords`
  - `unknown_expense_account/unknown_income_account`
  - `detail_mappings`（BDM）详解：
    - narration_keywords/payee_keywords
    - `SAME_AS_NARRATION`
    - priority 与 match_logic
    - metadata/tags 合并规则与冲突行为
- 给出“从 0 到 1”的配置模板：
  - 最少字段即可跑通
  - 如何逐步细化（分类、标签、元数据）

### C) 支持的数据源与导出方法（已在 README 中，但可结构化增强）

- 每个 importer 一页：
  - 支持的文件类型、编码、导出入口路径
  - 样例文件片段（表头/关键行）
  - 已知限制（例如：支付宝网页端不推荐）
  - 典型配置片段

### D) 解析与匹配工作原理（How it works）

- ingest 生命周期：identify -> extract
- 不同基类的差异：CsvImporter / PdfImporter / PdfTableImporter
- 账户匹配优先级：
  1. 卡号末四位映射
  2. detail_mappings
  3. unknown fallback
- 去重/后处理逻辑（目前的 wechat family-card）说明：
  - 触发条件
  - 对 entries 的修改（tags、narration、DUPLICATE_META）

### E) 兼容性与依赖（Compatibility）

- Python 版本范围
- beancount 版本限制（<3）与原因
- 可选依赖：pandas/openpyxl 的用途与安装方式
- PDF 解密注意事项与安全提示（不要把密码提交到仓库；推荐先去除 PDF 密码）

### F) Troubleshooting（用户排障手册）

- 常见错误：
  - identify 不生效（关键词不匹配/编码问题/文件扩展名）
  - PDF 解密失败
  - 金额方向/退款处理不符合预期
  - 账户映射缺失导致 Unknown 过多
- 日志/调试：
  - 如何打开调试输出
  - 如何最小化复现

### G) Contributing（贡献指南）

- 新增 importer 的模板与步骤：
  - 选择基类
  - 需要实现哪些方法
  - 测试样例放哪、如何脱敏
- 代码风格与项目约定
- PR checklist

## 4.2 详细设计文档建议（面向维护者）

### 建议的关键章节

1. **背景与目标**
   - 为什么要做这些 importer
   - 与 beancount ingest 的关系与约束

2. **总体架构**
   - 分层、模块边界、数据流（可复用你在阶段 1 的 Mermaid 图）

3. **核心抽象与扩展点**
   - BaseImporter 模板方法
   - Csv/Pdf/Xlsx 的识别策略
   - 输出 Transaction 的规范（字段、meta、tags 的约定）

4. **配置系统设计**
   - config schema 与向后兼容策略
   - detail_mappings 的冲突处理与优先级规则
   - 黑/白名单设计（card_narration_*）

5. **文件解析策略**
   - CSV：编码、表头定位、空行处理
   - PDF：
     - `words` 抽取与列定位
     - `find_tables` 的适用边界
     - 解密策略与失败处理
   - EML/HTML（如果使用 BeautifulSoup）：
     - 解析流程、容错、字段缺失

6. **去重与后处理**
   - 现有 wechat family-card 逻辑
   - 未来扩展为 pipeline 的建议（可插拔后处理器）

7. **性能与可观测性**
   - identify 阶段避免全量解析的原则
   - profiling 方法
   - 大文件/多页 PDF 的内存策略

8. **测试策略**
   - 单元测试 vs 集成测试（ingest 端到端）
   - 测试数据脱敏与生成
   - 回归指标：交易数、金额、日期、账户

9. **兼容性与发布**
   - beancount 版本限制的处理策略
   - PyPI 发布流程（Flit）

10. **风险清单**
   - 银行/平台随时变更格式
   - PDF 表格抽取不稳定
   - 用户配置错误导致错账

## 4.3 建议新增的“文档即资产”文件

- `docs/` 目录结构建议：
  - `docs/quickstart.md`
  - `docs/config-reference.md`
  - `docs/importers/<name>.md`
  - `docs/how-it-works.md`
  - `docs/troubleshooting.md`
  - `docs/contributing.md`
- `CHANGELOG.md`：记录每个版本新增/修复的 importer 与破坏性变更。
- `SECURITY.md`：提醒不要提交账单/密码/个人信息，说明如何脱敏。
