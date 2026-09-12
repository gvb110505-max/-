# Strukt — Shopify 섹션 세트

Claude Design 의 `Storefront.dc.html` (Modernist 디자인 시스템) 을 Shopify 테마 섹션으로 옮긴 것입니다.
기존 테마(Dawn 등)에 **파일만 추가**하면 되고, 테마 전체를 교체하지 않습니다.

---

## 파일 구성

```
assets/
  strukt.css                  디자인 토큰 + 전 컴포넌트 스타일 (.strukt 로 스코프)
  strukt.js                   카테고리 필터 · AJAX 장바구니 · 드로어 · 옵션 선택 · 토스트
sections/
  header-group.json           (선택) 헤더 그룹 — 기존 테마 헤더를 Strukt 로 교체
  footer-group.json           (선택) 푸터 그룹 — 푸터 + 장바구니 드로어 포함
  strukt-announcement.liquid  상단 공지 바
  strukt-header.liquid        스티키 헤더 + 팔레트 설정(색상은 여기서 관리)
  strukt-hero.liquid          히어로 (7:5 분할)
  strukt-promises.liquid      숫자 4칸 스트립
  strukt-catalogue.liquid     상품 그리드 + 타입 필터
  strukt-editorial.liquid     에디토리얼 (5:7 분할)
  strukt-archive.liquid       과거 생산분 테이블
  strukt-newsletter.liquid    액센트 밴드 + 구독 폼
  strukt-footer.liquid        4단 푸터
  strukt-product.liquid       상품 상세 (옵션 세그먼트 · 수량 · 스펙)
  strukt-cart-drawer.liquid   슬라이드인 장바구니
snippets/
  strukt-product-card.liquid  카탈로그 카드 1장
templates/
  index.json                  홈 조립 예시
  product.json                상품 페이지 조립 예시
```

---

## 설치

### 방법 A — 관리자에서 직접 (CLI 없이)

1. **Online Store → Themes → ⋯ → Edit code**
2. 위 구조 그대로 파일을 추가합니다.
   - `Assets → Add a new asset` 로 `strukt.css`, `strukt.js`
   - `Sections → Add a new section` 으로 `strukt-*.liquid` (이름 입력 시 `.liquid` 는 자동)
   - `Snippets → Add a new snippet` 으로 `strukt-product-card.liquid`
   - 새 섹션 생성 시 Shopify 가 기본 뼈대를 넣어주므로, **전체를 지우고** 이 저장소 내용을 붙여넣으세요.
3. 장바구니 드로어를 모든 페이지에 한 번 올립니다. 둘 중 하나를 선택하세요.

   - **A. 푸터 그룹 사용(권장)** — `sections/footer-group.json` 을 올리면 드로어가 포함되어 있어
     `theme.liquid` 을 건드리지 않아도 됩니다. 단, 이 파일은 **기존 테마의 푸터를 교체**합니다.
   - **B. 레이아웃에 직접 추가** — `layout/theme.liquid` 의 `</body>` 바로 위에:

     ```liquid
     {% section 'strukt-cart-drawer' %}
     ```

   > 어느 쪽이든 섹션 ID 가 `strukt-cart-drawer` 여야 합니다. 드로어는
   > `?section_id=strukt-cart-drawer` 로 다시 그려지므로, 이름을 바꾸면
   > `assets/strukt.js` 상단의 `DRAWER_SECTION` 값도 같이 바꿔야 합니다.

   `sections/header-group.json` / `footer-group.json` 은 **선택 사항**입니다.
   올리면 기존 테마(Horizon 등)의 헤더·푸터가 Strukt 것으로 대체됩니다.
   기존 헤더를 유지하려면 이 두 파일은 올리지 마세요.
4. **Customize** 에서 원하는 페이지에 `Strukt ...` 섹션을 추가합니다.
   (`templates/index.json` 을 그대로 붙여넣으면 홈 전체가 한 번에 구성됩니다.)

### 방법 B — Shopify CLI

```bash
shopify theme dev   --store ba9tpb-1g.myshopify.com   # 미리보기
shopify theme push  --store ba9tpb-1g.myshopify.com \
  --only assets/strukt.css \
  --only assets/strukt.js \
  --only "sections/strukt-*.liquid" \
  --only snippets/strukt-product-card.liquid
```

`templates/*.json` 은 기존 홈/상품 페이지를 덮어쓰므로, 확인 후 별도로 push 하세요.

---

## 커스터마이저에서 바꿀 수 있는 것

| 항목 | 위치 |
| --- | --- |
| 배경 · 텍스트 · 액센트 색 | **Strukt header** 섹션의 *Palette* (페이지 전체 Strukt 섹션에 적용) |
| 모든 문구 · 버튼 · 링크 | 각 섹션 설정 |
| 히어로 / 에디토리얼 이미지, 비율, 흑백 처리 | 해당 섹션 설정 |
| 상품 출처 컬렉션, 노출 개수, 필터 on/off | **Strukt catalogue** |
| 재고 임박 기준(기본 3개) | **Strukt catalogue → Low stock threshold** |
| 무료배송 기준액 | **Strukt cart drawer → Free shipping over** (기본 ₩150,000) |
| 스펙 행(원단/생산지/관리법) | **Strukt product** 의 블록 |

---

## 디자인 원본과 달라진 점 (의도된 것)

- **가격**: 디자인의 `$268` 고정값 대신 `{{ product.price | money }}` — 스토어 통화(KRW)로 출력됩니다.
- **재고 문구**: 하드코딩 대신 실제 재고를 읽습니다.
  품절 → `Sold out`, 임계치 이하 → `Only N left`, 그 외 → `In stock`.
  재고 추적을 안 하는 상품은 항상 `In stock` 입니다.
- **빠른 담기**: 단일 옵션 상품만 카드에서 바로 담습니다.
  사이즈 등 옵션이 있으면 카드 버튼이 상품 페이지로 보냅니다(디자인은 M을 임의로 담았지만, 실제 판매에서는 사용자가 사이즈를 골라야 합니다).
- **장바구니**: 데모용 상태 대신 Shopify Cart AJAX API 를 씁니다. 변경 시 드로어를 Liquid 로 다시 렌더하므로 금액 포맷이 항상 스토어 설정과 일치합니다. Checkout 버튼은 실제 결제로 연결됩니다.
- **구독 폼**: `{% form 'customer' %}` 로 고객에 `newsletter` 태그를 붙여 저장합니다.
- **반응형**: 원본 아트보드는 데스크톱 전용이라 900px / 750px 브레이크포인트를 추가해 2단 레이아웃을 1단으로 접습니다.
- **스코프**: 모든 CSS 가 `.strukt` 하위로 한정되어 기존 테마 스타일과 충돌하지 않습니다.

## 남은 작업

- 상품·컬렉션 데이터 입력(디자인의 8개 상품은 예시입니다)
- `Archive` 테이블은 정적 블록입니다. 메타오브젝트로 옮기려면 별도 작업이 필요합니다.
- 스토어가 **trial** 플랜이라 실제 판매를 시작하려면 업그레이드가 필요합니다.
