 #!/bin/bash

# MediaBot自动执行脚本 - 每90分钟运行一次
# 使用方法: ./run_autox.sh

echo "MediaBot自动执行脚本启动..."
echo "每90分钟执行一次: python autox.py --config config/tasks/job_auto_comment.json --account-id wingerbaby"
echo "按 Ctrl+C 停止脚本"
echo "=========================================="

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 执行计数器
counter=1

# 无限循环
while true; do
    echo ""
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始第 $counter 次执行..."
    
    # 执行python命令
    python autox.py --config config/tasks/job_auto_comment.json --account-id uMediaAgent
    python autox.py --config config/tasks/job_auto_comment.json --account-id wingerbaby
    python autox.py --config config/tasks/job_auto_comment.json --account-id uAgentDoctor
    # python autox.py --config config/tasks/job_auto_comment.json --multi-account
    
    # 检查执行结果
    exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 第 $counter 次执行完成 ✓"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 第 $counter 次执行失败，退出码: $exit_code ✗"
    fi
    
    # 增加计数器
    counter=$((counter + 1))
    
    # 等待60分钟 (3600秒)
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 等待120分钟后进行下次执行..."
    sleep 7200
done
