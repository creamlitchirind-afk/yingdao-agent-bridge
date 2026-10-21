# 参考资料与许可范围

本项目在既有个人互通原型基础上整理；新增可移植配置、账号/应用绑定、统一命令入口、构建断点、输出校验和发布包装。没有训练或分发模型权重，也不是影刀官方项目。

| 参考 | 用途 | 记录 |
| --- | --- | --- |
| [影刀官方 CLI Skill](https://github.com/ying-dao/skills/blob/main/shadowbot-cli/SKILL.md) | CLI 发现、先查真实帮助的操作方法 | 2026-10-17 本地快照 aaebb7c44cf105d1914207f8b53bf70e03b12e25；该快照未找到 LICENSE，未将其全文纳入分发 |
| [yingdao-xbot-ai-agent](https://github.com/apexcheng/yingdao-xbot-ai-agent) | xbot-tools、应用生命周期、保存/同步/运行诊断的经验 | 快照 eacb4abc9456c8e4a5bf79756c9be13362a65fd7，MIT；参考方法与接口，不打包其源码或知识库 |
| [影刀 MCP Server](https://github.com/ying-dao/yingdao_mcp_server) | 理解调用既有应用与构建 Studio 流程的边界 | 快照 aca4b715314e699b7eef576439ca978fb928dc17，MIT；本适配器没有打包此 Server |
| 本机影刀 Studio tools/list 与 visual-blocks | 当前工具参数和指令定义 | 使用者自行安装版本提供，不复制进发布包 |
| 本机 Kunar CLI 与 Skill 目录 | 集成与发现方式 | 需使用者安装并配置 Kunar |

这些是开发时参考的版本记录，不代表上游当前版本或长期兼容承诺。上游链接和名称归原项目；本项目 MIT 仅覆盖本仓库自有代码/文档，不重新授权影刀、Kunar、其内置资料或用户数据。

Python 依赖由 pip 从各自项目安装，不捆绑入压缩包：jsonschema、pypdf；开发/生成样例另需 openpyxl、reportlab。请保留并遵守所安装依赖自身的许可。样例 PDF 使用 ReportLab 内置中文 CID 字体描述，不携带系统字体文件。样例数据完全虚构。

0.2版考勤运行新增openpyxl为安装依赖。考勤样例姓名由[Faker中文Provider](https://faker.readthedocs.io/en/latest/locales/zh_CN.html)生成；不捆绑Faker代码，运行固定样例不需安装Faker。表格结构参考用户提供的业务模板，公开版移除真实学校/学院/班级/邮箱，保留模拟姓名及演示数字。请勿将模拟材料当成真实考勤记录或官方模板。本项目许可证不代表对第三方软件、商标或原始材料的重新授权。
