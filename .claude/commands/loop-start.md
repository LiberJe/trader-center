# Loop Start

创建 `.claude/loop.flag` 文件来启用策略优化循环模式。

## 操作

请在项目根目录下执行：

```bash
echo "active" > .claude/loop.flag
```

或者使用 PowerShell:

```powershell
"active" | Out-File -FilePath .claude/loop.flag -Encoding utf8
```

## 说明

- 启动后，`on-stop.js` 会在 Claude 停止时检查目标是否达成
- 如果目标未达成，会阻止停止并提示继续优化
- 使用 `/loop-end` 命令结束循环模式
