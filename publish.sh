#!/usr/bin/env bash
# Публикация офиса агентов на GitHub.
# Использование: ./publish.sh <your-github-username>
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 <github-username>"
  echo "Пример: $0 piniest"
  exit 1
fi

USER="$1"
REPO="agent-office"

# 1. Добавьте публичный ключ в GitHub (один раз):
#    https://github.com/settings/ssh/new
#    Key:   $(cat ~/.ssh/id_ed25519_github.pub)
echo "1. Убедитесь, что ключ добавлен:"
echo "   https://github.com/settings/ssh/new"
echo "   Key = $(cat ~/.ssh/id_ed25519_github.pub)"
echo ""

# 2. Настройка ssh для github
if ! grep -q "Host github.com" ~/.ssh/config 2>/dev/null; then
  cat >> ~/.ssh/config <<EOF
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_github
  IdentitiesOnly yes
EOF
  echo "2. ~/.ssh/config настроен"
fi

# 3. Проверка доступа
if ssh -o StrictHostKeyChecking=no -o BatchMode=yes -T git@github.com 2>&1 | grep -qi "successfully authenticated"; then
  echo "3. SSH-доступ к GitHub: OK"
else
  echo "3. SSH-доступ к GitHub: НЕТ (добавьте ключ и повторите)"
  exit 1
fi

# 4. Создание репозитория (публичный, без gh можно через API с токеном; с gh — напрямую)
if command -v gh >/dev/null 2>&1; then
  gh repo create "$USER/$REPO" --public --source . --push || echo "repo уже существует, пробую push"
else
  echo "4. gh не установлен. Создайте репозиторий вручную:"
  echo "   https://github.com/new  ->  name: $REPO  (Public)"
fi

# 5. Remote + push
git remote remove origin 2>/dev/null || true
git remote add origin "git@github.com:$USER/$REPO.git"
git branch -M main
git push -u origin main && echo "PUSHED: https://github.com/$USER/$REPO"
