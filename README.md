# Odyometre Sistemi — Multidisipliner Proje (2025-2026 Bahar)

Ankara Üniversitesi Mühendislik Fakültesi **Multidisipliner Proje Çalışması**
kapsamında geliştirilen, saf-ton (pure-tone) odyometre sisteminin yazılım
deposudur. Proje üç ekibin (Elektrik-Elektronik, Biyomedikal, Yazılım
Mühendisliği) ortak çalışmasıdır; bu depo bunlardan **yazılım** bileşenlerini
barındırır.

## Depo İçeriği

| Klasör | Ekip | İçerik |
|---|---|---|
| [`audiometer_fp/`](audiometer_fp/) | **Yazılım Müh. (YMH 334 — Fonksiyonel Programlama)** | Python tabanlı saf-fonksiyonel çekirdek: Hughson-Westlake eşik arama, IEC 60645-1 doğrulayıcıları, Maybe/Result monadları, map/filter/reduce işlem zinciri, 105 birim + property-based test. |
| [`src/`](src/main/java/com/audiometer/guiproject/) | **GUI / Entegrasyon** | JavaFX masaüstü arayüzü: COM port seçimi, jSerialComm ile seri haberleşme, canlı odyogram grafiği. |

İki bileşen, donanım (Proteus / Arduino UNO / MCP4921 DAC / LM358) ile sanal
COM port üzerinden `PLAY` / `RESPONSE` protokolüyle haberleşir.

## Hızlı Başlangıç

### Python FP çekirdeği (yazılım mühendisliği teslimi)

```bash
cd audiometer_fp
pip install -r requirements.txt

python -m pytest                         # 105 test (birim + property-based)
python -m audiometer.cli --simulate      # sanal hasta üzerinde uçtan uca demo
python -m audiometer.cli --serial COM3   # gerçek/Proteus donanımına bağlanmak için
```

Ayrıntılı dokümantasyon ve YMH 334 gereklilik eşlemesi için bkz.
[`audiometer_fp/README.md`](audiometer_fp/README.md).

### Java GUI

```bash
./mvnw clean javafx:run        # Windows: .\mvnw.cmd clean javafx:run
```

JDK 21 ve JavaFX 21 gerektirir (bağımlılıklar Maven ile otomatik indirilir).

## Sürekli Entegrasyon (CI)

Her `push` ve `pull request` üzerinde [GitHub Actions](.github/workflows/ci.yml),
Python çekirdeğinin tüm test takımını (105 birim + property-based test)
3.10 / 3.11 / 3.12 üzerinde çalıştırır.

## Standartlar

- **IEC 60645-1:2017** — Audiometric equipment, Part 1 (pure-tone audiometry)
- **ISO 389-1:2017** — RETSPL referans seviyeleri
- **WHO (2021)** — World Report on Hearing (işitme kaybı sınıflandırması)
