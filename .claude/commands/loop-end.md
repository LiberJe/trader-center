# Loop End

删除 `.claude/loop.flag` 文件来结束策略优化循环模式。

## 操作

请在项目根目录下执行：

```bash
rm -f .claude/loop.flag
```

或者使用 PowerShell:

```powershell
Remove-Item -Path .claude/loop.flag -ErrorAction SilentlyContinue
```

## 说明

- 结束后，`on-stop.js` 会直接退出，不再检查目标
- 清理相关状态文件（可选）：
  - `.claude/tmp/strategy-loop/flag.json`
  - `.claude/tmp/strategy-loop/state.json`
