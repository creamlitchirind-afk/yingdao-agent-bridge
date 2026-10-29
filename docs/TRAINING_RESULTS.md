# 操作训练结果

## 2026-10-29 新增验证

- 网页终版165条原生指令：元素定位与关联行、查询/翻页条件等待、循环/判断/break、末页、文件/窗口/剪贴板/键盘前台写入。Kunar单条需求60.05秒完成，3页24条、导出21条、209.79元；逐行核验及窗口打开/最大化检查通过。见[SHOP_ORDERS.md](SHOP_ORDERS.md)。
- 四列筛选17步：有限数值、二维列表收集后写入、空结果只保留表头，见[KUNAR_DEMO_LESSONS.md](KUNAR_DEMO_LESSONS.md)。
- 按周汇总：版本、占用提示、重复导入、中断恢复、图形结果逐人交叉核验见[ATTENDANCE_INBOX.md](ATTENDANCE_INBOX.md)，完整汇总仍含代码引擎。

以下2026-10-23三例及当时“尚待实测”是历史，不混用版本或推断任意同类操作全覆盖。方法与边界见[SKILL_TRAINING.md](SKILL_TRAINING.md)。

日期：2026-10-23。影刀实跑版本6.3.39。使用独立应用，保留原始运行响应和构建日志于本地.local/operation-training-20261023（不随仓库公开）。

|案例|原生指令预检|影刀运行|实际业务核验|run_id|
|---|---|---|---|---|
|logic|通过|通过，静态/运行错误均0|`{"values": [0.5, 2, 3, 1], "total": 6.5}`|`20261023T055038951Z_d131ccae8`|
|file_wait_regex|通过|通过，静态/运行错误均0|`{"ready": true, "matches": [["A102", "3"]]}`|`20261023T055125441Z_520b36d9d`|
|web_local|通过|通过，静态/运行错误均0|`["A", "C"]`|`20261023T055159680Z_bf07ac775`|

## 实际范围与失败修复

- logic：原生forin内嵌if筛选，变量累积；不代表多分支、任意嵌套、break/continue均已验证。
- file_wait_regex：原生文本文件读写、等待已存在文件、固定短等待；正则为programing.variable中的Python re表达式。未验证异步出现和超时分支。
- web_local：Chrome打开本机HTTP页面，通过浏览器JavaScript修改输入值、触发按钮及读取结果，然后仅关闭所建网页。未验证影刀原生元素库捕获、关联元素、鼠标键盘或图像。
- 首次在原测试应用中运行，logic与file_wait_regex输出正确，但run_succeeded=false；diagnostics.snapshot显示四条错误属于原process3。未修改该业务流程，改在独立应用完成验收。
- 首次网页使用file://因浏览器local file access权限失败；改为127.0.0.1临时HTTP服务后通过，服务已关闭。
- 仓库16项单元测试通过；Skill格式检查通过。这两项不替代上述影刀现场验收。

## 尚待实测

二分支/多分支、循环控制和其他等待模式、原生网页元素操作、Excel行列复制插删、鼠标键盘图像、Word与剪贴板需要独立案例。已有PDF/表格示例边界见EXAMPLES.md，不扩大为所有格式支持。
