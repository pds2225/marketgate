# GitHub 인증 가이드

GitHub 인증은 GitHub CLI 또는 Git Credential Manager를 우선 사용합니다. Personal Access Token(PAT)을 채팅, 문서, 코드, 커밋, 이슈, PR 본문에 붙여넣지 마세요.

## 권장: GitHub CLI로 로그인

~~~powershell
gh auth login
gh auth status
~~~

로그인 화면에서는 GitHub.com, HTTPS, 브라우저 로그인을 선택합니다. 자격 증명은 운영체제의 보안 저장소에 보관됩니다.

## PAT가 꼭 필요한 경우

1. GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens로 이동합니다.
2. 만료 기간은 작업에 필요한 최소 기간으로 설정합니다.
3. Resource owner를 확인합니다.
4. Repository access는 Only select repositories를 선택하고 marketgate만 지정합니다.
5. 권한은 작업에 필요한 최소 범위만 부여합니다.
   - 일반 코드 읽기·커밋·푸시: Contents
   - PR 생성·수정: Pull requests
   - 워크플로 파일 수정: 해당 작업을 할 때만 Workflows
6. 생성된 토큰은 비밀 관리자 또는 운영체제 자격 증명 저장소에 보관합니다.

Classic PAT, 무기한 토큰, 모든 저장소 접근, 광범위한 repo/workflow 권한을 기본값으로 사용하지 않습니다.

## 금지 사항

- 토큰을 채팅이나 이메일로 전달
- 저장소 파일, .env.example, 문서, 스크립트에 토큰 기록
- 명령 기록에 토큰이 남도록 직접 입력
- 실제 필요보다 넓은 저장소·조직·워크플로 권한 부여
- 만료 없는 토큰을 편의상 발급

## 노출이 의심될 때

1. GitHub Settings에서 해당 토큰을 즉시 revoke합니다.
2. 필요한 최소 권한과 짧은 만료 기간으로 새 토큰을 발급합니다.
3. 저장소의 현재 파일뿐 아니라 Git 기록, PR, 이슈, 로그도 점검합니다.
4. 관련 서비스의 자격 증명과 비밀도 함께 교체합니다.

## 참고

- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- https://docs.github.com/en/rest/authentication/keeping-your-api-credentials-secure
- https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/token-expiration-and-revocation
