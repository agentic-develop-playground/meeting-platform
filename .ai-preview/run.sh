#!/bin/bash
# Preview 环境启动脚本（A 方案：项目原生 settings.prod + 真 mysql-service）
# 假定预览部署到 ai-meeting-center namespace，那里运维侧长期部署了 mysql-service:3306。
# 项目期望的 DJANGO_SETTINGS_MODULE 是 meeting_platform.settings.prod（manage.py 默认）。
# settings.prod 需要 CONFIG_PATH / VAULT_PATH 指向有效 yaml：
#   - config.yaml 仓里有完整业务字段但 DEBUG=false/IS_DELETE_CONFIG=true，preview 模式改两个开关
#   - vault-config.yaml 仓里是空模板，preview 模式填好 SECRET_KEY/DB（指向 mysql-service）
set -e
cd /tmp/app

# Git 状态检查：确保运行的是 issue-140-impl 分支的最新提交
EXPECTED_BRANCH="issue-140-impl"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "$EXPECTED_BRANCH" ]; then
    echo "[WARN] Current branch '$CURRENT_BRANCH' != expected '$EXPECTED_BRANCH', fetching and resetting..."
    git fetch origin "$EXPECTED_BRANCH" 2>/dev/null || true
    git checkout "$EXPECTED_BRANCH" 2>/dev/null || true
    git reset --hard "origin/$EXPECTED_BRANCH" 2>/dev/null || true
fi
echo "[INFO] Running commit: $(git log --oneline -1)"

# 验证 MeetingStatsView 使用 IsAuthenticated（而非 AllowAny）
INNER_FILE="meeting_platform/apps/meeting/controller/inner.py"
MEETING_STATS_LINE=$(grep -n "class MeetingStatsView" "$INNER_FILE" | head -1 | cut -d: -f1)
if [ -n "$MEETING_STATS_LINE" ]; then
    PERMISSION_LINE=$(sed -n "${MEETING_STATS_LINE},$((MEETING_STATS_LINE + 10))p" "$INNER_FILE" | grep "permission_classes" | tail -1)
    if echo "$PERMISSION_LINE" | grep -q "AllowAny"; then
        echo "[ERROR] MeetingStatsView still has AllowAny permission, aborting"
        exit 1
    fi
    if ! echo "$PERMISSION_LINE" | grep -q "IsAuthenticated"; then
        echo "[ERROR] MeetingStatsView permission_classes is not IsAuthenticated, aborting"
        exit 1
    fi
    echo "[INFO] Permission check passed: MeetingStatsView uses IsAuthenticated"
else
    echo "[WARN] Could not find MeetingStatsView class for permission check"
fi

# 装依赖（drf-yasg 老版本依赖 pkg_resources，python 3.12 默认不带 setuptools，补一下）
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir setuptools

# config.yaml 项目仓里 DEBUG=false / IS_DELETE_CONFIG=true，preview 模式分别改成 true / false
sed -i 's/^DEBUG: false/DEBUG: true/' deploy/config/config.yaml
sed -i 's/^IS_DELETE_CONFIG: true/IS_DELETE_CONFIG: false/' deploy/config/config.yaml

# vault-config.yaml 项目仓里是空模板，preview 模式填好（仅 settings.prod 加载必须的字段）
# 注意：业务字段（COMMUNITY_ZOOM_OBS / COMMUNITY_HOST 等）prod.py 加载 settings 模块本身不读，
# 只有在调实际接口时才会读，preview 跑冒烟不需要全填
cat > deploy/config/vault-config.yaml <<'YEOF'
SECRET_KEY: "meeting-platform-preview-secret-key-2026"
DB:
  NAME: "meeting_platform"
  USER: "root"
  PASSWORD: "meeting_test_2026"
  HOST: "mysql-service"
  PORT: "3306"
COMMUNITY_ZOOM_OBS: {}
COMMUNITY_HOST: {}
MEETING_PLATFORM:
  USERNAME: "admin"
  PASSWORD: "meeting_admin_2026"
YEOF

export CONFIG_PATH="$PWD/deploy/config/config.yaml"
export VAULT_PATH="$PWD/deploy/config/vault-config.yaml"
export DJANGO_SETTINGS_MODULE=meeting_platform.settings.prod

# 跑 migration（连真 mysql-service）
python manage.py migrate --noinput || true

# 用 runserver 而非 gunicorn——项目 gunicorn.conf.py 要求 TLS cert（preview 没准备）
exec python manage.py runserver --noreload 0.0.0.0:${PORT:-8080}
