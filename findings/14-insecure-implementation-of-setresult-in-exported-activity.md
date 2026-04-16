# InsecureShop - Insecure Implementation of SetResult in Exported Activity

## 1. 개요

`InsecureShop`를 분석하던 중 `ResultActivity`가 외부에서 실행 가능한 상태로 공개되어 있고, 실행 즉시 호출자가 전달한 `Intent`를 아무 검증 없이 그대로 `setResult()`로 반환하는 구조를 확인하였다.

일반적으로 `Activity`가 결과를 반환할 때는 필요한 데이터만 선별해 새 `Intent`에 담아 반환해야 한다. 그러나 이 앱의 `ResultActivity`는 `setResult(-1, getIntent())`를 호출해 외부에서 들어온 `Intent` 전체를 그대로 호출자에게 되돌려준다.

이 구조는 `content://` URI와 `FLAG_GRANT_READ_URI_PERMISSION` 같은 URI permission flag가 포함된 경우 문제가 된다. 공격 앱이 `ResultActivity`에 특정 `content://` URI를 포함한 `Intent`를 전달하면, `ResultActivity`는 이를 검증하지 않고 그대로 result Intent로 반환한다. 그 결과 호출자는 반환된 URI를 사용해 `ContentResolver`로 접근을 시도할 수 있다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insecure Implementation of SetResult in Exported Activity` |
| 취약점 유형 | 부적절한 `setResult()` 구현을 통한 URI permission 중계 |
| 영향 | 외부 앱이 `content://` URI를 result Intent로 돌려받아 민감 리소스에 접근할 수 있음 |
| 분석 도구 | `jadx`, `Android Studio`, `adb` |
| 핵심 컴포넌트 | `ResultActivity`, `FileProvider` |
| 검증 URI | `content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `jadx` |
| 동적 검증 | `Android Studio`, `PoC App`, `adb` |
| 검증 대상 컴포넌트 | `com.insecureshop.ResultActivity` |

## 4. 분석 방법

이번 항목은 `ResultActivity`가 외부 입력 Intent를 안전하게 처리하는지 확인하기 위해 다음 순서로 분석하였다.

1. `AndroidManifest.xml`에서 `ResultActivity`가 외부에서 실행 가능한지 확인하였다.
2. `ResultActivity.onCreate()`에서 결과 Intent를 어떻게 반환하는지 확인하였다.
3. `content://` URI와 read grant flag를 포함한 Intent를 구성하였다.
4. 별도 `PoC App`에서 `ResultActivity`를 `startActivityForResult()`로 호출하였다.
5. 반환된 result Intent에서 URI를 추출하였다.
6. `ContentResolver.openInputStream()`으로 반환 URI를 열어 파일 내용을 읽을 수 있는지 검증하였다.

## 5. 상세 분석

### 5.1 `ResultActivity` 외부 실행 가능 여부

Manifest를 확인한 결과 `ResultActivity`는 `android:exported="true"`로 선언되어 있었다.

```xml
<activity
    android:name="com.insecureshop.ResultActivity"
    android:exported="true"/>
```

즉 외부 앱이 `ResultActivity`를 직접 실행할 수 있는 상태였다. 이 점은 공격 앱이 임의의 `Intent`를 전달할 수 있는 전제가 된다.

### 5.2 `setResult(-1, getIntent())` 구현

`ResultActivity.onCreate()`를 확인한 결과, Activity가 시작되자마자 `getIntent()`로 받은 입력 Intent를 그대로 `setResult()`의 결과 Intent로 사용하고 있었다.

```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setResult(-1, getIntent());
    finish();
}
```

여기서 `-1`은 `Activity.RESULT_OK`를 의미한다. 즉 이 코드는 호출자가 전달한 Intent를 검증하거나 필요한 데이터만 선별하지 않고, 그대로 성공 결과로 반환한다.

문제는 입력 Intent에 다음과 같은 값이 포함될 수 있다는 점이다.

- `content://` URI
- `FLAG_GRANT_READ_URI_PERMISSION`
- `FLAG_GRANT_WRITE_URI_PERMISSION`
- `ClipData`
- 민감한 extra 데이터

따라서 이 Activity는 의도하지 않게 URI permission을 호출자에게 되돌려주는 중계 지점으로 동작할 수 있다.

### 5.3 11번 항목과의 차이

이번 항목은 11번 `Insecure use of FilePaths in FileProvider`와 PoC 대상 URI가 유사하다. 그러나 분석 초점은 다르다.

11번은 `provider_paths.xml`의 `<root-path name="root" path="/" />` 설정 때문에 `FileProvider`가 파일시스템 루트(`/`) 전체를 공유 기준으로 삼는 문제에 초점을 둔다. 즉 내부 파일 경로가 과도하게 넓은 범위로 URI화될 수 있다는 점이 핵심이다.

반면 14번은 `ResultActivity`의 `setResult(-1, getIntent())` 구현 자체에 초점을 둔다. 외부 앱이 전달한 `Intent`를 아무 검증 없이 그대로 반환하기 때문에, `content://` URI와 권한 플래그가 포함된 Intent가 result 형태로 되돌아오며 호출자가 이를 사용할 수 있게 된다.

따라서 이번 PoC에서 동일한 `Prefs.xml` URI를 사용하더라도, 검증 목적은 `FileProvider` 경로 설정이 아니라 **`ResultActivity`가 URI를 result Intent로 중계하는지**를 확인하는 것이다.

### 5.4 공격 흐름

PoC 앱은 다음 URI를 대상으로 사용하였다.

```text
content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml
```

PoC 앱은 이 URI를 `Intent.setData()`와 `ClipData`에 설정하고, `FLAG_GRANT_READ_URI_PERMISSION`을 추가한 뒤 `com.insecureshop.ResultActivity`를 `startActivityForResult()`로 실행한다.

동작 흐름은 다음과 같다.

1. PoC 앱이 `content://.../Prefs.xml` URI 생성
2. `FLAG_GRANT_READ_URI_PERMISSION` 포함
3. `com.insecureshop.ResultActivity` 실행
4. `ResultActivity`가 `setResult(-1, getIntent())`로 동일 Intent 반환
5. PoC 앱이 `onActivityResult()`에서 반환 URI 수신
6. `ContentResolver.openInputStream()`으로 파일 내용 읽기

## 6. 영향

이 취약점을 악용하면 외부 앱이 `ResultActivity`를 URI permission 중계 지점으로 사용할 수 있다. 특히 입력 Intent의 data, flags, clipData를 검증하지 않고 그대로 result로 반환하기 때문에, 호출자는 반환된 URI를 통해 민감 리소스 접근을 시도할 수 있다.

실제 서비스 환경에서 동일한 구조가 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 외부 앱이 내부 파일 또는 Content Provider URI 접근 권한을 획득할 수 있음
- `content://` URI를 통해 민감 파일, 설정값, 캐시 데이터가 노출될 수 있음
- `ClipData`나 unsafe flag가 그대로 반환되어 예상하지 못한 URI permission 전파가 발생할 수 있음
- 다른 취약한 Provider 설정과 결합될 경우 데이터 유출 범위가 확대될 수 있음

이번 검증에서는 `Prefs.xml` 파일 읽기까지 확인했으며, 추가적인 파일 쓰기 또는 데이터 변조 시도는 수행하지 않았다.

## 7. 대응 방안

- 외부에서 실행 가능한 Activity에서 입력 Intent를 그대로 `setResult()`로 반환하지 않아야 한다.
- 결과를 반환해야 하는 경우 새 `Intent`를 생성하고 필요한 값만 선별해 담아야 한다.
- 입력 Intent의 `data`, `flags`, `clipData`는 제거하거나 안전한 값으로 재구성해야 한다.
- 외부 호출이 필요 없는 Activity는 `android:exported="false"`로 설정해야 한다.
- URI permission flag가 포함된 Intent를 처리할 때는 대상 authority, scheme, path를 allowlist 기반으로 검증해야 한다.
- `FLAG_GRANT_READ_URI_PERMISSION`, `FLAG_GRANT_WRITE_URI_PERMISSION`이 불필요하게 전달되지 않도록 명시적으로 제거해야 한다.

안전한 형태는 다음과 같다.

```java
Intent result = new Intent();
result.putExtra("safe_key", safeValue);
setResult(Activity.RESULT_OK, result);
finish();
```

이처럼 호출자가 전달한 Intent 전체를 재사용하지 않고, 반환해야 하는 최소 데이터만 새 Intent에 담아야 한다.

## 8. 정리

이번 분석에서는 `ResultActivity`가 `android:exported="true"`로 외부에 공개되어 있고, `onCreate()`에서 `setResult(-1, getIntent())`를 호출해 외부에서 전달된 Intent를 그대로 결과로 반환하는 구조를 확인하였다.

최종적으로 별도 `PoC App`을 제작해 `content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml` URI와 read grant flag를 포함한 Intent로 `ResultActivity`를 실행하였다. 그 결과 PoC 앱은 `onActivityResult()`에서 동일 URI를 반환받았고, `ContentResolver.openInputStream()`을 통해 `Prefs.xml` 내용을 읽는 데 성공하였다.

따라서 이번 항목은 **exported Activity의 부적절한 `setResult()` 구현으로 인해 외부 앱이 URI 접근 권한을 중계받을 수 있는 `Insecure Implementation of SetResult in Exported Activity` 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. ResultActivity exported 설정 확인

![ResultActivity exported 설정 확인](../images/14-Insecure%20Implementation%20of%20SetResult%20in%20exported%20Activity/01-resultactivity-exported.png)

`ResultActivity`는 `android:exported="true"`로 선언되어 있어 외부 앱이 직접 실행할 수 있었다.

### 2. setResult 구현 확인

![ResultActivity setResult 구현 확인](../images/14-Insecure%20Implementation%20of%20SetResult%20in%20exported%20Activity/02-resultactivity-setresult.png)

`ResultActivity`는 `setResult(-1, getIntent())`를 호출해 입력 Intent를 그대로 결과 Intent로 반환한다.

### 3. PoC 앱 화면에서 반환 URI 및 파일 내용 확인

![PoC App 화면 - 반환 URI 및 Prefs.xml 내용 확인](../images/14-Insecure%20Implementation%20of%20SetResult%20in%20exported%20Activity/03-poc-ui-result.png)

PoC 앱은 `ResultActivity`로부터 반환된 URI를 받아 `Prefs.xml` 내용을 화면에 출력하였다. 반환 URI와 파일 내용이 함께 표시되므로, result Intent를 통한 URI 중계가 실제 파일 접근으로 이어졌음을 확인할 수 있다.

### 4. adb logcat 기반 검증 결과

![PoC App logcat - 반환 URI 및 파일 내용 확인](../images/14-Insecure%20Implementation%20of%20SetResult%20in%20exported%20Activity/04-logcat-result-poc.png)

cmd에서 `adb logcat`으로도 다음 흐름을 확인하였다.

```text
D RESULT_POC: targetUri = content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml
D RESULT_POC: launching ResultActivity
D RESULT_POC: onActivityResult requestCode=1400, resultCode=-1
D RESULT_POC: returnedUri = content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml
D RESULT_POC: === FILE CONTENT START ===
```

로그에는 `password` 값 등 `Prefs.xml` 내용이 포함되어 있었고, 이를 통해 외부 앱이 `ResultActivity`를 통해 URI를 되돌려받아 민감 파일을 읽는 데 성공했음을 검증하였다.
