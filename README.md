# InsecureShop Android 앱 보안 분석

## 0. 폴더 구조

```text
insecureshop/
├─ README.md
└─ images/
   ├─ 01-hardcoded-credentials/
   ├─ 02-weak-host-validation-check/
   ├─ 03-access-to-protected-components/
   ├─ 04-insecure-content-provider/
   └─ 05-lack-of-ssl-certificate-validation/
```

이미지는 취약점별로 분리해 저장하고, 각 섹션의 `취약점 테스트` 항목에 적어둔 파일명 규칙을 그대로 사용하는 것을 기준으로 한다. 이렇게 정리하면 README 수정과 이미지 교체가 쉬워지고, GitHub에서도 구조가 한눈에 보인다.

## 1. 프로젝트 개요

`InsecureShop`은 학습용으로 제작된 취약한 Android 애플리케이션으로, 로그인 로직, WebView 처리, Android 컴포넌트 노출, 네트워크 통신 등 다양한 보안 취약점을 포함하고 있다. 본 프로젝트에서는 앱 전반을 분석한 뒤, 포트폴리오 관점에서 대표성이 높은 5개 취약점을 선정하여 정적 분석과 동적 분석을 수행하였다.

이번 분석의 목적은 단순한 문제 풀이에 그치지 않고, Android 애플리케이션에서 자주 발생하는 취약점 유형을 실제 코드와 동작 기준으로 식별하고, 재현 가능한 형태로 정리하는 데 있다.

## 2. 분석 대상 및 환경

| 항목 | 내용 |
|---|---|
| 분석 대상 | `InsecureShop` |
| 플랫폼 | Android |
| 실행 환경 | `Nox` |
| 분석 도구 | `adb`, `jadx` |
| 추가 도구 | `Burp Suite`, `Frida` |
| 분석 범위 | 로그인, WebView/Deeplink, Android Components, Content Provider, 네트워크 통신 |

## 3. 분석 방법

분석은 정적 분석과 동적 분석을 병행하는 방식으로 진행하였다.

- 정적 분석: `jadx`를 이용해 `AndroidManifest.xml`, Activity, Utility 클래스, WebView 처리 로직, Provider 설정, SSL 관련 코드를 확인하였다.
- 동적 분석: `adb`를 이용해 앱 설치 및 실행, 컴포넌트 호출, `logcat` 확인을 수행하였다.
- 네트워크 분석: `Burp Suite`를 통해 프록시 기반 트래픽 확인 및 SSL 검증 우회 여부를 검토하였다.
- 런타임 분석: 필요한 경우 `Frida`를 이용해 메서드 동작과 우회 가능성을 확인하였다.

## 4. 주요 취약점

### 4.1 Hardcoded Credentials

상세 보고서: [01-hardcoded-credentials.md](./findings/01-hardcoded-credentials.md)

#### 개요

로그인 기능을 분석한 결과, 사용자 인증에 사용되는 계정 정보가 애플리케이션 내부 코드에 하드코딩되어 있음을 확인하였다. 공격자는 APK를 디컴파일해 자격증명을 식별할 수 있으며, 이를 이용해 정상 로그인 절차를 그대로 통과할 수 있다.

#### 분석 방법

로그인 화면에서 임의의 값을 입력해 동작을 먼저 확인한 뒤, `jadx`를 이용해 로그인 처리 로직을 추적하였다. `LoginActivity`의 `onLogin()` 메서드에서 입력된 아이디와 비밀번호가 인증 함수로 전달되는 흐름을 확인하고, 이후 실제 인증 로직이 구현된 메서드까지 따라가며 계정 검증 방식을 분석하였다.

#### 발견 근거

`LoginActivity.onLogin()`에서는 사용자가 입력한 `username`, `password`를 `Util.verifyUserNamePassword(username, password)`로 전달한다. 이후 인증 로직을 추적한 결과, `getUserCreds()` 메서드에서 계정 정보가 `HashMap` 형태로 직접 선언되어 있었으며, `shopuser`와 `!ns3csh0p`가 하드코딩된 자격증명으로 사용되고 있음을 확인하였다.

이는 인증에 필요한 민감 정보가 클라이언트 애플리케이션 내부에 포함되어 있다는 의미이며, 공격자는 APK 확보만으로 자격증명 추출이 가능하다.

#### 재현 과정

먼저 로그인 화면에서 임의의 값을 입력했을 때 `Invalid username and password` 메시지가 출력되는 것을 확인하였다. 이후 `jadx`에서 로그인 로직을 분석하여 하드코딩된 계정 정보 `shopuser / !ns3csh0p`를 식별하였다. 식별한 계정 정보를 실제 로그인 화면에 입력한 결과, `ProductListActivity`로 이동하며 로그인이 성공하는 것을 확인하였다.

이를 통해 앱 내부에 포함된 자격증명만으로 인증 절차가 우회 가능함을 검증하였다.

#### 영향도

하드코딩된 자격증명은 디컴파일만으로 쉽게 추출될 수 있으므로, 공격자가 정상 사용자 권한을 획득하는 데 직접 악용될 수 있다. 특히 인증 검증이 클라이언트 내부 로직에 의존하는 경우, 앱을 분석한 누구나 동일한 방식으로 로그인 기능을 우회할 수 있다.

#### 대응 방안

- 인증에 사용되는 계정 정보나 비밀값을 애플리케이션 내부에 하드코딩하지 않아야 한다.
- 자격증명 검증은 서버 측에서 수행하고, 클라이언트는 결과만 처리하도록 설계해야 한다.
- 난독화는 분석 난도를 높이는 보조 수단일 뿐, 하드코딩 문제의 근본적인 해결책이 될 수 없다.

#### 취약점 테스트

이미지는 `README.md` 기준 상대 경로인 `./images/...`를 사용한다.

1. `./images/01-hardcoded-credentials/01-invalid-login.png`
2. `./images/01-hardcoded-credentials/02-login-activity-onlogin.png`
3. `./images/01-hardcoded-credentials/03-get-user-creds.png`
4. `./images/01-hardcoded-credentials/04-login-success.png`

실제 이미지 파일을 추가한 뒤 아래와 같이 바로 렌더링되도록 넣는다.

![그림 1. 임의 자격증명 입력 시 로그인 실패](./images/01-hardcoded-credentials/01-invalid-login.png)

![그림 2. LoginActivity에서 인증 함수 호출 확인](./images/01-hardcoded-credentials/02-login-activity-onlogin.png)

![그림 3. getUserCreds에서 하드코딩된 자격증명 확인](./images/01-hardcoded-credentials/03-get-user-creds.png)

![그림 4. 추출한 자격증명으로 로그인 성공](./images/01-hardcoded-credentials/04-login-success.png)

### 4.2 Weak Host Validation Check

#### 개요

앱의 URL 검증 로직을 분석하여, 허용된 호스트만 로드해야 하는 기능이 불완전한 검증 방식으로 구현되어 있는지 확인한다. 단순 문자열 비교 또는 불완전한 조건 검증이 존재할 경우, 공격자는 우회된 URL을 WebView에 로드시켜 임의 페이지를 표시할 수 있다.

#### 분석 방법

- `AndroidManifest.xml`에서 Deeplink 관련 Activity를 확인한다.
- `jadx`에서 `loadUrl`, `shouldOverrideUrlLoading`, `Uri.parse`, `getHost` 관련 코드를 추적한다.
- 호스트 검증 함수가 문자열 포함 여부, 접두사 비교, 부분 일치 등 취약한 방식으로 구현되어 있는지 확인한다.
- 필요 시 `adb` 또는 `Frida`를 통해 우회된 URL이 실제로 로드되는지 검증한다.

#### 발견 근거

`TODO: 호스트 검증 함수명, Activity명, 우회 가능한 URL 패턴 정리`

#### 재현 과정

`TODO: 정상 URL과 우회 URL 비교, adb 명령 또는 deeplink 호출 방식 작성`

#### 영향도

신뢰되지 않은 URL이 WebView에 로드될 경우 피싱 페이지 노출, 악성 스크립트 실행, 로컬 리소스 접근 시도 등으로 이어질 수 있다. 특히 사용자가 앱 내부 페이지로 오인할 가능성이 높아 보안 위험이 증가한다.

#### 대응 방안

- URL 허용 정책은 명확한 allowlist 기반으로 구현해야 한다.
- `scheme`, `host`, `path`를 모두 엄격히 검증해야 한다.
- 부분 문자열 비교가 아닌 정규화된 URL 비교를 사용해야 한다.

#### 취약점 테스트

1. `./images/02-weak-host-validation-check/01-deeplink-entry.png`
2. `./images/02-weak-host-validation-check/02-host-validation-code.png`
3. `./images/02-weak-host-validation-check/03-bypass-url.png`
4. `./images/02-weak-host-validation-check/04-webview-load-result.png`

### 4.3 Access to Protected Components

#### 개요

앱이 외부 입력으로 전달받은 `Intent`를 적절한 검증 없이 `startActivity()` 등에 전달하는 경우, 제3자 앱이 원래 보호되어야 하는 컴포넌트를 실행할 수 있다. 이는 Android 컴포넌트 노출 문제와 Intent 전달 구조를 함께 이해해야 하는 취약점이다.

#### 분석 방법

- `AndroidManifest.xml`에서 `exported` 설정과 컴포넌트 노출 상태를 확인한다.
- `jadx`에서 `getParcelableExtra`, `getIntent`, `startActivity`, `startActivityForResult` 사용 지점을 확인한다.
- 외부에서 주입된 `Intent` 객체가 내부 검증 없이 전달되는 흐름이 있는지 추적한다.
- `adb shell am start` 또는 PoC 앱을 통해 실제 컴포넌트 실행 가능 여부를 검증한다.

#### 발견 근거

`TODO: 취약한 Activity 또는 Intent 전달 코드 정리`

#### 재현 과정

`TODO: 외부에서 전달한 Intent로 보호된 컴포넌트 호출 절차 작성`

#### 영향도

정상적인 앱 흐름에서만 접근 가능해야 하는 내부 기능이 외부 앱에 의해 직접 실행될 수 있다. 이 과정에서 민감한 화면 노출, 내부 기능 악용, 추가적인 IPC 취약점 악용으로 이어질 가능성이 있다.

#### 대응 방안

- 외부 입력으로 전달된 `Intent`를 그대로 실행하지 않아야 한다.
- 호출 가능한 컴포넌트를 명시적으로 제한해야 한다.
- 내부 전용 컴포넌트는 `exported=false` 또는 권한 보호 설정을 적용해야 한다.

#### 취약점 테스트

1. `./images/03-access-to-protected-components/01-manifest-component.png`
2. `./images/03-access-to-protected-components/02-intent-receive-code.png`
3. `./images/03-access-to-protected-components/03-start-activity-code.png`
4. `./images/03-access-to-protected-components/04-external-launch-result.png`

### 4.4 Insecure Content Provider

#### 개요

앱의 `ContentProvider`가 적절한 접근 제어 없이 외부에 노출되어 있는 경우, 제3자 앱 또는 ADB를 통해 민감한 데이터를 조회할 수 있다. 이 취약점은 Android 데이터 공유 구조에 대한 이해를 보여주기 좋은 사례다.

#### 분석 방법

- `AndroidManifest.xml`에서 `provider` 선언과 `exported`, `grantUriPermissions`, `authorities` 값을 확인한다.
- `jadx`에서 `query`, `insert`, `update`, `delete` 구현 여부와 권한 검증 로직을 확인한다.
- `adb shell content query` 등으로 외부 접근 가능 여부를 검증한다.

#### 발견 근거

`TODO: provider authority, 노출 여부, 민감 데이터 위치 정리`

#### 재현 과정

`TODO: adb content query 명령과 반환 결과 작성`

#### 영향도

적절한 권한 검증이 없는 `ContentProvider`는 외부 앱이 사용자 자격증명, 로컬 저장 데이터, 설정값 등 민감 정보를 직접 읽을 수 있게 만든다. 실제 앱에서 이 구조가 존재할 경우 계정 탈취나 개인 정보 유출로 이어질 수 있다.

#### 대응 방안

- 민감 데이터를 제공하는 `ContentProvider`는 기본적으로 외부 공개를 피해야 한다.
- 외부 공개가 필요할 경우 읽기/쓰기 권한을 명시적으로 분리하고 권한 검사를 적용해야 한다.
- 민감한 컬럼은 최소화하고, 접근 가능한 URI 범위를 제한해야 한다.

#### 취약점 테스트

1. `./images/04-insecure-content-provider/01-manifest-provider.png`
2. `./images/04-insecure-content-provider/02-provider-code.png`
3. `./images/04-insecure-content-provider/03-content-query-command.png`
4. `./images/04-insecure-content-provider/04-query-result.png`

### 4.5 Lack of SSL Certificate Validation

#### 개요

앱의 WebView 또는 네트워크 처리 로직에서 SSL 인증서 오류를 안전하게 처리하지 않는 경우, 공격자는 중간자 공격 환경에서 트래픽을 가로채거나 위조된 인증서를 이용해 사용자 통신을 감시할 수 있다.

#### 분석 방법

- `jadx`에서 `onReceivedSslError`, `SslErrorHandler.proceed`, `WebViewClient` 구현을 검색한다.
- SSL 오류 발생 시 사용자 경고 없이 통신을 계속 허용하는지 확인한다.
- `Burp Suite` 프록시 환경에서 실제 트래픽 가시성 여부를 확인한다.

#### 발견 근거

`TODO: SSL 오류 처리 코드와 취약한 메서드 정리`

#### 재현 과정

`TODO: Burp 프록시 연결, 인증서 오류 무시 동작, 트래픽 확인 절차 작성`

#### 영향도

SSL 검증이 제대로 이뤄지지 않으면 공격자는 사용자의 요청과 응답을 가로채거나 변조할 수 있다. 로그인 정보, 세션 정보, 웹 콘텐츠가 모두 노출될 수 있으므로 네트워크 구간의 기밀성과 무결성이 훼손된다.

#### 대응 방안

- SSL 오류 발생 시 통신을 즉시 중단해야 한다.
- `SslErrorHandler.proceed()` 호출을 지양하고 기본 검증 흐름을 유지해야 한다.
- 필요한 경우 인증서 고정(`SSL Pinning`) 등 추가 보호 기법을 검토할 수 있다.

#### 취약점 테스트

1. `./images/05-lack-of-ssl-certificate-validation/01-ssl-error-code.png`
2. `./images/05-lack-of-ssl-certificate-validation/02-proxy-setup.png`
3. `./images/05-lack-of-ssl-certificate-validation/03-burp-traffic.png`
4. `./images/05-lack-of-ssl-certificate-validation/04-mitm-result.png`

## 5. 종합 대응 방안

`InsecureShop`에서 확인한 주요 취약점은 서로 다른 영역에 존재하지만, 공통적으로 "신뢰하면 안 되는 입력과 클라이언트 내부 정보에 대한 과도한 신뢰"라는 문제를 보여준다. 따라서 다음과 같은 원칙이 필요하다.

- 인증과 권한 검증은 가능한 한 서버 측에서 수행한다.
- 외부에서 유입되는 URL, Intent, URI는 모두 명시적 allowlist 기반으로 검증한다.
- Android 컴포넌트는 최소 권한 원칙에 따라 외부 공개 범위를 축소한다.
- 민감 정보는 앱 내부에 하드코딩하거나 평문으로 저장하지 않는다.
- 네트워크 통신은 기본적인 TLS 검증을 우회하지 않도록 구현한다.

## 6. 결론

이번 프로젝트에서는 `InsecureShop`을 대상으로 대표 취약점 5개를 선정해 Android 앱 보안 분석을 수행하였다. 분석 과정에서 `jadx`를 이용한 정적 분석, `adb` 기반 동적 검증, `Burp Suite`를 통한 네트워크 확인, 필요 시 `Frida`를 활용한 런타임 분석까지 연결 가능한 구조를 설계하였다.

특히 단순히 취약점을 나열하는 데 그치지 않고, 실제 코드 위치, 재현 절차, 영향도, 대응 방안까지 함께 정리함으로써 모바일 애플리케이션 보안 분석 역량을 체계적으로 보여주고자 했다.

## 7. 작성 메모

- 각 취약점은 동일한 형식으로 유지한다.
- 취약점 테스트 이미지는 취약점당 3~4장으로 제한해 핵심만 남긴다.
- `Hardcoded Credentials` 외의 항목은 실제 분석 후 `TODO` 부분만 채우면 된다.
- 추가로 `Insecure Logging`, `Insecure Data Storage`는 부록 또는 추가 발견 사항으로 짧게 정리할 수 있다.
