#!/usr/bin/env node
/**
 * Claude Stop Hook - 策略目标检查脚本
 *
 * 功能：
 * 1. 读取 .claude/tmp/strategy-loop/strategy-goals.json 获取目标策略和指标要求
 * 2. 检查 logs/backtest/{target_strategy}/ 下最新回测结果
 * 3. 读取 metrics.json 验证指标是否全部达标（复合条件）
 * 4. 达标：打开报告，保存状态，显示成功信息
 * 5. 未达标：返回优化 prompt
 */

const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

// 配置文件路径
const CONFIG_PATH = path.join(__dirname, '..', 'tmp', 'strategy-loop', 'strategy-goals.json');
const STATE_PATH = path.join(__dirname, '..', 'tmp', 'strategy-loop', 'state.json');
const FLAG_PATH = path.join(__dirname, '..', 'tmp', 'strategy-loop', 'flag.json');
const BACKTEST_BASE_DIR = path.join(__dirname, '..', '..', 'logs', 'backtest');

/**
 * 从 stdin 读取 Claude hook 输入
 */
function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => {
      data += chunk;
    });
    process.stdin.on('end', () => {
      try {
        const input = data ? JSON.parse(data) : {};
        resolve(input);
      } catch (e) {
        resolve({});
      }
    });
    process.stdin.on('error', (err) => {
      reject(err);
    });
  });
}

/**
 * 读取策略目标配置
 */
function loadConfig() {
  try {
    if (!fs.existsSync(CONFIG_PATH)) {
      return null;
    }
    const config = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
    return config;
  } catch (error) {
    console.error('读取配置文件失败:', error.message);
    return null;
  }
}

/**
 * 读取状态文件
 */
function loadState() {
  try {
    if (!fs.existsSync(STATE_PATH)) {
      return null;
    }
    return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
  } catch (error) {
    return null;
  }
}

/**
 * 保存状态文件
 */
function saveState(state) {
  try {
    const stateDir = path.dirname(STATE_PATH);
    if (!fs.existsSync(stateDir)) {
      fs.mkdirSync(stateDir, { recursive: true });
    }
    fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2));
  } catch (error) {
    console.error('保存状态失败:', error.message);
  }
}

/**
 * 加载计数器
 */
function loadCounter() {
  try {
    if (!fs.existsSync(FLAG_PATH)) {
      return { iteration: 0 };
    }
    return JSON.parse(fs.readFileSync(FLAG_PATH, 'utf8'));
  } catch (error) {
    return { iteration: 0 };
  }
}

/**
 * 保存计数器
 */
function saveCounter(counter) {
  try {
    const flagDir = path.dirname(FLAG_PATH);
    if (!fs.existsSync(flagDir)) {
      fs.mkdirSync(flagDir, { recursive: true });
    }
    fs.writeFileSync(FLAG_PATH, JSON.stringify(counter, null, 2));
  } catch (error) {
    console.error('保存计数器失败:', error.message);
  }
}

/**
 * 递增计数器
 */
function incrementCounter() {
  const counter = loadCounter();
  counter.iteration = (counter.iteration || 0) + 1;
  saveCounter(counter);
  return counter.iteration;
}

/**
 * 获取指定策略的最新回测目录
 */
function getLatestBacktest(strategyName) {
  try {
    const strategyDir = path.join(BACKTEST_BASE_DIR, strategyName);

    if (!fs.existsSync(strategyDir)) {
      return null;
    }

    const entries = fs.readdirSync(strategyDir, { withFileTypes: true });
    const backtestDirs = entries
      .filter(entry => entry.isDirectory())
      .map(entry => entry.name)
      .sort((a, b) => b.localeCompare(a)); // 按时间倒序

    if (backtestDirs.length === 0) {
      return null;
    }

    const latestDir = path.join(strategyDir, backtestDirs[0]);
    return {
      runId: backtestDirs[0],
      path: latestDir
    };
  } catch (error) {
    console.error('获取最新回测失败:', error.message);
    return null;
  }
}

/**
 * 读取回测指标
 */
function loadMetrics(backtestPath) {
  try {
    const metricsPath = path.join(backtestPath, 'metrics.json');
    if (!fs.existsSync(metricsPath)) {
      return null;
    }
    return JSON.parse(fs.readFileSync(metricsPath, 'utf8'));
  } catch (error) {
    console.error('读取指标文件失败:', error.message);
    return null;
  }
}

/**
 * 检查指标是否达标（复合条件）
 * @returns {Object} { achieved: boolean, failures: Array, results: Object }
 */
function checkGoals(metrics, goals) {
  const failures = [];
  const results = {};
  let allAchieved = true;

  for (const [metricName, thresholds] of Object.entries(goals)) {
    const actualValue = metrics[metricName];

    if (actualValue === undefined) {
      failures.push(`指标 '${metricName}' 在回测结果中未找到`);
      allAchieved = false;
      continue;
    }

    results[metricName] = actualValue;
    let achieved = true;
    const reasons = [];

    // 检查最小值
    if (thresholds.min !== null && thresholds.min !== undefined) {
      if (actualValue < thresholds.min) {
        achieved = false;
        reasons.push(`当前值 ${(actualValue * 100).toFixed(2)}% 低于目标最小值 ${(thresholds.min * 100).toFixed(2)}%`);
      }
    }

    // 检查最大值
    if (thresholds.max !== null && thresholds.max !== undefined) {
      // 对于负值指标（如回撤），值越大（越接近0）越好
      const isNegativeMetric = thresholds.max < 0;
      if (isNegativeMetric) {
        // 负值指标：实际值应该 >= 目标值（如 -6.69% >= -10% 表示回撤更小，更好）
        if (actualValue < thresholds.max) {
          achieved = false;
          reasons.push(`当前值 ${(actualValue * 100).toFixed(2)}% 比目标最大值 ${(thresholds.max * 100).toFixed(2)}% 更差（回撤更大）`);
        }
      } else {
        // 正值指标：正常比较
        if (actualValue > thresholds.max) {
          achieved = false;
          reasons.push(`当前值 ${(actualValue * 100).toFixed(2)}% 高于目标最大值 ${(thresholds.max * 100).toFixed(2)}%`);
        }
      }
    }

    if (!achieved) {
      allAchieved = false;
      failures.push(`[${metricName}] ${reasons.join(', ')}`);
    }
  }

  return {
    achieved: allAchieved,
    failures,
    results
  };
}

/**
 * 打开报告文件
 */
function openReport(backtestPath) {
  const reportPath = path.join(backtestPath, 'performance_report.html');

  if (!fs.existsSync(reportPath)) {
    return;
  }

  // Windows 下使用 start 命令
  const command = process.platform === 'win32'
    ? `start "" "${reportPath}"`
    : `open "${reportPath}"`;

  exec(command, (error) => {
    if (error) {
      console.error('打开报告失败:', error.message);
    }
  });
}

/**
 * 格式化结果信息
 */
function formatResults(results) {
  return Object.entries(results)
    .map(([key, value]) => {
      let formatted;
      if (key.includes('return') || key.includes('drawdown') || key.includes('rate')) {
        formatted = `${(value * 100).toFixed(2)}%`;
      } else {
        formatted = value.toFixed(4);
      }
      return `  - ${key}: ${formatted}`;
    })
    .join('\n');
}

/**
 * 格式化成功信息
 * @param {Object} results - 指标结果
 * @returns {string} 格式化后的成功信息
 */
function formatSuccessOutput(results) {
  return `策略已达标！\n\n最终指标：\n${formatResults(results)}`;
}

/**
 * 格式化失败信息
 * @param {Array} failures - 未达标的指标列表
 * @param {Object} results - 当前指标值
 * @returns {string} 格式化后的失败信息
 */
function formatFailOutput(failures, results) {
  const failureText = failures.map(f => `  - ${f}`).join('\n');
  const resultsText = formatResults(results);

  return `当前策略未达到目标：\n${failureText}\n\n当前指标：\n${resultsText}\n\n请分析并优化策略：\n1. 查看回测结果和交易日志\n2. 识别问题根源\n3. 调整策略参数或逻辑\n4. 重新运行回测验证改进效果`;
}

/**
 * 统一退出输出
 * @param {Object} params - 输出参数
 * @param {string} params.decision - "approve" 或 "block"
 * @param {string} params.reason - 原因（日志用）
 * @param {string} params.systemMessage - 用户可见消息
 */
function outputPrompt({ decision, reason, systemMessage }) {
  const blockResponse = {
    decision: decision || "approve",
    reason: reason,
    systemMessage: systemMessage,
  };
  process.stdout.write(JSON.stringify(blockResponse));
  process.exit(0);
}

/**
 * 主函数
 */
async function main() {
  // 1. 删除旧的状态文件，确保每次检查都基于最新回测结果
  try {
    if (fs.existsSync(STATE_PATH)) {
      fs.unlinkSync(STATE_PATH);
    }
  } catch (error) {
    console.error('删除旧状态文件失败:', error.message);
  }

  // 2. 加载配置
  const config = loadConfig();
  if (!config) {
    return outputPrompt({
      decision: "approve",
      reason: "未找到策略目标配置文件",
      systemMessage: "未找到策略目标配置文件，跳过目标检查。"
    });
  }

  const { target_strategy, goals, open_report_on_success, prompt_on_fail, prompt_on_success, max_iterations } = config;

  // 3. 加载并递增计数器
  const currentIteration = incrementCounter();
  const maxIter = max_iterations || 10;

  // 4. 检查是否超过最大迭代次数
  if (currentIteration > maxIter) {
    return outputPrompt({
      decision: "approve",
      reason: `已达到最大迭代次数限制 (${maxIter} 次)`,
      systemMessage: `策略优化已达到最大迭代次数限制 (${maxIter} 次)。请查看当前回测结果，或调整策略目标后重新开始。`
    });
  }

  if (!target_strategy || !goals) {
    return outputPrompt({
      decision: "approve",
      reason: "配置文件中缺少 target_strategy 或 goals",
      systemMessage: "策略目标配置不完整，跳过目标检查。"
    });
  }

  // 5. 获取最新回测
  const latestBacktest = getLatestBacktest(target_strategy);
  if (!latestBacktest) {
    return outputPrompt({
      decision: "approve",
      reason: `未找到策略 '${target_strategy}' 的回测记录`,
      systemMessage: `未找到策略 '${target_strategy}' 的回测记录，请先运行回测。`
    });
  }

  // 6. 读取指标
  const metrics = loadMetrics(latestBacktest.path);
  if (!metrics) {
    return outputPrompt({
      decision: "approve",
      reason: "无法读取回测指标",
      systemMessage: "无法读取回测指标文件，请检查回测是否完整执行。"
    });
  }

  // 7. 检查目标（复合条件）
  const checkResult = checkGoals(metrics, goals);

  // 8. 保存状态
  saveState({
    last_check: new Date().toISOString(),
    strategy: target_strategy,
    run_id: latestBacktest.runId,
    achieved: checkResult.achieved,
    metrics: checkResult.results,
    iteration: currentIteration
  });

  // 9. 根据结果处理
  if (checkResult.achieved) {
    // 达标：显示成功信息并打开报告
    const successMessage = prompt_on_success
      ? prompt_on_success
          .replace('{strategy}', target_strategy)
          .replace('{results}', formatResults(checkResult.results))
      : formatSuccessOutput(checkResult.results);

    if (open_report_on_success) {
      openReport(latestBacktest.path);
    }

    // 达标，允许停止
    return outputPrompt({
      decision: "approve",
      reason: `策略 '${target_strategy}' 已达标`,
      systemMessage: successMessage
    });
  } else {
    // 未达标：输出 JSON block 格式阻止 Claude 停止
    const failMessage = prompt_on_fail
      ? prompt_on_fail
          .replace('{strategy}', target_strategy)
          .replace('{failures}', checkResult.failures.join('\n'))
          .replace('{results}', formatResults(checkResult.results))
          .replace('{iteration}', String(currentIteration))
          .replace('{max_iterations}', String(maxIter))
      : formatFailOutput(checkResult.failures, checkResult.results) + `\n\n当前迭代次数: ${currentIteration}/${maxIter}`;

    // 阻止 Claude 停止，返回优化提示
    return outputPrompt({
      decision: "block",
      reason: failMessage.replace(/\n/g, " "),
      systemMessage: failMessage
    });
  }
}

// 执行主函数
main().catch(err => {
  console.error('Hook 执行出错:', err);
  process.exit(1);
});
