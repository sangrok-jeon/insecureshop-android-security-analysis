# InsecureShop Android Security Analysis

## 1. 프로젝트 개요

`InsecureShop`은 Optiv가 공개한 intentionally vulnerable Android 애플리케이션으로, 로그인 로직, WebView, Android 컴포넌트, Content Provider, 동적 코드 로딩 등 다양한 모바일 보안 이슈를 포함한다. 이 저장소는 공식 문제 번호를 기준으로 각 취약점의 코드 근거와 동적 검증 결과를 정리한다.

참조: [optiv/InsecureShop](https://github.com/optiv/InsecureShop)

## 2. 분석 환경

- 실행 환경: `Nox`
- 정적 분석: `jadx`
- 동적 분석: `adb`, `Android Studio`
- 보조 도구: `Burp Suite`, `Frida`, `APK Easy Tool`, `nuclei`, `AWS CLI`, `python http.server`

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
| 16 | Lack of SSL Certificate Validation | `APK Easy Tool`, `jadx`, `adb` | [findings/16-lack-of-ssl-certificate-validation.md](./findings/16-lack-of-ssl-certificate-validation.md) |
| 17 | Insecure WebView Properties Enabled | `APK Easy Tool`, `jadx`, `adb`, `python http.server` | [findings/17-insecure-webview-properties-enabled.md](./findings/17-insecure-webview-properties-enabled.md) |
| 18 | Insecure Data Storage | `APK Easy Tool`, `jadx`, `adb` | [findings/18-insecure-data-storage.md](./findings/18-insecure-data-storage.md) |
| 19 | Insecure Logging | `APK Easy Tool`, `jadx`, `adb logcat` | [findings/19-insecure-logging.md](./findings/19-insecure-logging.md) |

## 4. 공식 취약점 목록

아래 목록은 InsecureShop에서 다루는 주요 취약점 항목을 기준으로 정리하였다. 각 항목의 상세 분석과 동적 검증 결과는 위의 분석 현황 표에 연결된 개별 문서에서 확인할 수 있다.

1. **Hardcoded Credentials**: 애플리케이션 내부에 로그인 가능한 계정 정보가 하드코딩되어 있다.
2. **Insufficient URL Validation**: Deeplink로 전달된 URL이 충분히 검증되지 않은 채 WebView에 로드될 수 있다.
3. **Weak Host Validation Check**: 약한 host 검증으로 인해 허용되지 않은 URL이 WebView에 로드될 수 있다.
4. **Arbitrary Code Execution**: 서드파티 패키지 컨텍스트를 통해 임의 코드 실행으로 이어질 수 있다.
5. **Access to Protected Components**: embedded Intent를 검증 없이 `startActivity()`에 전달해 보호된 컴포넌트 접근이 가능해질 수 있다.
6. **Unprotected Data URIs**: 신뢰되지 않은 URI가 `loadUrl()`에 전달되어 WebView에서 임의 URI가 로드될 수 있다.
7. **Theft of Arbitrary Files**: `ChooserActivity`를 통해 앱 로컬 저장소의 파일을 외부로 복사할 수 있다.
8. **Using Components with Known Vulnerabilities**: 취약한 서드파티 컴포넌트가 로컬 파일 유출에 악용될 수 있다.
9. **Insecure Broadcast Receiver**: 동적으로 등록된 broadcast receiver가 외부 입력을 받아 임의 URL 로딩으로 이어질 수 있다.
10. **AWS Cognito Misconfiguration**: 잘못 구성된 AWS Cognito 설정을 통해 S3 버킷 접근이 가능해질 수 있다.
11. **Insecure use of FilePaths in FileProvider**: 과도하게 넓은 FileProvider 경로 설정으로 내부 파일 접근이 가능해질 수 있다.
12. **Use of Implicit Intent to Send a Broadcast with Sensitive Data**: 민감정보가 암시적 브로드캐스트로 전송되어 서드파티 앱이 수신할 수 있다.
13. **Intercepting Implicit intent to load arbitrary URL**: 암시적 Intent 처리 구조로 인해 서드파티 앱이 WebView URL 흐름을 가로챌 수 있다.
14. **Insecure Implementation of SetResult in Exported Activity**: exported Activity의 안전하지 않은 `setResult()` 구현이 임의 content provider 접근으로 이어질 수 있다.
15. **Insecure Content Provider**: 외부에서 접근 가능한 ContentProvider가 사용자 자격증명을 반환한다.
16. **Lack of SSL Certificate Validation**: WebView의 SSL 오류 처리 구현이 안전하지 않아 트래픽 도청 또는 변조 위험이 발생할 수 있다.
17. **Insecure WebView Properties Enabled**: 위험한 WebView 속성이 활성화되어 로컬 데이터가 원격 도메인으로 유출될 수 있다.
18. **Insecure Data Storage**: 사용자 자격증명이 암호화 없이 로컬에 저장된다.
19. **Insecure Logging**: 사용자 자격증명이 logcat에 평문으로 출력된다.

## 5. 참고 자료

- [optiv/InsecureShop](https://github.com/optiv/InsecureShop)
- [InsecureShopApp 본격해체쇼](https://aeng-is-young.tistory.com/entry/InsecureShopApp-%EB%B3%B8%EA%B2%A9%ED%95%B4%EC%B2%B4%EC%87%BC)
- [Walkthrough of The InsecureShop Android Vulnerable Application](https://itsfading.github.io/posts/Insecureshop-Android-Vulnerable-Application-Writeup/)
