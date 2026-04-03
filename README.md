# InsecureShop Android 보안 분석

## 1. 프로젝트 개요

`InsecureShop`은 로그인 로직, WebView, Android 컴포넌트, Content Provider, 네트워크 처리 등 다양한 모바일 보안 취약점을 포함한 실습용 Android 애플리케이션이다. 이 저장소는 `InsecureShop`의 취약점을 공식 문제 번호 기준으로 분석하고, 코드 근거와 동적 검증 결과를 함께 정리한 포트폴리오 프로젝트다.

## 2. 분석 환경

- 실행 환경: `Nox`
- 정적 분석: `jadx`
- 동적 분석: `adb`, `nox_adb`, Android Studio
- 보조 도구: `Burp Suite`, `Frida`

## 3. 완료한 분석 현황

| # | 취약점 | 툴 | 경로 |
|---|---|---|---|
| 1 | Hardcoded Credentials | `jadx`, `nox_adb` | [findings/01-hardcoded-credentials.md](./findings/01-hardcoded-credentials.md) |
| 2 | Insufficient URL Validation | `jadx`, `nox_adb` | [findings/02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md) |
| 3 | Weak Host Validation Check | `jadx`, `nox_adb` | [findings/02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md) |
| 5 | Access to Protected Components | `jadx`, `Android Studio`, `PoC` | [findings/05-access-to-protected-components.md](./findings/05-access-to-protected-components.md) |
| 15 | Insecure Content Provider | `jadx`, `nox_adb` | [findings/15-insecure-content-provider.md](./findings/15-insecure-content-provider.md) |

`2`와 `3`은 동일한 `WebViewActivity`의 deeplink 처리 구조에서 함께 확인되어 하나의 상세 보고서로 통합해 정리하였다.
