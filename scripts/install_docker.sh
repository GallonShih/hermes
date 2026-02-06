#!/bin/bash
# 安裝 Docker Engine + Docker Compose Plugin on Ubuntu 22.04

echo "👉 更新系統與必要工具..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg lsb-release

echo "👉 新增 Docker 官方 GPG 金鑰..."
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "👉 設定 Docker APT repository..."
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

echo "👉 安裝 Docker 與 Compose Plugin..."
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "✅ 測試 Docker 安裝是否成功..."
sudo docker run hello-world

echo "👉 將目前使用者加入 docker 群組（需重新登入生效）..."
sudo usermod -aG docker $USER

echo ""
echo "🎉 安裝完成！請輸入 exit，然後重新登入 SSH，以便使用 docker 指令不需 sudo"