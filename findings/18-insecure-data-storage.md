# InsecureShop - Insecure Data Storage

## 1. 개요

`InsecureShop`의 로그인 및 로컬 저장 로직을 분석한 결과, 사용자 자격증명이 암호화 없이 `SharedPreferences`에 저장되는 것을 확인하였다.

로그인 성공 시 `LoginActivity`는 입력된 `username`, `password` 값을 `Prefs.setUsername()`, `Prefs.setPassword()`로 전달한다. 이후 `Prefs` 클래스는 `context.getSharedPreferences("Prefs", 0)`로 생성한 `SharedPreferences`에 값을 저장하며, 내부적으로 `putString("username", value)`, `putString("password", value)`를 그대로 호출한다.

동적 검증에서는 로그인 후 `/data/data/com.insecureshop/shared_prefs/Prefs.xml` 파일을 확인하였다. 해당 파일에는 `username`과 `password`가 별도의 암호화, 해시, Keystore 보호 없이 XML 문자열 형태로 저장되어 있었다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insecure Data Storage` |
| 취약점 유형 | 민감정보 평문 로컬 저장 |
| 영향 | 로컬 파일 접근 가능 시 사용자명/비밀번호 평문 노출 |
| 분석 도구 | `jadx`, `adb` |
| 핵심 컴포넌트 | `LoginActivity`, `Prefs` |
| 저장 위치 | `/data/data/com.insecureshop/shared_prefs/Prefs.xml` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `jadx` |
| 동적 검증 | `adb shell` |
| 검증 계정 | `shopuser / !ns3csh0p` |

## 4. 분석 방법

이번 항목은 로그인 성공 후 입력된 자격증명이 어떤 저장소에 어떤 형태로 기록되는지 추적하는 방식으로 분석하였다.

1. `AndroidManifest.xml`에서 로그인 기능의 진입점인 `LoginActivity`를 확인하였다.
2. `LoginActivity`에서 로그인 성공 후 `Prefs`에 사용자명과 비밀번호를 저장하는지 확인하였다.
3. `Prefs.getInstance()`가 어떤 로컬 저장소를 사용하는지 확인하였다.
4. `Prefs.setUsername()`, `Prefs.setPassword()` 내부에서 암호화 없이 `putString()`을 호출하는지 확인하였다.
5. 실제 앱에서 `shopuser / !ns3csh0p`로 로그인하였다.
6. `/data/data/com.insecureshop/shared_prefs/Prefs.xml` 파일을 확인해 값이 평문으로 저장되는지 검증하였다.

## 5. 상세 분석

### 5.1 LoginActivity 식별

Manifest를 확인한 결과 로그인 화면은 `com.insecureshop.LoginActivity`로 구성되어 있었다.

```xml
<activity android:name="com.insecureshop.LoginActivity"/>
```

따라서 로그인 입력값이 저장되는 흐름을 확인하기 위해 `LoginActivity`의 인증 성공 분기를 우선 분석하였다.

### 5.2 로그인 성공 후 Prefs에 자격증명 저장

`LoginActivity`의 로그인 처리 흐름을 확인한 결과, 입력된 `username`, `password` 값을 검증한 뒤 인증에 성공하면 `Prefs`에 저장하고 있었다.

```java
boolean auth = Util.INSTANCE.verifyUserNamePassword(username, password);
if (auth) {
    Prefs prefs = Prefs.INSTANCE;
    Context applicationContext = getApplicationContext();
    prefs.getInstance(applicationContext).setUsername(username);

    Prefs prefs2 = Prefs.INSTANCE;
    Context applicationContext2 = getApplicationContext();
    prefs2.getInstance(applicationContext2).setPassword(password);

    Intent intent = new Intent(this, (Class<?>) ProductListActivity.class);
    startActivity(intent);
    return;
}
```

이 코드는 인증 성공 후 사용자가 입력한 계정 정보를 메모리에서만 사용하는 것이 아니라, 앱 로컬 저장소에 별도로 기록한다는 의미다.

### 5.3 SharedPreferences 기반 저장소 사용

`Prefs.getInstance()`를 확인한 결과, 앱은 `SharedPreferences`를 사용해 값을 저장하고 있었다.

```java
public final Prefs getInstance(Context context) {
    if (prefs == null) {
        SharedPreferences sharedPreferences =
            context.getSharedPreferences("Prefs", 0);
        sharedpreferences = sharedPreferences;
        prefs = this;
    }
    return prefs;
}
```

`getSharedPreferences("Prefs", 0)`에서 `"Prefs"`는 저장 파일 이름이고, `0`은 `MODE_PRIVATE`에 해당한다. `MODE_PRIVATE`은 다른 앱이 일반 권한으로 직접 접근하지 못하도록 제한하는 설정일 뿐, 저장 값 자체를 암호화하지는 않는다.

Android의 `SharedPreferences`는 기본적으로 앱 내부 저장소에 XML 파일 형태로 값을 기록한다. 따라서 이 코드 흐름에서는 아래 파일이 생성된다.

```text
/data/data/com.insecureshop/shared_prefs/Prefs.xml
```

### 5.4 password 평문 저장

`Prefs.setPassword()` 구현을 확인한 결과, 전달받은 `password` 값을 별도의 암호화 처리 없이 `putString()`으로 저장하고 있었다.

```java
public final void setPassword(String value) {
    SharedPreferences sharedPreferences = sharedpreferences;
    if (sharedPreferences == null) {
        Intrinsics.throwUninitializedPropertyAccessException("sharedpreferences");
    }
    sharedPreferences.edit().putString("password", value).apply();
}
```

`putString("password", value)`는 전달된 문자열을 그대로 `SharedPreferences`에 저장한다. 이 과정에서 해시, 암호화, Android Keystore 기반 보호는 확인되지 않았다.

### 5.5 username 평문 저장

`Prefs.setUsername()` 역시 동일한 방식으로 사용자명을 저장하고 있었다.

```java
public final void setUsername(String value) {
    SharedPreferences sharedPreferences = sharedpreferences;
    if (sharedPreferences == null) {
        Intrinsics.throwUninitializedPropertyAccessException("sharedpreferences");
    }
    sharedPreferences.edit().putString("username", value).apply();
}
```

즉 `username`과 `password` 모두 동일한 `Prefs.xml` 파일에 문자열로 저장된다.

### 5.6 실제 저장 결과

동적 검증에서는 앱에 `shopuser / !ns3csh0p` 계정으로 로그인한 뒤, 앱 내부 shared preferences 파일을 확인하였다.

```shell
cat /data/data/com.insecureshop/shared_prefs/Prefs.xml
```

확인 결과 `Prefs.xml`에는 아래와 같은 값이 평문으로 저장되어 있었다.

```xml
<string name="password">!ns3csh0p</string>
<string name="username">shopuser</string>
```

이를 통해 정적 분석에서 확인한 `putString()` 저장 흐름이 실제 파일 저장 결과로 이어지는 것을 검증하였다.

## 6. 영향

이 취약점은 단독으로는 앱 샌드박스 보호에 의해 외부 앱이 즉시 파일을 읽지 못할 수 있다. 그러나 민감정보가 암호화 없이 로컬 파일에 저장되어 있기 때문에, 다른 취약점이나 환경 조건과 결합될 경우 자격증명이 그대로 노출될 수 있다.

실제 위험 시나리오는 다음과 같다.

- 루팅된 단말에서 `Prefs.xml` 직접 접근
- 디버그 가능 앱 또는 테스트 환경에서 `run-as`/shell을 통한 파일 확인
- 백업 또는 파일 추출 경로를 통한 shared preferences 유출
- FileProvider, WebView, 취약한 서드파티 컴포넌트 등 다른 취약점과 결합된 파일 탈취
- 단말 분실 또는 악성 코드에 의한 로컬 저장소 분석

특히 이 프로젝트의 다른 항목들에서 `Prefs.xml` 파일이 여러 경로로 외부에 노출될 수 있음을 확인했기 때문에, 평문 저장 문제는 단순한 구현상 약점이 아니라 실제 자격증명 유출 위험으로 연결된다.

## 7. 대응 방안

- 비밀번호를 로컬에 평문으로 저장하지 않아야 한다.
- 로그인 세션 유지가 필요한 경우 비밀번호 대신 서버에서 발급한 제한된 범위의 토큰을 저장해야 한다.
- 민감한 로컬 값은 Android Keystore 기반 암호화 저장소를 사용해 보호해야 한다.
- `SharedPreferences`에 민감정보를 저장해야 한다면 `EncryptedSharedPreferences` 사용을 검토해야 한다.
- 인증 정보는 저장 전 암호화하고, 암호화 키는 앱 코드나 리소스에 하드코딩하지 않아야 한다.
- 로그아웃 시 저장된 인증 관련 값을 안전하게 삭제해야 한다.
- 앱 내부 파일 유출로 이어질 수 있는 다른 컴포넌트 취약점도 함께 제거해야 한다.

예시적으로 AndroidX Security Crypto를 사용할 경우 다음과 같이 `EncryptedSharedPreferences`를 적용할 수 있다.

```java
MasterKey masterKey = new MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build();

SharedPreferences securePrefs = EncryptedSharedPreferences.create(
    context,
    "secure_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
);
```

다만 가장 안전한 방향은 비밀번호 자체를 로컬에 저장하지 않는 것이다.

## 8. 결론

`InsecureShop`은 로그인 성공 후 사용자명과 비밀번호를 `Prefs` 클래스에 전달하고, `Prefs`는 이를 `SharedPreferences("Prefs", MODE_PRIVATE)`에 저장한다. `setUsername()`과 `setPassword()` 내부에서는 각각 `putString("username", value)`, `putString("password", value)`를 호출하며, 별도의 암호화나 해시 처리는 존재하지 않았다.

동적 검증 결과 `/data/data/com.insecureshop/shared_prefs/Prefs.xml` 파일에서 `shopuser`와 `!ns3csh0p` 값이 평문으로 확인되었다.

따라서 이번 항목은 **사용자 자격증명을 암호화 없이 로컬 SharedPreferences에 저장하는 Insecure Data Storage 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. LoginActivity 식별

![LoginActivity Manifest 확인](../images/18-Insecure%20Data%20Storage/01-loginactivity-manifest.png)

Manifest에서 `com.insecureshop.LoginActivity`가 로그인 화면 Activity로 선언되어 있음을 확인하였다.

### 2. 로그인 성공 후 Prefs 저장 호출 확인

![LoginActivity에서 Prefs 저장 호출 확인](../images/18-Insecure%20Data%20Storage/02-loginactivity-save-prefs.png)

`LoginActivity`는 인증 성공 시 `Prefs.getInstance(...).setUsername(username)`와 `Prefs.getInstance(...).setPassword(password)`를 호출한다. 이 흐름을 통해 입력된 자격증명이 로컬 저장 로직으로 전달된다.

### 3. SharedPreferences 사용 확인

![Prefs에서 SharedPreferences 사용 확인](../images/18-Insecure%20Data%20Storage/03-prefs-sharedpreferences.png)

`Prefs.getInstance()`는 `context.getSharedPreferences("Prefs", 0)`를 호출한다. 이로 인해 앱 내부 shared preferences 경로에 `Prefs.xml` 파일이 생성된다.

### 4. setPassword에서 password 평문 저장 확인

![setPassword putString 확인](../images/18-Insecure%20Data%20Storage/05-setpassword-putstring.png)

`setPassword()`는 전달받은 값을 `putString("password", value)`로 저장한다. 암호화나 해시 처리는 확인되지 않았다.

### 5. setUsername에서 username 평문 저장 확인

![setUsername putString 확인](../images/18-Insecure%20Data%20Storage/06-setusername-putstring.png)

`setUsername()`도 동일하게 `putString("username", value)`를 사용해 사용자명을 그대로 저장한다.

### 6. 로그인 화면에서 계정 입력

![로그인 화면 계정 입력](../images/18-Insecure%20Data%20Storage/04-login-input-credentials.png)

동적 검증을 위해 로그인 화면에서 `shopuser / !ns3csh0p` 값을 입력하였다. 이후 로그인 성공 시 해당 값이 `Prefs`에 저장되는지 확인하였다.

### 7. Prefs.xml 평문 저장 확인

![Prefs.xml 평문 저장 확인](../images/18-Insecure%20Data%20Storage/07-prefs-xml-plaintext.png)

`/data/data/com.insecureshop/shared_prefs/Prefs.xml` 파일을 확인한 결과, `password`와 `username` 값이 XML에 평문으로 저장되어 있었다. 이를 통해 앱이 사용자 자격증명을 암호화 없이 로컬에 저장한다는 점을 동적으로 검증하였다.

## 10. 참고

- Android Developers - SharedPreferences
- Android Developers - Security tips
- AndroidX Security - EncryptedSharedPreferences
