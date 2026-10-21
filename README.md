# Yingdao Agent Bridge（0.2.0 预览版）

让已有 AI 助手通过本机影刀 Studio 的真实接口读取流程、构建自动化、运行并核对结果。面向会配置 Python / AI 工具、偶尔使用影刀的用户；支持 Kunar Skill 接入，也可由其他具备本机命令执行能力的助手使用。

这是一个独立社区项目。需要自行安装、登录影刀并具备相应功能权限；不包含影刀、模型或 Kunar 授权，不保证免费，也不绕过产品权限。

## 当前能做什么

- 查询当前应用、流程、指令参数及可用工具，依据本机指令资料构建空白流程。
- 绑定当前账号和应用，显式限定可修改/运行的流程；换账号后旧绑定失效。
- 创建/复制流程、保存、运行、查询同一 run_id 的结果，记录修改前状态和构建断点。
- 提供固定订单文本 PDF → Excel、Excel 名单筛选提取、按列名填写模板的完整样例。
- 提供13个学院、三周考勤与晚点名汇总样例：同堂课折算、缺报状态、模板填写、学院排序和重复导入检查。
- 通过现场工具 schema 检查参数，未知指令拒绝构建。语义正确仍需运行和结果验证。

目前是可供开发者试用的版本。已验证环境、未覆盖范围见 [兼容性与验证](docs/VALIDATION.md)。不承诺任意任务一句话完成。

## 安装与首次运行（Windows）

先安装 Python（本机验证为 3.14；其他版本尚未实测）、影刀，并登录、打开一个专用测试应用。下载/解压本项目后在仓库目录运行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\yingdao.py doctor
```

首次 doctor 的 binding 检查失败是正常的。CLI 尝试从常见安装位置寻找；不在这些位置时显式配置。多个版本并存时必须选择正在运行版本的指令目录：

```powershell
.\.venv\Scripts\python.exe scripts\yingdao.py configure --cli-path "D:\Program Files\ShadowBot\shadowbot.shell-cli.exe" --catalog-dir "D:\Program Files\ShadowBot\shadowbot-版本号\Resources\Copilot\knowledge\visual-blocks"
.\.venv\Scripts\python.exe scripts\yingdao.py current
.\.venv\Scripts\python.exe scripts\yingdao.py bind --app-id "上一步显示且你要操作的app_id"
.\.venv\Scripts\python.exe scripts\yingdao.py doctor
```

上面的 D 盘路径是示例，必须换成自己机器的实际位置。默认配置位于 `.local/config.json`，也可用 `YINGDAO_BRIDGE_CONFIG` 指定配置文件。换账号后重新选择应用、绑定，旧流程权限不会沿用。此工具不会替你切换或保存正在编辑的其他应用。

建立第一个流程：

```powershell
.\.venv\Scripts\python.exe scripts\yingdao.py create-flow --name "HelloBridge" --write
.\.venv\Scripts\python.exe scripts\yingdao.py build --plan examples\hello-plan.json --flow-id "刚返回的flow_id" --write
.\.venv\Scripts\python.exe scripts\yingdao.py run --flow-id "刚返回的flow_id" --write
```

期望结果：`run_succeeded: true`，输出 `bridge_message: Hello from Yingdao Agent Bridge`。若仍在运行，查询返回的同一 run_id，不能重复启动。JSON 中 `ok` 仅表示命令检查通过；判断业务完成还要检查运行状态和输出。

## 在 Kunar 中使用

先按上面完成安装、自检和绑定，再运行：

```powershell
.\.venv\Scripts\python.exe tools\install_kunar_skill.py
```

默认安装到当前用户 Kunar 的 default workspace；其他 workspace 可通过 `--skills-dir "实际skills目录"` 指定。安装器不会覆盖已有同名 Skill，也不会改旧的 `yingdao-studio-assistant`。

Kunar 2.1.0 会把新发现的技能默认设为未启用。运行 `kunar skills test yingdao-agent-bridge` 验证，再运行 `kunar skills config`，勾选 yingdao-agent-bridge 并保存（或在界面的技能管理中启用）；用 `kunar skills info yingdao-agent-bridge` 确认 Enabled 为 yes。kunar 未加入 PATH 时用其 exe 完整路径。

在 Kunar 新对话中明确要求“使用 yingdao-agent-bridge 技能，先检查影刀连接，再按我的要求生成并验证流程”。Skill 需要助手具有本机读文件/运行命令能力。未发现技能时重新加载技能或重启 Kunar；不要随意重置整个 Kunar 环境。安装的是指向本仓库虚拟环境与配置的本地入口，安装后不要移动仓库；移动后重新配置入口。

## 示例、开发与发布

- [三个可复现的数据处理例子](docs/EXAMPLES.md)
- **[三周考勤汇总完整样例](docs/ATTENDANCE.md)**：78份演示表格、运行命令和预期结果。
- [Gitee发布步骤](docs/GITEE.md)
- [接口、计划格式、中断恢复和常见问题](docs/DEVELOPMENT.md)
- [测试记录和当前限制](docs/VALIDATION.md)
- [参考资料及第三方说明](THIRD_PARTY.md)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\package_release.py
```

发布打包只收录明确列出的源码、文档及已替换个人/机构信息的演示表格，不包含 `.local`、虚拟环境、真实业务输入输出、账号绑定、运行日志或影刀内置知识库。日志和快照可能包含业务数据，反馈问题时自行脱敏，只提供复现步骤、版本和必要的错误片段。

本项目自有代码采用 [MIT](LICENSE)。欢迎用虚构数据提交可复现的问题和修改；添加能力时同时提供输入边界与结果验证，不要将个人路径、账号或业务材料提交到仓库。
