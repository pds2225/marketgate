# Claude Code: oh-my-claudecode

이 Cloud Agent 환경에는 아래가 준비되어 있습니다.

- CLI: `omc` (PATH: `~/.local/bin/omc`, v4.x)
- 플러그인 체크아웃: `~/.claude/plugins/oh-my-claudecode`

Cursor 채팅의 `/add-plugin` 은 Claude Code 플러그인 마켓플레이스 명령이라
**이 레포 에이전트에서는 실행되지 않습니다.** 로컬 Claude Code 세션에서:

```text
/plugin marketplace add https://github.com/Yeachan-Heo/oh-my-claudecode
/plugin install oh-my-claudecode
```

또는 체크아웃 직접 로드:

```bash
omc --plugin-dir ~/.claude/plugins/oh-my-claudecode
# 또는
claude --plugin-dir ~/.claude/plugins/oh-my-claudecode
```
