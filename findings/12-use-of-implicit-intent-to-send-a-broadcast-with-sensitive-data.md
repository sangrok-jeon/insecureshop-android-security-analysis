# InsecureShop - Use of Implicit Intent to Send a Broadcast with Sensitive Data

## 1. 개요

`InsecureShop`를 분석하던 중 `AboutUsActivity`가 저장된 사용자 자격증명을 암시적 브로드캐스트(`implicit broadcast`)로 외부에 전송하는 구조를 확인하였다. 일반적으로 민감한 데이터는 특정 수신자만 명시한 `explicit intent` 또는 제한된 내부 통신 방식으로 전달해야 하지만, 이 앱은 `username`, `password`를 action 문자열만 포함한 브로드캐스트에 담아 전송하고 있었다.

또한 `AboutUsActivity`는 `android:exported="true"`로 선언되어 있어 외부 앱이 직접 실행할 수 있었다. 사용자가 해당 화면에서 `About InsecureShop` 버튼을 누르면 `onSendData()`가 실행되고, 이 메서드는 `Prefs`에 저장된 `username`, `password`를 `com.insecureshop.action.BROADCAST` 브로드캐스트의 extra로 담아 `sendBroadcast()`로 전송한다.

실제 검증에서는 별도 `PoC App`을 제작해 동일한 action에 대한 `BroadcastReceiver`를 등록한 뒤 `AboutUsActivity`를 실행하고 버튼을 눌렀다. 그 결과 외부 앱이 `shopuser / !ns3csh0p` 자격증명을 그대로 수신하는 것을 확인하였다.

즉 이번 항목은 **민감 정보를 implicit broadcast로 전송하는 구조로 인해, 동일 action을 등록한 제3자 앱이 자격증명을 탈취할 수 있는 취약점**을 검증한 사례다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Use of Implicit Intent to Send a Broadcast with Sensitive Data` |
| 취약점 유형 | 민감 데이터가 포함된 암시적 브로드캐스트 전송 |
| 영향 | 외부 앱이 동일한 action을 등록해 저장된 자격증명을 수신할 수 있음 |
| 분석 도구 | `APK Easy Tool`, `jadx`, `Android Studio`, `nox_adb` |
| 핵심 컴포넌트 | `AboutUsActivity`, `Prefs`, `BroadcastReceiver` |
| 전송 데이터 | `username`, `password` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 정적 분석 | `APK Easy Tool`, `jadx` |
| 동적 검증 | `Android Studio`, `PoC App`, `nox_adb` |
| 검증 대상 액션 | `com.insecureshop.action.BROADCAST` |

## 4. 분석 방법

이번 항목은 앱이 저장된 자격증명을 암시적 브로드캐스트로 외부에 전송하는지를 기준으로 다음 순서로 분석하였다.

1. `AndroidManifest.xml`에서 `AboutUsActivity`가 외부에서 실행 가능한지 확인하였다.
2. `AboutUsActivity.onSendData()`에서 어떤 데이터를 브로드캐스트로 전송하는지 확인하였다.
3. `activity_about_us.xml`에서 버튼 클릭이 어떤 메서드로 연결되는지 확인하였다.
4. 별도 `PoC App`에서 동일 action을 수신하는 `BroadcastReceiver`를 등록하였다.
5. `PoC App`으로 `AboutUsActivity`를 실행한 뒤 버튼을 눌러 브로드캐스트를 발생시키고, 외부 앱이 자격증명을 수신하는지 검증하였다.

## 5. 상세 분석

### 5.1 `AboutUsActivity` 외부 실행 가능 여부 확인

Manifest를 확인한 결과 `AboutUsActivity`는 `android:exported="true"`로 선언되어 있었다.

![AboutUsActivity exported 설정 확인](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/01-aboutus-exported.png)

```xml
<activity
    android:name="com.insecureshop.AboutUsActivity"
    android:exported="true"/>
```

즉 외부 앱이 `AboutUsActivity`를 직접 실행할 수 있는 상태였다. 이 점은 이후 `PoC App`이 해당 화면을 열고 브로드캐스트를 유도할 수 있는 전제가 된다.

### 5.2 `onSendData()`에서 자격증명을 implicit broadcast로 전송

`AboutUsActivity.onSendData()`를 확인한 결과, `Prefs`에서 저장된 `username`과 `password`를 읽은 뒤 `com.insecureshop.action.BROADCAST` action을 갖는 브로드캐스트에 extra로 담아 전송하고 있었다.

![onSendData에서 username/password 브로드캐스트 전송 확인](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/02-onsenddata-broadcast-creds.png)

```java
public final void onSendData(View view) {
    String userName = Prefs.INSTANCE.getUsername();
    String password = Prefs.INSTANCE.getPassword();

    Intent intent = new Intent("com.insecureshop.action.BROADCAST");
    intent.putExtra("username", userName);
    intent.putExtra("password", password);
    sendBroadcast(intent);
}
```

여기서 핵심은 다음과 같다.

- `Prefs.INSTANCE.getUsername()`, `Prefs.INSTANCE.getPassword()`로 민감 정보 조회
- `new Intent("com.insecureshop.action.BROADCAST")`로 특정 action만 지정
- `sendBroadcast(intent)` 호출 시 수신자를 제한하지 않음

즉 이 브로드캐스트는 특정 패키지나 컴포넌트를 지정하지 않는 `implicit broadcast`이며, 동일한 action을 등록한 외부 앱도 수신 가능하다.

### 5.3 버튼 클릭이 `onSendData()`로 연결되는 구조 확인

`activity_about_us.xml`을 확인한 결과 `About InsecureShop` 버튼은 `android:onClick="onSendData"`로 연결되어 있었다.

![activity_about_us.xml의 onClick 연결 확인](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/03-aboutus-button-onclick.png)

```xml
<Button
    android:id="@+id/send_data_to_broadcast"
    android:text="About InsecureShop"
    android:onClick="onSendData" />
```

이 구조는 사용자가 해당 버튼을 누를 때 `AboutUsActivity.onSendData()`가 실행된다는 뜻이다. 따라서 실제 브로드캐스트 전송은 사용자의 UI 동작과 직접 연결되어 있다.

### 5.4 `PoC App` 실행 전 준비 화면

최종 검증을 위해 별도 `PoC App`을 제작하였다. 이 앱은 `com.insecureshop.action.BROADCAST` action에 대한 `BroadcastReceiver`를 등록한 뒤, `AboutUsActivity`를 여는 버튼을 제공한다.

![PoC App 초기 화면](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/04-poc-initial-screen.png)

이 화면에서 `OPEN ABOUTUSACTIVITY` 버튼을 누르면 InsecureShop의 `AboutUsActivity`가 실행된다.

### 5.5 `AboutUsActivity` 버튼 클릭으로 브로드캐스트 발생

PoC 앱에서 `AboutUsActivity`를 실행한 뒤, InsecureShop 화면에서 `About InsecureShop` 버튼을 눌러 브로드캐스트를 발생시켰다.

![InsecureShop AboutUsActivity 화면](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/05-aboutus-runtime-screen.png)

이 버튼 클릭 시 앞서 확인한 `onSendData()`가 실행되며, 저장된 `username`, `password`를 암시적 브로드캐스트로 전송한다.

### 5.6 `PoC App`에서 자격증명 수신 확인

버튼 클릭 이후 PoC 앱 화면에서는 브로드캐스트 수신 결과가 아래와 같이 표시되었다.

![PoC App 화면 - 수신된 자격증명 표시](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/06-poc-ui-received-creds.png)

화면에는 다음 값이 표시되었다.

```text
username = shopuser
password = !ns3csh0p
```

즉 외부 앱이 동일 action을 등록하는 것만으로 InsecureShop가 전송한 자격증명을 수신할 수 있음을 확인하였다.

### 5.7 `logcat` 기반 수신 결과 검증

동일 결과는 `logcat`에서도 확인되었다.

![PoC App logcat - 브로드캐스트 수신 성공](../images/12-Use%20of%20Implicit%20intent%20to%20send%20a%20broadcast%20with%20sensitive%20data/07-logcat-received-creds.png)

로그에서는 다음 흐름이 확인되었다.

- `receiver registered for com.insecureshop.action.BROADCAST`
- `AboutUsActivity launched`
- `received username = shopuser`
- `received password = !ns3csh0p`

또한 동일 로그가 여러 번 반복된 것은 사용자가 `About InsecureShop` 버튼을 여러 차례 눌렀기 때문이며, 버튼 클릭 시마다 동일 브로드캐스트가 반복 전송되는 구조임을 의미한다.

## 6. 영향

이 구조를 악용하면 외부 앱이 별도의 특수 권한 없이도 `InsecureShop`가 전송하는 로그인 자격증명을 수신할 수 있다. 특히 action 문자열만 알면 동일한 `BroadcastReceiver`를 등록해 손쉽게 정보를 탈취할 수 있으므로, 앱 내부에 저장된 민감 정보가 브로드캐스트 IPC를 통해 외부로 노출되는 결과가 발생한다.

실제 서비스 환경에서 동일한 구성이 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 로그인 자격증명이 제3자 앱으로 유출될 수 있음
- 탈취된 자격증명으로 계정 재사용 공격이 가능할 수 있음
- 민감 데이터가 앱 샌드박스 밖으로 전달되어 추가 공격의 기반이 될 수 있음
- 브로드캐스트를 반복 유도할 수 있을 경우 지속적인 자격증명 수집이 가능할 수 있음

이번 검증에서는 저장된 `username`, `password` 수신까지 확인했으며, 추가적인 계정 사용 시도는 수행하지 않았다.

## 7. 대응 방안

- 민감한 데이터는 `implicit broadcast`로 전송하지 않아야 한다.
- 브로드캐스트가 필요한 경우 `setPackage()` 또는 명시적 컴포넌트 지정으로 수신 대상을 제한해야 한다.
- 내부 앱 통신에는 `explicit intent`, `bound service`, `Activity result`, 앱 내부 저장소 참조 등 더 제한적인 방식을 사용해야 한다.
- 자격증명 자체를 브로드캐스트 extra에 담아 전달하는 구조를 제거해야 한다.
- 외부 호출이 필요 없는 Activity는 `android:exported="false"`로 제한해야 한다.
- 민감 정보는 가능하면 메모리 내에서만 처리하고, 불필요한 IPC 경로를 통해 전달하지 않아야 한다.

## 8. 정리

이번 분석에서는 `AboutUsActivity`가 `android:exported="true"`로 외부에 공개되어 있고, `activity_about_us.xml`의 버튼 클릭이 `onSendData()`로 연결되어 있음을 확인하였다. 이어서 `onSendData()`는 `Prefs`에 저장된 `username`, `password`를 읽어 `com.insecureshop.action.BROADCAST` action을 갖는 암시적 브로드캐스트에 담아 `sendBroadcast()`로 전송하고 있음을 확인하였다.

최종적으로 별도 `PoC App`을 제작해 동일 action의 `BroadcastReceiver`를 등록한 뒤 `AboutUsActivity`를 실행하고 버튼을 누르자, 외부 앱이 `shopuser / !ns3csh0p` 자격증명을 그대로 수신하는 데 성공하였다.

따라서 이번 항목은 **민감 정보를 implicit broadcast로 전송함으로써 제3자 앱이 자격증명을 탈취할 수 있는 `Use of Implicit Intent to Send a Broadcast with Sensitive Data` 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

본 항목의 취약점 테스트는 5번 상세 분석에서 정적 근거 확인, `PoC App` 기반 브로드캐스트 수신 검증, `logcat` 기반 자격증명 확인까지 동일한 흐름으로 증적과 함께 다루었다.

따라서 동일한 이미지와 설명의 반복을 피하기 위해 별도의 취약점 테스트 세부 절은 분리하지 않았다.
