# 开发、恢复与排错

## 结构

scripts/settings.py 负责配置和安装发现；studio_bridge.py 负责 schema 检查、账号/应用约束和证据；builder.py 负责可恢复构建；yingdao.py 提供统一命令入口；agent_entry.py 让 Skill 使用仓库虚拟环境。业务例子独立放在 examples。

CLI 使用当前安装的 shadowbot.shell-cli.exe。本地 Studio 连接通过临时目录中的 shadowbot.cli.*.port 找到回环地址 /api/v1/mcp。实际 tools/list 和本机 visual-blocks 目录是指令依据。此接口属于实验依赖，产品升级可能变化；不是跨版本稳定性承诺。不会解密 .pybx，也不随项目分发影刀程序和知识库。

## 计划格式

```json
{
  "flow_id": "创建后返回的实际ID",
  "blocks": [{
    "prototype": "programing.variable",
    "label": "输出示例",
    "inputs": {"value_type": "str", "value": {"expression": "'Hello'"}},
    "output": "message"
  }],
  "out_parameters": [{"name": "message", "type": "any"}]
}
```

`output` 简写只适用于有一个真实输出槽的指令。多输出用 `outputs` 映射真实槽名。输入值可能是字面值、`{"variable":"变量名"}` 或 `{"expression":"表达式"}`，必须以当前指令资料为准。先执行 preflight；它检查 prototype 和输入字段名，不能证明表达式、元素定位或业务逻辑正确。当前 builder 是顺序插入器；任意嵌套控制结构尚未作为发布样例验证。

读取实际工具 schema：`yingdao.py tools --names flow.fill_blocks,app.copy_flow`。通用调用：`yingdao.py call --tool 工具名 --args @参数.json`，修改加 `--write`。适配器只开放代码中 READ/WRITE 集合的工具，不开放发布和删除应用。

## 修改和恢复

- 绑定包含本地账号指纹、应用 ID 和允许操作的 flow_id。换账号/应用停止写入；绑定不是权限系统，也不是不可信代理沙箱。
- 创建流程自动加入允许列表。复制原流程后修改副本更易恢复；allow-flow 只应对明确要修改的流程使用。
- 每次 flow 修改前记录块和参数；这不是完整应用备份，不能据此承诺自动回滚，元素库和其他全局资产不在快照范围。
- build 默认要求空流程。journal 记录计划哈希、账号/应用、已插入块和已填写数量。
- `build --plan 原计划.json --flow-id 原ID --resume journal.json --write` 可恢复已确认的填写步骤。计划必须不变；不要同时在 Studio 手工编辑。
- `insert_uncertain` 表示插入请求是否生效不确定，自动恢复被拒绝。读取实际块和 evidence，人工确认后在副本中修复；不盲目重复插入。
- `complete` journal 再次恢复只报告已完成，不重插。已有块 ID 列表不符时停止。当前检测不能识别所有外部参数变更，所以只支持串行、单编辑者。
- app.save 保存整个应用，流程级允许列表不能隔离同一应用其他未保存改动。使用专用应用；当前没有跨进程编辑锁。

运行：`run --flow-id ... --write --wait 20`。未结束时 `wait --run-id ... --wait 20`，或 `result --run-id ...`。每次等待最多 45 秒。连接超时后先查询原任务/日志，绝不能因为没收到响应就重跑可能有副作用的流程。日志、快照和 journal 默认在配置旁 state 目录，不进入发布包。

## 常见问题

| 情况 | 处理 |
| --- | --- |
| 找不到 CLI | configure 指定真实 exe，确认不是开始菜单快捷方式 |
| 多份指令目录 | 指向当前运行版本，不能直接选编号最大的文件夹 |
| 端口文件为零/多个 | 确认影刀运行且仅一套目标会话；排查残留，不批量删除临时目录 |
| 当前无应用 | 在 Studio 手动打开专用应用，再 current / bind |
| 账号改变/应用不同 | 选择正确应用，再显式重新绑定，不复用旧账号 ID |
| 新插入块提示必填项 | 插入后尚未填参数是预期状态；检查填充结果，不能重复插入 |
| failed_count/fill_errors | 视为失败，检查实际内容和构建断点 |
| 流程成功但输出错误 | 以输出校验为准，检查输入、规则、对应步骤；不宣称完成 |

## 提交修改

运行 unittest；对新的影刀行为添加虚构样例和现场输出核对。不要只用 mock 证明平台兼容。提交问题时说明影刀版本、操作类型、预期/实际结果和脱敏错误；不贴完整账号配置、模型密钥或实际业务文件。
