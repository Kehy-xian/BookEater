# 몬스터 이미지 교체 가이드

몬스터 원화와 애니메이션은 독서기록·유전정보·진화 로직과 분리되어 있습니다. 그림을
바꾸어도 저장 데이터나 진화 트리는 바뀌지 않으며, 완성된 프레임 묶음만 앱이 읽습니다.

## 개발 중 시험 교체 위치

설치 폴더의 `_internal/resources/sprites`는 업데이트 때 덮어써질 수 있으므로 직접 수정하지
마세요. 일반 이용자에게는 이미지 교체 기능을 노출하지 않습니다. 개발자가 자기 PC에서만
비교할 때 다음 폴더를 직접 사용합니다.

```text
%LOCALAPPDATA%\BookEater\art_overrides
```

개발 저장소에서 검증·설치 도구를 쓰면 새 묶음을 먼저 검사한 뒤 이 폴더에 원자적으로
활성화합니다. 실패한 묶음은 현재 그림을 망가뜨리지 않습니다.

## 파일 규격

- 파일 형식: PNG, 8-bit RGBA
- 캔버스: 정확히 190×190 px
- 배경: 완전 투명. 흰 배경이나 체크무늬를 그림에 포함하지 않음
- Windows 테두리 번짐 방지: 경계와 그림자 알파는 가능하면 완전 투명(0) 또는 완전 불투명(255) 사용
- 위치: 모든 프레임에서 발 바닥과 중심축을 같은 좌표에 맞춤
- 여백: 귀·꼬리·점프가 190×190 밖으로 잘리지 않도록 모든 프레임에 동일하게 확보
- 프레임 번호: 0부터 시작하는 두 자리 숫자 (`00`, `01`, ...)

기본 종의 파일 접두사는 `paperling`입니다. 예를 들어 대기 4장은 다음 이름입니다.

```text
paperling_idle_00.png
paperling_idle_01.png
paperling_idle_02.png
paperling_idle_03.png
```

## 동작별 파일 수

| 상태 | 의미 | 장수 | 재생 속도 |
|---|---|---:|---:|
| `idle` | 기본 숨쉬기 | 4 | 장당 420ms |
| `eat` | 독서 기록 먹기 | 6 | 장당 115ms |
| `walk` | 걷기 | 4 | 장당 130ms |
| `read` | 읽기 | 3 | 장당 220ms |
| `sleep` | 잠자기 | 3 | 장당 420ms |
| `talk` | 말하기 | 2 | 장당 180ms |
| `spit_memory` | 기억 뱉기 | 4 | 장당 145ms |
| `snack` | 간식 먹기 | 6 | 장당 120ms |
| `delicious` | 맛있는 표정 | 3 | 장당 260ms |
| `play` | 놀기 | 4 | 장당 150ms |
| `wash` | 씻기 | 4 | 장당 190ms |
| `bump` | 화면 끝/착지 충돌 | 3 | 장당 130ms |
| `drop` | 낙하 | 2 | 장당 120ms |

한 상태를 바꾸려면 그 상태에 필요한 장수를 모두 제공해야 합니다. 한 장이라도 없거나
손상되면 그 상태 전체만 기존 그림·동작으로 안전하게 되돌아갑니다.

## 자연스러운 숨쉬기 디자인

`idle` 4장은 발과 그림자를 같은 위치에 고정하고 몸통만 다음 순서로 움직이는 것을
권장합니다.

1. `00`: 기준 자세
2. `01`: 몸통 위로 1px, 가로 폭을 아주 조금 넓힘
3. `02`: 몸통 위로 3px, 가슴 부분을 1~2% 부풀림
4. `03`: 몸통 위로 1px, 기준 자세로 돌아가는 중간 모양

캐릭터 전체를 통째로 올리면 공중에 뜨는 것처럼 보입니다. 눈·입·장식은 몸통을 따라가되
발, 접지 그림자, 바닥에 닿은 소품은 움직이지 않는 편이 자연스럽습니다. 프레임 간 윤곽
변화는 1~3px 안으로 제한하고, 첫 장과 마지막 장이 자연스럽게 이어지도록 확인하세요.

## 검증하고 적용하기

교체할 PNG를 임의의 작업 폴더(예: `C:\BookEaterArt\paperling`)에 모은 뒤 BookEater
저장소 루트에서 실행합니다. PowerShell 실행 정책 문제를 피하려고 이 과정은 Python만
사용합니다.

```powershell
python tools\validate_sprite_pack.py C:\BookEaterArt\paperling paperling --states idle,eat,walk,read,sleep,talk,spit_memory,snack,delicious,play,wash,bump,drop
python tools\install_sprite_override.py C:\BookEaterArt\paperling paperling --states idle,eat,walk,read,sleep,talk,spit_memory,snack,delicious,play,wash,bump,drop
```

일부 동작만 바꿀 때는 `--states`에 그 동작만 적습니다. 예를 들어 숨쉬기와 밥 먹기만
바꾸려면 `--states idle,eat`를 사용합니다. `SPRITE_PACK_OK`와
`SPRITE_PACK_INSTALLED`가 차례로 나오면 앱을 완전히 종료한 뒤 다시 실행합니다.

## 진화형 접두사

| 형태 | 파일 접두사 |
|---|---|
| 기본 | `paperling` |
| 1차 A/B/C | `pagedge`, `inknest`, `lantern` |
| 2차 분기 | `route_a1`, `route_a2`, `route_b1`, `route_b2`, `route_c1`, `route_c2` |

아직 확정 원화가 없는 최종 진화형은 가장 가까운 승인 조상의 이미지를 상속합니다. 나중에
최종 진화형 접두사와 원화를 추가해도 기존 사용자의 유전정보와 진화 경로는 그대로 유지할
수 있습니다. 모든 사용자에게 배포할 최종 원화는 검수 후 저장소의 빌드 리소스로 편입하면
되고, 개인 PC에서 비교할 때는 위 사용자 전용 교체 폴더를 사용하면 됩니다.

위쪽 이동의 뒷모습은 별도 방향 프레임 규격을 확정한 뒤 추가합니다. 현재 빌드는 위·아래·
대각선 이동은 지원하지만, 뒷모습 원화가 없을 때 기존 걷기 프레임을 사용합니다.
