# 网页订单到可见表格

## 安装与配置

先完成README的虚拟环境、依赖、CLI及指令目录配置，在影刀打开并保存专用应用，运行`scripts/yingdao.py current`取得实际app_id。然后执行：

```powershell
.\.venv\Scripts\python.exe examples\shop_orders.py setup --app-id "实际app_id"
.\.venv\Scripts\python.exe tools\install_kunar_skill.py --skill yingdao-shop-orders
.\.venv\Scripts\python.exe examples\shop_orders.py launch --product "短袖T恤" --pages all --session "D:\RPA演示\订单报表_本次"
.\.venv\Scripts\python.exe examples\shop_orders.py status --wait 8 --session "D:\RPA演示\订单报表_本次"
```

D盘路径是示例，需要替换。只安装需要的Skill，并按README在Kunar启用。每个新任务使用全新目录，同一任务只查询同一目录。配置及配方缓存位于`.local/shop-demo`，可用`YINGDAO_SHOP_CONFIG`指定配置路径。切换账号/应用后重新setup，使用新会话。

没有当前应用的有效缓存时从空流程构建，完整核验成功后才缓存，以供下次复制、改写本次参数并重新采集。不需要开发者的历史流程。可配置入口和打包检查是本次发布整理，不能据此声称第二台电脑已现场运行通过。

## 实现与现场验证

2026-10-29，影刀6.3.39，Kunar默认智能体。该示例面向 https://shop.yingdao.com/list/table-list ，当前默认采集查询结果全部页面，以下一页不可用为终点；用户明确限制前N页时可传数字N。支持商品名称精确匹配、仅保留“完成”状态、按订单编号去重且保留行序，导出订单编号/商品名称/金额/日期/状态，金额是数值。

`examples/shop_orders_plan.py` 当前编排165条原生指令；`examples/shop_orders.py` 调用影刀开发接口、配置参数、保存运行并只读核验原生采集证据与Excel。早期107/119条版本的验证记录保留在下文。辅助程序仍是本机工程依赖。

当前表格方案：影刀复制无业务值的空白样式模板，重命名为含时间与短标识的新报表，用WPS打开并最大化，原生剪贴板和快捷键前台写入、Ctrl+S保存，不关闭窗口。空白资产位于examples/assets/shop-report-empty.xlsx，只有列宽/格式，不能用历史Excel替代。网页与表格操作均在影刀中完成，无代码流程、自编Python表达式或JavaScript采集。前台填表期间用户不要切窗口或使用键鼠。

当前最终Kunar单轮复测：process33，20261029T111507092Z_2ae421a7e，任务60.05秒，3页24条采集、21条导出、209.79元。运行后独立核验通过，实际WPS窗口仍打开且最大化。该数字是本次数据，不是固定答案。每次文件名唯一，保留上次打开的报表也不会同名冲突；全部页面模式额外要求末页证据一致，1000页为异常保护上限。

录制体验修正版：119条原生指令；以实际网页标题获取对应Chrome窗口，原生最大化并激活到前台；增加启动、窗口、查询、页面就绪等阶段日志。配方process22原生运行20261029T100343330Z_a80382c81通过，窗口最大化已用只读Windows窗口状态复核。原版107条及其运行记录保留作历史证据。

固定命令入口为 `examples/shop_orders.cmd`，它锁定仓库虚拟环境，可从Kunar的CMD命令工具调用。`status --wait 8`等待后返回精简摘要，不再依赖额外shell等待语法。失败和不确定任务拒绝重新launch，已验证的任务不会重新运行；内部worker只由启动器使用。CLI非JSON响应仅对身份及当前应用这两项只读查询限次重试，不重发写入请求。

Skill源文件为`skills/yingdao-shop-orders/SKILL.md`，安装入口从自己的`.local/runtime.json`读取本机仓库与Python。用户一次提交完整需求，内部可以多次工具调用。首次构建通常比缓存复用耗时更长。自然需求示例：“查询短袖T恤的全部页面，只保留完成订单，按订单编号去重，五列导出；浏览器最大化，全部采集后打开并最大化空白WPS，再前台写入保存，保持打开，核对条数金额和实际文件。”

## 实测

| 主体 | 商品/页数 | flow_id | 网页记录/导出 | 金额 |
|---|---|---|---|---|
| 维护者 | 短袖T恤/2 | process17 | 20/17 | 169.83 |
| 维护者换参数 | 篮球鞋/1 | process19 | 7/5 | 940 |
| Kunar一次业务需求 | 短袖T恤/2 | process20 | 20/17 | 169.83 |

Kunar run_id：20261029T074056965Z_666812c3c。单条需求任务164.52秒；影刀实际运行约6.9秒；静态和运行错误0。维护者在Kunar任务结束后只读复核107条流程及Excel每行、金额类型和顺序，通过。Kunar测试走命令行task入口，不是桌面GUI录屏。

实际输出数量和金额来自本次网页，不能固定为上述值。页面变化、无匹配结果、请求页数不足时会明确失败；未验证任意网站、任意规则、大量分页、无匹配结果成功空表或跨电脑安装。启动后只查询同一session；pending运行不能再run；失败保留原证据。后文两页矩阵是历史验证，不代表当前只能采集两页。

公开入口不包含固定账号或应用编号，setup只绑定用户明确指定且实际已打开的应用。所有新环境仍须验证CLI、浏览器扩展、WPS与工具参数。缓存的源结构被修改时拒绝复用；不自动把任意错误流程当作新配方。

公开验证摘要见[evidence/shop-orders-20261029.json](evidence/shop-orders-20261029.json)，培养过程与失败修正见[SKILL_TRAINING.md](SKILL_TRAINING.md)。原始日志保留本地，不发布账号绑定、机器路径或产品内置资料。14项订单必要测试：`python -m unittest discover -s tests -p test_shop_orders.py -v`。
