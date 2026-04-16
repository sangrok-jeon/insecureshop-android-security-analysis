# InsecureShop - Insecure Logging

## 1. 개요

`InsecureShop`의 로그인 처리 로직을 분석한 결과, 사용자가 입력한 사용자명과 비밀번호가 Android 로그에 평문으로 출력되는 것을 확인하였다.

`LoginActivity`는 로그인 버튼 클릭 시 입력된 `username`, `password` 값을 읽은 뒤 `Log.d()`로 그대로 기록한다. 이후 동일한 값을 인증 로직에 전달하므로, 로그인 성공 여부와 관계없이 입력된 민감정보가 logcat에 남을 수 있다.

동적 검증에서는 로그인 화면에 `shopuser / !ns3csh0p` 값을 입력한 뒤 `adb logcat`을 확인하였다. 그 결과 `userName: shopuser`, `password: !ns3csh0p` 값이 평문으로 출력되는 것을 확인하였다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insecure Logging` |
| 취약점 유형 | 민감정보 로그 출력 |
| 영향 | logcat 접근 가능 환경에서 사용자 자격증명 평문 노출 |
| 분석 도구 | `jadx`, `adb` |
| 핵심 컴포넌트 | `LoginActivity` |
| 노출 데이터 | `username`, `password` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `jadx` |
| 동적 검증 | `adb logcat` |
| 검증 계정 | `shopuser / !ns3csh0p` |

## 4. 분석 방법

이번 항목은 로그인 입력값이 Android 로그에 기록되는지 확인하는 방식으로 분석하였다.

1. `LoginActivity`의 로그인 처리 로직을 확인하였다.
2. 입력된 `username`, `password`가 로그 출력 함수로 전달되는지 확인하였다.
3. 실제 앱에서 로그인 화면에 `shopuser / !ns3csh0p` 값을 입력하였다.
4. 로그인 버튼 클릭 후 `adb logcat`에서 동일한 값이 출력되는지 확인하였다.

## 5. 상세 분석

### 5.1 LoginActivity의 입력값 처리

`LoginActivity`는 로그인 화면에서 사용자가 입력한 사용자명과 비밀번호를 문자열로 읽어온다.

```java
String username = String.valueOf(textInputEditText.getText());
String password = String.valueOf(textInputEditText2.getText());
```

이후 해당 값은 인증 검증 함수로 전달되기 전에 로그로 먼저 출력된다.

### 5.2 username/password 로그 출력

로그인 처리 코드에서는 아래와 같이 `Log.d()`가 호출된다.

```java
Log.d("userName", username);
Log.d("password", password);
boolean auth = Util.INSTANCE.verifyUserNamePassword(username, password);
```

이 구현은 사용자가 입력한 자격증명을 Android 로그에 그대로 남긴다. 특히 `password`는 인증에 필요한 민감정보이므로 로그 출력 대상이 되어서는 안 된다.

문제는 이 로그가 인증 성공 후에만 출력되는 것이 아니라, 인증 검증 이전에 실행된다는 점이다. 따라서 사용자가 잘못된 비밀번호를 입력하더라도 그 값이 logcat에 남을 수 있다.

### 5.3 logcat에 남는 민감정보

동적 검증에서는 로그인 화면에 아래 값을 입력하였다.

```text
username: shopuser
password: !ns3csh0p
```

이후 `adb logcat`을 확인한 결과, 동일한 값이 로그에 출력되었다.

```text
D userName: shopuser
D password: !ns3csh0p
```

이 결과는 정적 분석에서 확인한 `Log.d()` 호출이 실제 런타임에서도 동작하며, 사용자가 입력한 자격증명이 평문으로 노출된다는 점을 보여준다.

## 6. 영향

Android 최신 버전에서는 일반 서드파티 앱이 다른 앱의 로그를 자유롭게 읽는 것이 제한되어 있지만, 로그에 민감정보를 남기는 구현은 여전히 안전하지 않다. 개발/테스트 환경, 디버그 빌드, 루팅 단말, MDM/로그 수집 도구, 물리 접근이 가능한 분석 환경에서는 logcat을 통해 민감정보가 노출될 수 있다.

실제 위험 시나리오는 다음과 같다.

- 디버그 환경에서 `adb logcat`으로 사용자 자격증명 노출
- 루팅된 단말 또는 분석 도구를 통한 앱 로그 수집
- 개발/운영 로그 수집 시스템에 민감정보 저장
- 테스트 빌드가 실사용 환경에 배포될 경우 계정 정보 유출
- 다른 로컬 취약점과 결합되어 로그 파일 또는 로그 스트림 탈취

이번 검증에서는 `shopuser / !ns3csh0p` 값이 그대로 logcat에 출력되는 것을 확인하였다.

## 7. 대응 방안

- 사용자명, 비밀번호, 토큰, 세션 값 등 민감정보를 로그로 출력하지 않아야 한다.
- 인증 로직 주변의 디버그 로그는 배포 전 제거해야 한다.
- 반드시 로그가 필요하다면 민감정보를 마스킹해야 한다.
- 릴리즈 빌드에서는 디버그 로그가 출력되지 않도록 로깅 정책을 분리해야 한다.
- 로그 수집 시스템에 민감정보가 전달되지 않도록 필터링 정책을 적용해야 한다.
- 코드 리뷰 및 정적 분석 단계에서 `Log.d()`, `Log.e()` 등에 민감정보가 전달되는지 점검해야 한다.

안전하지 않은 예시는 다음과 같다.

```java
Log.d("password", password);
```

개선 예시는 다음과 같다.

```java
Log.d("LoginActivity", "login button clicked");
```

또는 디버그 빌드에서만 최소한의 비식별 로그를 남기도록 제한해야 한다.

## 8. 결론

`LoginActivity`는 로그인 처리 과정에서 사용자가 입력한 `username`, `password` 값을 `Log.d()`로 출력하고 있었다. 동적 검증 결과 `adb logcat`에서 `userName: shopuser`, `password: !ns3csh0p` 값이 평문으로 확인되었다.

따라서 이번 항목은 **사용자 자격증명을 Android 로그에 평문으로 출력하는 Insecure Logging 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. LoginActivity의 민감정보 로그 출력 코드 확인

![LoginActivity 로그 출력 코드 확인](../images/19-Insecure%20Logging/01-loginactivity-log-code.png)

`LoginActivity`에서 `Log.d("userName", username)`와 `Log.d("password", password)`가 호출되는 것을 확인하였다. 이 코드는 사용자가 입력한 사용자명과 비밀번호를 Android 로그에 그대로 출력한다.

### 2. 로그인 정보 입력

![로그인 정보 입력](../images/19-Insecure%20Logging/02-login-input.png)

동적 검증을 위해 InsecureShop 로그인 화면에 `shopuser / !ns3csh0p` 값을 입력하였다. 이후 로그인 버튼을 눌러 `LoginActivity`의 로그인 처리 로직을 실행하였다.

### 3. logcat에서 자격증명 평문 출력 확인

![logcat 자격증명 출력 확인](../images/19-Insecure%20Logging/03-logcat-credentials.png)

`adb logcat` 확인 결과 `userName: shopuser`, `password: !ns3csh0p` 값이 평문으로 출력되었다. 이를 통해 로그인 입력값이 Android 로그에 그대로 기록되는 것을 동적으로 검증하였다.

## 10. 참고

- Android Developers - Log
- OWASP MASVS - Sensitive Data in Logs
- OWASP MASTG - Testing Logs for Sensitive Data
