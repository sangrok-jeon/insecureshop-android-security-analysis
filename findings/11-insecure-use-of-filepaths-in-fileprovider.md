# InsecureShop - Insecure use of FilePaths in FileProvider

## 1. 개요

`InsecureShop`를 분석하던 중 `androidx.core.content.FileProvider`가 `provider_paths.xml`을 통해 파일시스템 루트(`/`) 전체를 공유 기준 경로로 사용하고 있음을 확인하였다. 일반적으로 `FileProvider`는 앱이 의도한 특정 디렉터리만 외부에 안전하게 공유하도록 설계되지만, 이 앱은 `<root-path name="root" path="/" />` 설정을 사용하고 있어 `/data/data/com.insecureshop/...`와 같은 앱 내부 경로까지 URI로 표현할 수 있는 상태였다.

또한 `com.insecureshop.ResultActivity`는 `android:exported="true"`로 노출되어 있으며, `onCreate`에서 `setResult(-1, getIntent())`를 호출해 외부에서 전달된 `Intent`를 그대로 반환한다. 이 구조는 `FileProvider`의 `grantUriPermissions="true"` 설정과 결합될 경우 외부 앱이 `content://com.insecureshop.file_provider/...` URI에 대한 읽기 권한을 획득하는 중계점으로 악용될 수 있다.

## 2. 취약점 요약

| 항목 | 내용 |
|---|---|
| 취약점명 | `Insecure use of FilePaths in FileProvider` |
| 취약점 유형 | 과도한 `FileProvider` 경로 설정과 URI 권한 중계 |
| 영향 | 외부 앱이 앱 내부 파일 URI에 대한 읽기 권한을 획득해 민감 파일을 읽을 수 있음 |
| 분석 도구 | `jadx`, `Android Studio`, `adb` |
| 핵심 컴포넌트 | `FileProvider`, `provider_paths.xml`, `ResultActivity` |
| 검증 대상 파일 | `/data/data/com.insecureshop/shared_prefs/Prefs.xml` |

## 3. 분석 환경

| 항목 | 내용 |
|---|---|
| 대상 앱 | `InsecureShop` |
| 실행 환경 | `Nox` |
| 운영체제 | `Android` |
| 정적 분석 | `jadx` |
| 동적 검증 | `Android Studio`, `PoC App`, `adb` |
| 검증 대상 컴포넌트 | `androidx.core.content.FileProvider`, `com.insecureshop.ResultActivity` |

## 4. 분석 방법

이번 항목은 앱 내부 파일을 가리키는 `content://` URI가 실제로 외부 앱으로 전달되고 읽힐 수 있는가를 기준으로 다음 순서로 분석하였다.

1. `AndroidManifest.xml`에서 `FileProvider` 선언과 `ResultActivity` 공개 여부를 확인하였다.
2. `provider_paths.xml`에서 `FileProvider`가 어떤 경로를 공유 대상으로 삼는지 확인하였다.
3. `androidx.core.content.FileProvider` 구현을 분석해 `root-path`가 실제로 `/`에 매핑되는지, 그리고 해당 URI가 실제 파일로 열리는지 확인하였다.
4. `ResultActivity`가 외부 입력 `Intent`를 그대로 `setResult`로 반환하는지 확인하였다.
5. `adb shell am start`로 공격용 URI와 `FLAG_GRANT_READ_URI_PERMISSION`를 포함한 Intent가 전달되는지 1차 확인하였다.
6. 마지막으로 `PoC App`을 제작하여 반환된 URI를 실제로 읽고, 앱 내부 `Prefs.xml` 내용이 외부 앱 로그로 출력되는지 검증하였다.

## 5. 상세 분석

### 5.1 FileProvider 선언

Manifest를 확인한 결과 `InsecureShop`는 `androidx.core.content.FileProvider`를 사용하고 있었고, authority는 `com.insecureshop.file_provider`로 설정되어 있었다. 또한 `grantUriPermissions="true"`가 활성화되어 있어 앱이 특정 URI 권한을 다른 앱에 전달할 수 있는 상태였다.

```xml
<provider
    android:name="androidx.core.content.FileProvider"
    android:exported="false"
    android:authorities="com.insecureshop.file_provider"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/provider_paths" />
</provider>
```

`FileProvider` 자체는 `exported=false`이므로 외부 앱이 직접 광범위하게 접근하는 구조는 아니지만, 이후 확인한 `ResultActivity`와 결합되면 URI 권한이 외부 앱으로 전달될 수 있다.

### 5.2 `provider_paths.xml`의 `root-path` 설정

Manifest에서 참조하는 `provider_paths.xml`을 확인한 결과, 아래와 같이 `root-path`가 `/`로 설정되어 있었다.

```xml
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <root-path name="root" path="/" />
</paths>
```

이 설정은 `FileProvider`가 앱 내부 특정 디렉터리만이 아니라 파일시스템 루트(`/`) 전체를 기준 경로로 사용한다는 뜻이다. 따라서 아래와 같은 URI도 구성 가능하다.

```text
content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml
```

안전한 구성에서는 일반적으로 `files-path`, `cache-path` 등 특정 앱 디렉터리만 제한적으로 열어두어야 한다. 반면 이 앱은 `/` 전체를 열어두고 있어 경로 범위가 과도하게 넓다.

### 5.3 `FileProvider`가 실제 파일 경로로 해석하는 방식

`FileProvider` 구현을 확인한 결과, `parsePathStrategy()`에서 `root-path` 태그를 만나면 `DEVICE_ROOT`를 사용하도록 구현되어 있었다.

```java
if (TAG_ROOT_PATH.equals(tag)) {
    target = DEVICE_ROOT;
}
```

여기서 `DEVICE_ROOT`는 `/`를 의미한다. 즉 `provider_paths.xml`의 `<root-path name="root" path="/" />`는 실제 코드 수준에서도 파일시스템 루트 전체를 허용하는 설정으로 반영된다.

이후 `getFileForUri()`는 URI에서 `tag`와 `path`를 분리하고, 해당 root를 기준으로 실제 파일 경로를 만든다.

```java
File root = this.mRoots.get(tag);
File file = new File(root, path2);
File file2 = file.getCanonicalFile();
if (file2.getPath().startsWith(root.getPath())) {
    return file2;
}
```

이 검사는 configured root 밖으로 벗어나는지만 확인한다. 그런데 configured root 자체가 `/`이므로 `/data/data/com.insecureshop/shared_prefs/Prefs.xml`도 조건을 통과한다.

### 5.4 `openFile()`과 `query()`를 통한 파일 접근 가능성

`FileProvider`는 `getFileForUri()`로 해석한 경로를 기반으로 실제 파일을 연다.

```java
public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
    File file = this.mStrategy.getFileForUri(uri);
    int fileMode = modeToMode(mode);
    return ParcelFileDescriptor.open(file, fileMode);
}
```

또한 `query()`는 같은 URI를 실제 파일로 해석한 뒤 `_display_name`, `_size`와 같은 메타데이터를 반환한다. 이 흐름은 `content://com.insecureshop.file_provider/...` URI가 실제 파일 객체로 해석되고 파일 열기까지 이어질 수 있음을 보여준다.

### 5.5 `ResultActivity`를 통한 URI 권한 중계

이 취약점이 실제 외부 앱 공격으로 이어지려면, `FileProvider` URI에 대한 읽기 권한이 외부 앱으로 전달되어야 한다. 이를 위해 `ResultActivity`를 확인한 결과, Manifest에서 `android:exported="true"`로 선언되어 있었다.

그리고 `ResultActivity`의 구현은 아래와 같았다.

```java
@Override
protected void onCreate(Bundle savedInstanceState) {
    super.onCreate(savedInstanceState);
    setResult(-1, getIntent());
    finish();
}
```

이 코드는 외부 앱이 전달한 `Intent`를 아무 검증 없이 그대로 `RESULT_OK`로 반환한다는 뜻이다. 따라서 공격자가 `content://com.insecureshop.file_provider/...` URI와 `FLAG_GRANT_READ_URI_PERMISSION`를 실어 보내면, `ResultActivity`는 그 `Intent`를 그대로 돌려주는 중계점으로 동작할 수 있다.

## 6. 영향

이 구조를 악용하면 별도의 루트 권한 없이도 외부 앱이 `InsecureShop` 내부 파일을 읽을 수 있다. 실제 검증에서는 `Prefs.xml`이 대상이었지만, 동일한 방식으로 `/` 아래의 다른 경로를 가리키는 URI를 구성할 수 있으므로 추가적인 민감 파일 노출 가능성도 존재한다.

실제 서비스 환경에서 동일한 구성이 존재할 경우 다음과 같은 문제가 발생할 수 있다.

- 앱 내부 `shared_prefs`, 캐시, 파일 저장소 등 민감 데이터가 외부 앱에 노출될 수 있음
- 사용자 계정 정보, 토큰, 설정값, 캐시된 응답 등이 탈취될 수 있음
- 노출된 정보가 다른 취약점과 결합되어 계정 탈취나 추가 권한 상승으로 이어질 수 있음
- 앱 샌드박스 경계가 `content://` URI 권한 중계로 우회될 수 있음

이번 검증에서는 `Prefs.xml` 읽기까지 확인했으며, 불필요한 파일 삭제나 쓰기 테스트는 수행하지 않았다.

## 7. 대응 방안

- `provider_paths.xml`에서 `<root-path path="/" />`와 같은 과도한 범위 설정을 제거해야 한다.
- `FileProvider`는 `files-path`, `cache-path`, `external-files-path` 등 필요한 디렉터리만 최소 범위로 제한해야 한다.
- 앱 내부 민감 파일이 포함된 디렉터리는 `FileProvider` 공유 범위에서 제외해야 한다.
- `ResultActivity`처럼 외부 입력 `Intent`를 그대로 `setResult`로 반환하는 구조를 제거하거나, 반환 전 data/flags/clipData를 검증해야 한다.
- 외부 호출이 필요 없는 Activity는 `android:exported="false"`로 변경해야 한다.
- URI grant가 필요한 경우에도 allowlist 기반으로 대상 authority와 경로를 검증한 뒤 제한적으로 권한을 부여해야 한다.

## 8. 정리

이번 분석에서는 `InsecureShop`의 `FileProvider`가 `provider_paths.xml`에서 `<root-path name="root" path="/" />`를 사용하고 있어 파일시스템 루트 전체를 공유 범위로 삼고 있음을 확인하였다. 이어서 `FileProvider` 구현 분석을 통해 이 설정이 실제로 `DEVICE_ROOT`에 매핑되고, `getFileForUri()`와 `openFile()`를 통해 실제 파일 경로 해석과 파일 열기로 이어진다는 점을 확인하였다.

또한 `ResultActivity`가 외부에서 전달된 `Intent`를 검증 없이 그대로 `setResult(-1, getIntent())`로 반환하는 구조를 확인하였다. 최종적으로 별도 `PoC App`을 제작해 `content://com.insecureshop.file_provider/root/data/data/com.insecureshop/shared_prefs/Prefs.xml` URI를 전달하고, 반환된 URI를 통해 `Prefs.xml`의 `username`, `password` 값을 읽는 데 성공하였다.

따라서 11번 항목은 **과도하게 넓은 FileProvider 경로 설정과 URI 권한 중계 구조가 결합되어 앱 내부 파일 유출로 이어지는 `Insecure use of FilePaths in FileProvider` 취약점**으로 정리할 수 있다.

## 9. 취약점 테스트

### 1. FileProvider Manifest 선언 확인

![FileProvider Manifest 선언 확인](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2011%2052%2028.png)

`FileProvider`는 `com.insecureshop.file_provider` authority를 사용하고 있었고, `grantUriPermissions="true"`가 설정되어 있었다.

### 2. provider_paths.xml의 root-path 설정 확인

![provider_paths.xml의 root-path 설정 확인](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2013%2023%2008.png)

`provider_paths.xml`에서 `<root-path name="root" path="/" />` 설정을 확인하였다. 이 설정은 파일시스템 루트 전체를 공유 기준 경로로 삼는다는 의미다.

### 3. FileProvider 내부 경로 해석 확인

![attachInfo에서 grantUriPermissions 확인](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2013%2032%2001.png)

![parsePathStrategy에서 TAG_ROOT_PATH를 DEVICE_ROOT로 매핑](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2013%2043%2025.png)

`FileProvider`는 `root-path`를 `DEVICE_ROOT`로 매핑하고, URI를 실제 파일 경로로 해석한다.

### 4. openFile 및 query 동작 확인

![openFile에서 getFileForUri 결과를 실제 파일로 여는 코드](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2014%2009%2035.png)

![query에서 파일 메타데이터를 반환하는 코드](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2014%2010%2020.png)

`openFile()`은 `getFileForUri()` 결과를 실제 파일로 열고, `query()`는 파일명과 크기 같은 메타데이터를 반환할 수 있다.

### 5. ResultActivity를 통한 URI 권한 중계 확인

![ResultActivity exported 설정 확인](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2014%2035%2044.png)

`ResultActivity`는 `exported=true`이며, 입력 Intent를 그대로 `setResult(-1, getIntent())`로 반환하는 구조였다.

### 6. am start로 공격용 URI 전달 확인

![am start로 ResultActivity에 공격용 URI 전달](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2014%2048%2052.png)

`adb shell am start`로 `ResultActivity`에 `content://com.insecureshop.file_provider/.../Prefs.xml` URI와 read grant flag를 전달할 수 있음을 확인하였다.

### 7. PoC App으로 실제 파일 읽기 확인

![PoC App logcat - 반환된 URI와 파일 읽기 시작 확인](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2014%2057%2059.png)

![PoC App logcat - Prefs.xml 내용과 종료 지점 확인](../images/11-Insecure%20use%20of%20FilePaths%20in%20FileProvider/2026-04-15%2014%2058%2010.png)

PoC 앱은 반환된 URI를 `openInputStream()`으로 읽었고, `Prefs.xml` 내부의 `username`, `password` 값을 확인하였다.
