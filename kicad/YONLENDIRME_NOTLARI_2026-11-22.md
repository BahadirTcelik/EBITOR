# Yönlendirme notları – 22 Kasım 2026 (Emrecan + Claude)

Başlangıç: Melis'in 21 Kasım 20:33 kaydı (DRC12: 47 bağlanmamış). Son durum: **bütün bağlantılar çizildi.**

## Kontrol sonuçları (22 Kasım 17:2x)

| Kontrol | Sonuç | Dosya |
|---|---|---|
| KiCad DRC | 0 hata, 0 bağlanmamış; yalnızca kabul edilmiş 67 `lib_footprint_mismatch` | `out/DRC21.rpt` |
| ERC | 0 hata; kabul edilmiş 6 `lib_symbol_mismatch` (Q1–Q3, U3, U4, RV1) | `out/erc.rpt` |
| Şema–PCB eşleşmesi | temiz | (PCB-Checker içinde) |
| Kurs PCB-Checker (`--overload`) | **0 must fix**, 1 should fix (Q2 kapı izi, aşağıda karar 1) | `out/pcb_check.html` |
| Toprak adaları | 11 GND parçası, hepsi via ile düzleme bağlı; L3 GND dolgusu tek parça | – |

## Kartta ne değişti

**Parça kaydırma (2 adet, takım onayıyla):** C22 0.5 mm sağa (103.0 → 103.5), R5 0.6 mm sağa (105.5 → 106.1).
Neden: U1 pin 21 (SW) ile C22 arasına SW için 0.5 mm kuralına uyan bir yol açmak. `.kicad_dru` kuralı değişmedi.

**Yeni bağlantılar (47 → 0):**
- U1 sol üstü: VIN_IC, EXTVCC, DRVCC (C23, TP11, R29'a kartın alt kenarından L3 ile), INTVCC (U1-18/19, R12, TP12).
- U1 sağ üstü: BOOST (U1-22 → L3 → C22, 7.4 mm), SW (U1-21 → R6 ile C22 arası → C22 → SW dolgusu).
- Snubber C15–R7; geri besleme R15.1 → B.Cu → TP6 (J2 tarafı, SW'ye 16 mm uzak).
- Test noktaları TP14–TP17 (PGOOD B.Cu'da).
- Akım sınırlama bloğunun tamamı: U2 Kelvin (RSH1'e 6.8 / 9.1 mm), +5V_CC, U3 çevresi, RV1, TP18–TP21.
- **EXTVCC beslemesi (karar 2, seçenek A):** R22.1 → B.Cu → sağdaki VOUT_C güç dolgusu / TP7 (60 mm, 0.4 mm). Akım ölçme izine (RS1 → U1-4) bağlanmadı; bağlansaydı EXTVCC akımı ölçmeye ~4 mV hata katardı.

**Toprak ve ısı:**
- In2.Cu (L3) boş alanlarına GND dolgusu.
- Dikiş via'ları: C9–C13 (her birine 2), C7, R4; CC bloğundaki her toprak pedine 1; Q3 toprak adasına 6 (toplam 18 → 7.5 A için yeterli).
- Q1 drain padinin yanına 8 VIN ısıl via'sı (B.Cu'daki 8 cm² VIN dolgusuna).
- İz bağlantısı olmayan bütün via'lar "free" işaretli (KiCad ağlarını değiştirmesin diye).

**Diğer:** Q1–Q3 ve U1–U4'ün Datasheet alanları şemadan karta yazıldı (şema–PCB farkı buydu).
`pcb_checker.json`'a 5 gerekçe (waiver) eklendi: 4 katman, Q1 kapı izi (asıl yol 21.3 mm, kalanı TP9 kolu), VIN_IC test noktası, Q2 ve Q3 ısıl via.

## Takımın vermesi gereken kararlar

1. **TP10 / BG_G kolu.** Q2'nin asıl sürücü→kapı yolu **14.9 mm**; PCB-Checker'ın gördüğü 39 mm'nin 24.4 mm'si TP10'a giden kol (sınır ~30 mm).
   (a) Kolu silmek, ölçümü Q2 kapı padinden yapmak; (b) TP10'u Q2'ye yaklaştırmak; (c) kolu bırakıp gerekçe yazmak.
2. **Serigrafideki grup numarası** ("GROUP __").
3. Üretim firması ve katman yapısı (Board Setup → Physical Stackup) – sipariş öncesi.

## Bahadır'a not
- ERC ayarlarında 4 kontrol kapalı (ör. "global label only appears once"). Kart şemayla birebir eşleştiği için sorun görmüyoruz; bilerek mi kapatıldı?
- VIN_IC için test noktası yok (PCB-Checker sordu); şimdilik C26 padinden ölçüm gerekçesi yazıldı.

## İncelemek için
KiCad'de `ee463_dcdc.kicad_pro` → PCB → **B** (dolguları yenile). Katmanları tek tek açın: F.Cu, In2.Cu (L3), B.Cu.
Kalan işler: karar 1 ve 2'yi uygulamak, Gerber/delik/BOM/zip, zip üzerinde PCB-Checker, `layout_plan.md` güncellemesi.
