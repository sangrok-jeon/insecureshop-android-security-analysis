# InsecureShop Android Security Analysis

## 1. 프로젝트 개요

`InsecureShop`은 로그인 로직, WebView, Android 컴포넌트, Content Provider, 동적 코드 로딩 등 다양한 모바일 보안 취약점을 포함한 학습용 애플리케이션이다. 이 저장소는 공식 문제 번호 기준으로 취약점을 분석하고, 코드 근거와 동적 검증 결과를 포트폴리오 형식으로 정리한 프로젝트다.

## 2. 분석 환경

- 실행 환경: `Nox`
- 정적 분석: `jadx`
- 동적 분석: `adb`, `nox_adb`, `Android Studio`
- 보조 도구: `Burp Suite`, `Frida`

## 3. 완료한 분석 현황

| # | 취약점 | 툴 | 경로 |
|---|---|---|---|
| 1 | Hardcoded Credentials | `jadx`, `nox_adb` | [findings/01-hardcoded-credentials.md](./findings/01-hardcoded-credentials.md) |
| 2 | Insufficient URL Validation | `jadx`, `nox_adb` | [findings/02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md) |
| 3 | Weak Host Validation Check | `jadx`, `nox_adb` | [findings/02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md) |
| 4 | Arbitrary Code Execution | `jadx`, `Android Studio`, `nox_adb`, `PoC App` | [findings/04-arbitrary-code-execution.md](./findings/04-arbitrary-code-execution.md) |
| 5 | Access to Protected Components | `jadx`, `Android Studio`, `PoC App` | [findings/05-access-to-protected-components.md](./findings/05-access-to-protected-components.md) |
| 6 | Unprotected Data URIs | `jadx`, `nox_adb` | [findings/06-unprotected-data-uris.md](./findings/06-unprotected-data-uris.md) |
| 7 | Theft of Arbitrary Files | `jadx`, `nox_adb` | [findings/07-theft-of-arbitrary-files.md](./findings/07-theft-of-arbitrary-files.md) |
| 15 | Insecure Content Provider | `jadx`, `nox_adb` | [findings/15-insecure-content-provider.md](./findings/15-insecure-content-provider.md) |

`2`와 `3`은 동일한 `WebViewActivity`의 deeplink 처리 구조에서 함께 발생해 하나의 상세 보고서로 통합했다. `4`는 Android Studio로 제작한 별도 `PoC App`과 `logcat` 검증 결과를 함께 사용해 재현했다.
