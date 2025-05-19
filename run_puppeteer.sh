#!/bin/bash

echo "Puppeteer 서버 시작..."

# Node 모듈 설치
if [ ! -d "node_modules" ]; then
    echo "Node 모듈 설치 중..."
    npm install
fi

# Puppeteer 서버 실행
echo "Puppeteer 서버 실행 중..."
node puppeteer_server.js