# InsecureShop Android 앱 보안 분석

## 1. 프로젝트 개요

`InsecureShop`은 학습용으로 제작된 취약한 Android 애플리케이션으로, 로그인 로직, WebView 처리, Android 컴포넌트 노출, 네트워크 통신 등 다양한 보안 취약점을 포함하고 있다. 본 저장소는 `InsecureShop`을 대상으로 수행한 Android 앱 보안 분석 결과를 정리한 포트폴리오 프로젝트다.

이번 분석의 목적은 단순한 문제 풀이에 그치지 않고, Android 애플리케이션에서 자주 발생하는 취약점 유형을 실제 코드와 동작 기준으로 식별하고 재현 가능한 형태로 정리하는 데 있다.

## 2. 분석 대상 및 환경

| 항목 | 내용 |
|---|---|
| 분석 대상 | `InsecureShop` |
| 플랫폼 | Android |
| 실행 환경 | `Nox` |
| 분석 도구 | `adb`, `jadx`, `Android Studio` |
| 추가 도구 | `Burp Suite`, `Frida` |
| 분석 범위 | 로그인, WebView/Deeplink, Android Components, Content Provider, 네트워크 통신 |

## 3. 분석 방법

분석은 정적 분석과 동적 분석을 병행하는 방식으로 진행하였다.

- 정적 분석: `jadx`를 이용해 `AndroidManifest.xml`, Activity, Utility 클래스, WebView 처리 로직, Provider 설정, SSL 관련 코드를 확인하였다.
- 동적 분석: `adb`를 이용해 앱 설치 및 실행, 컴포넌트 호출, `logcat` 확인을 수행하였고, 필요한 경우 Android Studio 기반 PoC 앱으로 일반 서드파티 앱 관점의 재현을 진행하였다.
- 네트워크 분석: `Burp Suite`를 통해 프록시 기반 트래픽 확인 및 SSL 검증 우회 여부를 검토하였다.
- 런타임 분석: 필요한 경우 `Frida`를 이용해 메서드 동작과 우회 가능성을 확인하였다.

## 4. 취약점 분석

### 4.1 Hardcoded Credentials

상세 보고서: [01-hardcoded-credentials.md](./findings/01-hardcoded-credentials.md)

로그인 로직을 분석한 결과, 계정 정보가 애플리케이션 내부 코드에 하드코딩되어 있었고, APK 디컴파일만으로 식별한 자격증명을 이용해 정상 로그인까지 가능함을 확인하였다. 이 항목은 클라이언트 내부 인증정보 노출과 인증 우회 가능성을 보여주는 기본 사례다.

### 4.2 WebView Deeplink URL Validation Issues

상세 보고서: [02-webview-deeplink-url-validation.md](./findings/02-webview-deeplink-url-validation.md)

`WebViewActivity`를 분석한 결과, deeplink로 전달된 외부 URL을 WebView에 로드하는 과정에서 두 가지 문제가 확인되었다. `/web` 경로에서는 `url` 파라미터가 충분한 검증 없이 바로 `loadUrl()`로 전달되었고, `/webview` 경로에서는 검증이 존재하더라도 `endsWith("insecureshopapp.com")`와 같은 약한 문자열 비교만 수행하여 우회 가능성이 존재했다.
동적 검증에서는 `nox_adb shell am start` 명령으로 `/web` 및 `/webview` 경로를 각각 호출하여, 임의 URL 로드와 약한 host 검증 우회 가능성을 확인하였다. 이 항목은 deeplink, WebView, URL 검증 로직이 어떻게 결합되어 취약점으로 이어지는지를 보여준다.

### 4.3 Access to Protected Components

상세 보고서: [03-access-to-protected-components.md](./findings/03-access-to-protected-components.md)

`PrivateActivity`는 `android:exported="false"`로 선언되어 일반 외부 앱이 직접 접근할 수 없는 보호 대상 컴포넌트였다. 그러나 `WebView2Activity`는 외부에서 전달된 `extra_intent`를 `getParcelableExtra("extra_intent")`로 받은 뒤 검증 없이 `startActivity()`로 실행하고 있었다.

동적 검증은 일반 서드파티 앱 역할의 PoC 애플리케이션을 별도로 만들어 진행하였다. `PrivateActivity`를 직접 호출했을 때는 `SecurityException`이 발생했지만, `WebView2Activity`를 경유해 `extra_intent` 안에 `PrivateActivity` Intent를 넣어 전달했을 때는 내부 화면이 실제로 열렸다. 이를 통해 exported Activity를 통해 protected component에 우회 접근 가능한 구조를 확인하였다.

### 4.4 Insecure Content Provider

상세 보고서: [04-insecure-content-provider.md](./findings/04-insecure-content-provider.md)

`InsecureShopProvider`는 `content://com.insecureshop.provider/insecure` URI에 대한 query 요청을 처리하며, `username`과 `password`를 그대로 반환하고 있었다. `query()` 내부에서는 `Prefs`에 저장된 사용자명과 비밀번호를 `MatrixCursor`에 담아 반환하고 있었고, 실제로 `nox_adb shell content query` 명령만으로 자격증명이 직접 조회되었다.

## 5. 결론

이번 저장소에서는 `InsecureShop`을 대상으로 Android 앱 보안 분석을 수행하며, 현재 `Hardcoded Credentials`, `WebView Deeplink URL Validation Issues`, `Access to Protected Components`, `Insecure Content Provider` 네 가지 항목을 정리하였다. 각 사례를 통해 클라이언트 내부 자격증명 노출, deeplink 기반 WebView URL 처리 문제, Android 컴포넌트 보호 경계 우회, 그리고 IPC를 통한 민감정보 유출이 각각 어떤 방식으로 실제 악용 가능성으로 이어지는지 확인할 수 있었다.

각 분석은 정적 분석과 동적 검증을 함께 포함하며, 코드 근거와 실제 재현 절차를 함께 정리하는 것을 기준으로 작성하였다.
