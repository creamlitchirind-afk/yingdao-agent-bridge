# Yingdao Agent Bridge（0.3.0 预览版）

让已有 AI 助手通过本机影刀 Studio 的真实接口读取流程、构建自动化、运行并核对结果。面向会配置 Python / AI 工具、偶尔使用影刀的用户；支持 Kunar Skill 接入，也可由其他具备本机命令执行能力的助手使用。

这是一个独立社区项目。需要自行安装、登录影刀并具备相应功能权限；不包含影刀、模型或 Kunar 授权，不保证免费，也不绕过产品权限。

## 项目定位

这是一个**通用的影刀 RPA 桥接层**，目标是让任意具备本机命令执行能力的 AI 助手（Kunar、Claude、Cursor、Cherry Studio、自写 Python 脚本等）都能通过同一套 CLI 安全地：读取影刀流程、构建可视化流程、运行并核对结果。仓库里附带了几套已在本机验证过的示例，用来展示桥接层能完成的自动化类型，也作为回归测试用例。

## 通用能力

- 查询当前应用、流程、指令参数及可用工具，依据本机指令资料构建空白流程。
- 绑定当前账号和应用，显式限定可修改/运行的流程；换账号后旧绑定失效。
- 创建/复制流程、保存、运行、查询同一 run_id 的结果，记录修改前状态和构建断点。
- 通过现场工具 schema 检查参数，未知指令拒绝构建。语义正确仍需运行和结果验证。
- 提供本地断点与运行证据，支持中断后按原计划恢复。

## 仓库内置示例

- **[网页订单 → 可见Excel报表](docs/SHOP_ORDERS.md)**：165条原生指令，查询商品、等待页面更新、采集到末页、筛选去重；打开并最大化WPS后前台填入，保存并保持打开。已在Kunar中验证一次完整业务需求驱动构建、运行和核验。
- **[四列表格筛选](docs/KUNAR_DEMO_LESSONS.md)**：17条原生指令，按缺勤学时筛选，验证全部记录及顺序；无匹配时只输出表头。
- **[按周目录导入与版本留存](docs/ATTENDANCE_INBOX.md)**：识别待导入周、材料快照、逐人核验、不可变版本、已导入标记与中断后的归档恢复；完整汇总仍使用代码引擎。

- **[三周考勤汇总完整样例](docs/ATTENDANCE.md)**：78 份模拟 Excel、运行命令和预期结果，演示同堂课学时折算、缺报状态、模板填写、学院排序和重复导入检查。
- **[三个可复现的数据处理例子](docs/EXAMPLES.md)**：固定订单文本 PDF → Excel、Excel 名单筛选提取、按列名填写模板。
- **[操作训练与验证](docs/OPERATION_TRAINING.md)**：判断、循环、文件等待、正则和本地网页；明确区分计划预检、实际运行和业务验收。

这些示例使用模拟姓名和演示数据。真实业务请按用户给定的字段和规则重新构建流程。

目前是可供开发者试用的版本。已验证环境、未覆盖范围见 [兼容性与验证](docs/VALIDATION.md)。

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

默认安装到当前用户 Kunar 的 default workspace；其他 workspace 可通过 `--skills-dir "实际skills目录"` 指定。安装器默认不覆盖已有同名Skill。更新已安装入口时加`--update`，会先备份到工作区的`skill_backups`，再刷新该入口；不会修改Kunar的启用状态或其他助手。

也可以单独安装网页和考勤筛选入口：

```powershell
.\.venv\Scripts\python.exe tools\install_kunar_skill.py --skill yingdao-shop-orders
.\.venv\Scripts\python.exe tools\install_kunar_skill.py --skill yingdao-attendance-demo
```

在影刀打开并保存专用应用，运行`current`取得其实际app_id，再为要使用的演示执行首次绑定：

```powershell
.\.venv\Scripts\python.exe examples\shop_orders.py setup --app-id "实际app_id"
.\.venv\Scripts\python.exe examples\attendance_video.py setup --app-id "实际app_id"
```

两类示例使用各自本地配置，不带开发者账号或测试应用编号；只配置需要使用的示例即可。商城第一次会从空流程构建，核验通过后保存本地配方缓存供下次复制；不需要下载开发者的历史流程。

本机Kunar 2.1.0中新发现的技能默认未启用。运行`kunar skills test <安装的技能名>`验证，再运行`kunar skills config`勾选并保存，或在界面启用；用`kunar skills info <技能名>`确认Enabled为yes。kunar未加入PATH时用其exe完整路径。

在 Kunar 新对话中明确要求“使用 yingdao-agent-bridge 技能，先检查影刀连接，再按我的要求生成并验证流程”。Skill 需要助手具有本机读文件/运行命令能力。未发现技能时重新加载技能或重启 Kunar；不要随意重置整个 Kunar 环境。安装的是指向本仓库虚拟环境与配置的本地入口，安装后不要移动仓库；移动后重新配置入口。

## 文档与开发

- [Gitee发布步骤](docs/GITEE.md)
- [接口、计划格式、中断恢复和常见问题](docs/DEVELOPMENT.md)
- [测试记录和当前限制](docs/VALIDATION.md)
- [Skill经验来源、培养方法及失败修正](docs/SKILL_TRAINING.md)
- [参考资料及第三方说明](THIRD_PARTY.md)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools\package_release.py
```

发布打包只收录明确列出的源码、文档及已替换个人/机构信息的演示表格，不包含 `.local`、虚拟环境、真实业务输入输出、账号绑定、运行日志或影刀内置知识库。日志和快照可能包含业务数据，反馈问题时自行脱敏，只提供复现步骤、版本和必要的错误片段。

本项目自有代码采用 [MIT](LICENSE)。欢迎用虚构数据提交可复现的问题和修改；添加能力时同时提供输入边界与结果验证，不要将个人路径、账号或业务材料提交到仓库。
