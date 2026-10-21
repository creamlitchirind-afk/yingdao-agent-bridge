# 可复现样例

以下命令在仓库目录运行。需要先完成 README 中的账号绑定，并安装开发依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe examples\make_samples.py
```

样例生成器在 `.local/samples` 生成虚构输入。重新执行会覆盖此目录内三个同名样例文件。

## 1. 文本 PDF → Excel

```powershell
.\.venv\Scripts\python.exe examples\pdf_orders.py inspect --pdf .local\samples\orders.pdf
.\.venv\Scripts\python.exe examples\pdf_orders.py create --pdf .local\samples\orders.pdf --write
```

每页一笔订单，字段按“订单编号、供应商、日期、金额”顺序逐行出现，冒号分隔。日期 YYYY-MM-DD，金额为非负数、最多两位小数。样例预期两行订单，金额 120.50 和 80.00。pypdf 预读得到独立期望值；影刀原生 PDF 指令提取文本，写 Excel 后回读，并比较磁盘文件。

不支持扫描件、加密 PDF、任意表格布局或字段别名。预读失败应停止，不能宣称已经支持 OCR。输出保留在 state/outputs/pdf-orders 下。

Kunar 可用自然语言：“使用 yingdao-agent-bridge，把 <orders.pdf绝对路径> 中的订单编号、供应商、日期、金额提取到新 Excel，生成影刀流程并核对实际文件。”

## 2. 名单提取

```powershell
.\.venv\Scripts\python.exe examples\sheet_records.py inspect --source .local\samples\registrations.xlsx
.\.venv\Scripts\python.exe examples\sheet_records.py extract --source .local\samples\registrations.xlsx --write
```

单个名为 Sheet 的工作表；首行包含报名编号、姓名、报名项目、联系方式、确认状态，列顺序不限。只取“已确认”，缺失必填字段记录为问题，完全相同编号保留一条，冲突编号停止。编号和联系方式必须存为文本，不猜测数字单元格已丢失的零。

五条虚构来源记录预期留下 A001、A004 两条，记录三条剔除原因；输出联系方式仍为 00010001、00010004。输入源不保存、不改写。

## 3. 按列名填写模板

```powershell
.\.venv\Scripts\python.exe examples\sheet_records.py fill --source .local\samples\registrations.xlsx --template .local\samples\template.xlsx --write
```

同样提取名单，填写模板副本。模板第 3 行含编号、姓名、项目、联系电话，允许列重排；第 4–13 行对应数据区必须为空，最多十条。只填匹配列，核对其他单元格、列宽及源文件哈希。样例的人工备注和审核人行必须保留。

此固定模块拒绝公式、多工作表、合并单元格。检查值和列宽不等于验证全部 Excel 特性；复杂样式、图表、宏不属于已验证范围。

Kunar 可说：“使用 yingdao-agent-bridge，从 <来源绝对路径> 提取已确认报名，忽略缺少必填字段和完全重复的记录，按列名填入 <模板绝对路径> 的副本；保留备注、源文件及联系方式前导零，生成并运行影刀流程后核对。”

## 中断

每次 create/extract/fill 都会新建流程。若中断，不要直接重复此命令。先检查该次输出目录的 verification.json、plan.json 和构建 journal；按 DEVELOPMENT 中的方法恢复或查询原 run_id。脚本若在等待窗口内未确认运行成功，会标记 incomplete，即使任务稍后完成，也须查原结果并补核对，不能当作已验证。
# 三周考勤业务样例

新增的13学院三周样例见 [ATTENDANCE.md](ATTENDANCE.md)，包含完整输入、空白总表、规则、影刀创建入口与预期结果。

