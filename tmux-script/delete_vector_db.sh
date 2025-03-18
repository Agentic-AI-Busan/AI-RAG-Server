#!/bin/bash

# 사용자로부터 3개의 입력 받기
echo -e "tmux 세션 이름을 입력하세요:"
read SESSION_NAME

echo -e "저장소 이름을 입력하세요:"
read REPO_NAME

# 입력 값 확인
echo -e "\n입력한 값:"
echo "tmux 세션 이름: $SESSION_NAME"
echo "저장소 이름: $REPO_NAME"

# 기존에 동일한 이름의 세션이 있는지 확인
if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "경고: '$SESSION_NAME' 세션이 이미 존재합니다."
    read -p "기존 세션을 종료하고 새로 시작하시겠습니까? (y/n): " KILL_SESSION
    if [ "$KILL_SESSION" = "y" ]; then
        tmux kill-session -t $SESSION_NAME
    else
        echo "스크립트를 종료합니다."
        exit 1
    fi
fi

# tmux 세션 생성 및 명령 실행
echo -e "\ntmux 세션 '$SESSION_NAME'을 생성하고 명령을 실행합니다..."

COMMAND="rm -rf vectordb/$REPO_NAME"

# tmux 세션 생성 및 명령 실행
tmux new-session -d -s $SESSION_NAME
tmux send-keys -t $SESSION_NAME "docker exec ai-preprocessing bash -c \"$COMMAND > logs/delete_vector_db_logs 2>&1; exit \"" C-m