# Kunar 对话训练成果整合（2026-10-27）

## 2026-10-29 录制入口更新

公开入口配置：先在影刀打开并保存用户指定专用应用，执行`python examples/attendance_video.py setup --app-id <实际ID>`；随后用本次文件执行`launch --source <文件> --session <新目录>`，用`status --session <同目录>`查询。安装专用Skill：`python tools/install_kunar_skill.py --skill yingdao-attendance-demo`。入口使用`.local/video-demo`绑定，不照搬历史应用编号；不读取历史默认输入文件。测试自行生成虚构工作簿。

当前 `attendance_video.py` 使用 `attendance_video_native_recipe.json` 的17个原生步骤，以列表收集后批量写入替代行号递增和列表索引表达式。保留下面的12步资料作为历史来源，不能与新配方的运行证据混用。新配方还处理筛选无匹配记录时只输出表头，限定学时为有限数值。Skill为本机Kunar已启用的yingdao-attendance-demo。

本轮17步改造和预演由Codex协助。新Kunar对话能否一次完成，以其本次工具记录、影刀run_id与实际结果为准。

## 已吸收的内容

- 将 Kunar 的 `process8_fixed_recipe.py:get_recipe_steps()` 提取为仓库内 `examples/attendance_video_recipe.json`。保留真实指令、参数类型、表达式包装、变量输出槽位和 12 步顺序；不复制其交互式 main、不依赖外部快照。
- 指定区域排除表头；按实际输入行数调整末行。`float(loop_item[3]) > 0` 只用于已检查的有限数值输入，不能对任意空白或文本盲目转换。
- 写入坐标使用 `row_num/column_name`；内容为二维列表表达式；初始化和递增均写回同一个变量。
- 先确认应用再创建流程。flow_id 只在应用内有效，不照搬 process8，不在偶然打开的“定时点击”中创建。
- 修改请求使用 inputs/outputs；回读使用 fields.<字段>.value。构建后逐项核对配方，再运行。
- 运行成功和业务验收分开。独立读取指定结果文件，核对全部记录、顺序、学时合计和输入哈希；不能用预期结果补写输出。
- 不将历史 `used_range` 快照混入成功案例；不将更换文件路径说成智能匹配新输入；不因 HTTP 400/404 推断流程丢失。

## 与成熟工具合并方式

使用原有 studio_bridge、builder 的真实 schema 校验、应用/账号绑定、写入前快照和构建 journal。演示独立配置位于 `.local/video-demo`，不覆盖原先考勤汇总应用的绑定。

新增 `examples/attendance_video.py` 提供 prepare/build/run/check。输入只有一个工作表、四列固定表头，不含公式或空数据行；筛选规则固定为缺勤学时大于零。计划准备与独立核验在外部 Python 完成，读取、判断、循环、写入和保存由影刀原生可视化指令完成。

## 证据与表达边界

历史 process8 在指导修复后通过，运行 ID 为 `20261026T051235068Z_6e692b5f8`。配方来源是 2026-10-26T10:18:13.194293+00:00 的真实回读快照。新入口是否通过实测，以各 session.json 为准，不能继承历史案例的运行结论。

录屏可表述为“通过与 Kunar 对话总结经验，形成 Skill；现在用它调用已验证方案，自动构建并运行考勤筛选流程”。这不是完整三周学院汇总，也不是任意 Excel 任务的独立生成能力。原有完整汇总样例继续保留，避免交稿前改动其业务规则。
