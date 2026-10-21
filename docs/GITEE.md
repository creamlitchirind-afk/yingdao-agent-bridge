# Gitee发布说明

建议仓库名 `yingdao-agent-bridge`，项目名“影刀AI开发助手：Excel自动化与考勤汇总样例”。版本为0.2.0-preview，MIT。

本目录可直接作为Git仓库。提交源码、文档、测试与 `examples/attendance/data` 中的演示表格；不要提交 `.local`、`.venv`、`dist`、运行结果、账号绑定、原始业务材料或影刀知识库。

在Gitee创建空仓库后配置实际仓库地址，先检查远程内容再推送。若远程已有提交，应获取并保留其历史，不使用强制推送覆盖。

```powershell
git init -b main
git add README.md SKILL.md LICENSE THIRD_PARTY.md .gitignore config.example.json requirements.txt requirements-dev.txt scripts examples docs tests tools
git diff --cached --stat
git commit -m "Prepare Excel automation examples and attendance workflow"
git remote add origin https://gitee.com/你的用户名/yingdao-agent-bridge.git
git push -u origin main
```

仓库地址、公开性由维护者确定。登录或令牌在本机Git凭据管理器配置，不要把令牌写进URL、代码或聊天。源代码ZIP可作为Gitee附件；ZIP使用白名单打包并附SHA-256清单。

参考：[Gitee提交代码说明](https://gitee.com/help/articles/4122)、[Gitee帮助中心](https://help.gitee.com/)。
