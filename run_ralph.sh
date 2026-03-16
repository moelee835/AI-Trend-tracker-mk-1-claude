#!/bin/bash
# run_ralph.sh — Ralph Loop 실행기

PROMPT_FILE="./prompt.md"
MAX_RUNS=50
run=0

while [ $run -lt $MAX_RUNS ]; do
  run=$((run + 1))
  echo "=== Session $run ==="

  # prompt.md를 파이프로 넘겨 non-interactive 모드 실행
  cat "$PROMPT_FILE" | claude -p

  # 종료 조건 5개 직접 검사
  all_pass=$(python3 -c "
import json, sys
try:
    features = json.load(open('feature_list.json'))
    print('yes' if all(f['passes'] for f in features) else 'no')
except: print('no')
")

  if [ "$all_pass" = "yes" ]; then
    echo "All features passing. Checking tests..."
    # 테스트 커버리지 확인 (프로젝트에 맞게 수정)
    npm test -- --coverage 2>&1 | tail -5
    echo "Ralph Loop complete after $run sessions."
    break
  fi

  echo "Not done yet. Starting session $((run + 1))..."
  sleep 2
done