# InsecureShop Android Security Analysis

## 1. 프로젝트 개요

`InsecureShop`은 Optiv가 공개한 intentionally vulnerable Android 애플리케이션으로, 로그인 로직, WebView, Android 컴포넌트, Content Provider, 동적 코드 로딩 등 다양한 모바일 보안 이슈를 포함한다. 이 저장소는 공식 문제 번호를 기준으로 각 취약점의 코드 근거와 동적 검증 결과를 정리한다.

참조: [optiv/InsecureShop](https://github.com/optiv/InsecureShop)

## 2. 분석 환경

- 실행 환경: `Nox`
- 정적 분석: `jadx`
- 동적 분석: `adb`, `Android Studio`
- 보조 도구: `Burp Suite`, `Frida`

## 3. 완료한 분석 현황

| # | 취약점 | 툴 | 경로 |
|---|---|---|---|
| 1 | Hardcoded Credentials | `jadx`, `adb` | [findings/01-hardcoded-credentials.md](./findings/01-hardcoded-credentials.md) |
| 2 | Insufficient URL Validation | `jadx`, `adb` | [findings/02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md) |
| 3 | Weak Host Validation Check | `jadx`, `adb` | [findings/02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md) |
| 4 | Arbitrary Code Execution | `jadx`, `Android Studio`, `adb`, `PoC App` | [findings/04-arbitrary-code-execution.md](./findings/04-arbitrary-code-execution.md) |
| 5 | Access to Protected Components | `jadx`, `Android Studio`, `PoC App` | [findings/05-access-to-protected-components.md](./findings/05-access-to-protected-components.md) |
| 6 | Unprotected Data URIs | `jadx`, `adb` | [findings/06-unprotected-data-uris.md](./findings/06-unprotected-data-uris.md) |
| 7 | Theft of Arbitrary Files | `jadx`, `adb` | [findings/07-theft-of-arbitrary-files.md](./findings/07-theft-of-arbitrary-files.md) |
| 8 | Using Components with Known Vulnerabilities | `jadx`, `Android Studio`, `PoC App` | [findings/08-using-components-with-known-vulnerabilities.md](./findings/08-using-components-with-known-vulnerabilities.md) |
| 9 | Insecure Broadcast Receiver | `jadx`, `adb` | [findings/09-insecure-broadcast-receiver.md](./findings/09-insecure-broadcast-receiver.md) |
| 10 | AWS Cognito Misconfiguration | `APK Easy Tool`, `nuclei`, `AWS CLI` | [findings/10-aws-cognito-misconfiguration.md](./findings/10-aws-cognito-misconfiguration.md) |
| 11 | Insecure use of FilePaths in FileProvider | `APK Easy Tool`, `jadx`, `Android Studio`, `adb`, `PoC App` | [findings/11-insecure-use-of-filepaths-in-fileprovider.md](./findings/11-insecure-use-of-filepaths-in-fileprovider.md) |
| 12 | Use of Implicit Intent to Send a Broadcast with Sensitive Data | `APK Easy Tool`, `jadx`, `Android Studio`, `adb`, `PoC App` | [findings/12-use-of-implicit-intent-to-send-a-broadcast-with-sensitive-data.md](./findings/12-use-of-implicit-intent-to-send-a-broadcast-with-sensitive-data.md) |
| 13 | Intercepting Implicit intent to load arbitrary URL | `APK Easy Tool`, `jadx`, `Android Studio`, `adb`, `PoC App` | [findings/13-intercepting-implicit-intent-to-load-arbitrary-url.md](./findings/13-intercepting-implicit-intent-to-load-arbitrary-url.md) |
| 14 | Insecure Implementation of SetResult in Exported Activity | `APK Easy Tool`, `jadx`, `Android Studio`, `adb`, `PoC App` | [findings/14-insecure-implementation-of-setresult-in-exported-activity.md](./findings/14-insecure-implementation-of-setresult-in-exported-activity.md) |
| 15 | Insecure Content Provider | `jadx`, `adb` | [findings/15-insecure-content-provider.md](./findings/15-insecure-content-provider.md) |
