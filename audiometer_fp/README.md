# Audiometer FP Core — YMH 334 Teslimi

Ankara Üniversitesi Mühendislik Fakültesi, **Multidisipliner Proje Çalışması
2025-2026 Bahar Dönemi**, *Odyometre Sistemi Tasarımı ve Testi* projesinin
**Yazılım Mühendisliği (YMH 334 - Fonksiyonel Programlama)** ekibi tarafından
geliştirilen Python tabanlı çekirdek modüldür.

Proje görev tanımında YMH ekibi için aşağıdaki yükümlülükler tanımlanmıştır:

> - Tüm medikal hesaplamaları **saf fonksiyonlar (pure functions)** olarak yazmak
> - Test verilerini **değişmez (immutable) veri yapılarıyla** yönetmek
> - RESPONSE mesajlarını **map / filter / reduce zinciriyle** işlemek
> - Hata durumlarını **Optional / Maybe deseniyle** yan etkisiz olarak yönetmek
> - Biyomedikal ekibin tanımladığı **IEC 60645-1** algoritma kurallarına uyumu
>   **otomatik birim testleri ve property-based testler** yazarak doğrulamak

Bu depo bu beş kalemin tamamını karşılar.

---

## Hızlı Başlangıç

```bash
# Gerekirse:
pip install -r requirements.txt

# Tüm testleri çalıştır (birim + property-based):
python -m pytest

# Sanal hasta üzerinde uçtan uca demo:
python -m audiometer.cli --simulate

# Proteus / ESP32 / FPGA üzerinden gerçek seri porta bağlanmak için:
python -m audiometer.cli --serial COM3 --baud 9600
```

Şu an depoda **105 test** geçer durumdadır (87 birim + 18 property-based;
property-based testler her koşumda otomatik olarak yüzlerce rastgele örnek
üretir).

---

## Klasör Yapısı

```
audiometer_fp/
├── pyproject.toml
├── requirements.txt
├── conftest.py
├── audiometer/
│   ├── __init__.py
│   ├── types.py              # Maybe, Result, Ear, Stimulus, Audiogram, HWState
│   ├── pure_calc.py          # dB ↔ amplitude, DAC, validation, PTA, sınıflandırma
│   ├── hughson_westlake.py   # H-W durum makinesi (saf fonksiyonel)
│   ├── response.py           # RESPONSE map / filter / reduce ardışık düzeni
│   ├── iec60645.py           # IEC 60645-1 doğrulayıcıları
│   ├── audiogram.py          # Odyogram toplama ve JSON çıktısı
│   ├── serial_bridge.py      # pyserial köprüsü + sanal hasta (yan etkiler burada)
│   └── cli.py                # Demo girişi
└── tests/
    ├── test_types.py
    ├── test_pure_calc.py
    ├── test_hughson_westlake.py
    ├── test_response.py
    ├── test_iec60645.py
    ├── test_audiogram.py
    └── test_properties.py    # Hypothesis property-based testler
```

---

## YMH 334 Gereklilikleri ↔ Kod Eşlemesi

| YMH 334 maddesi | Karşılandığı modül(ler) |
|---|---|
| Saf fonksiyonlar (pure functions) | `pure_calc.py`, `hughson_westlake.py`, `audiogram.py`, `response.py`, `iec60645.py` — **tüm hesaplama mantığı** referans şeffaf, yan etkisiz fonksiyonlar olarak yazıldı |
| Değişmez veri yapıları | `types.py` — bütün domain tipleri `@dataclass(frozen=True)`. Listeler yerine `Tuple[...]`. Durum güncellemeleri `dataclasses.replace(...)` ile **yeni** değer döner. |
| map / filter / reduce zinciri | `response.py` — `to_events`, `count_responses`, `latest_response`, `first_response_within`, `summarise` fonksiyonlarının hepsi `map` + `filter` + `functools.reduce` ile yazıldı. `hughson_westlake.run_session` da `reduce` ile çalışır. |
| Optional / Maybe ile yan etkisiz hata yönetimi | `types.py` — `Maybe = Just \| Nothing` ile `Result = Ok \| Err` cebirsel tipleri. `Just/Nothing/Ok/Err` üzerinde `map`, `bind`, `map_err`, `get_or_else`, `filter`, `to_maybe` metotları. Hiçbir domain fonksiyonu istisna fırlatmaz; bütün hatalar `Result` ya da `Maybe` ile döner. |
| Otomatik birim testleri | `tests/test_*.py` — 87 deterministic birim test. |
| Property-based testler | `tests/test_properties.py` — Hypothesis ile 18 property; monad yasaları, IEC aralık değişmezleri, H-W sonlanması, adım-boyu kuralı, değişmezlik ve odyogram fold özelliği. |

---

## Mimari Not — Yan Etkilerin İzolasyonu

Saf çekirdek herhangi bir I/O yapmaz. Yan etkiler **yalnızca** iki yerde
bulunur:

* `audiometer.serial_bridge` — `pyserial` üzerinden Proteus / ESP32 /
  FPGA'ya bağlanır, `RESPONSE` satırlarını okur, komut yazar.
* `audiometer.cli` — argüman ayrıştırma ve raporu `stdout`'a yazma.

Hughson-Westlake döngüsü saf bir `(state, response) -> state` fonksiyonu
olarak yazıldığından, sanal hasta (`VirtualPatient`) ile gerçek seri port
arasında geçiş yapmak, yalnızca `oracle: Stimulus -> bool` fonksiyonunu
değiştirmekten ibarettir. Bu, "donanım olmadan da algoritma test
edilebilsin" gereksiniminin doğrudan karşılığıdır.

---

## Hughson-Westlake Algoritması

`audiometer/hughson_westlake.py` modülü, Biyomedikal ekibi tarafından
belgelenmiş ve IEC 60645-1 ekinde tanımlanmış modifiye Hughson-Westlake
prosedürünü uygular:

1. Başlangıç dB seviyesi: 30 dB HL (familyarizasyon).
2. Hasta yanıt verirse → 10 dB azalt (alçalan adım).
3. Hasta yanıt vermezse → 5 dB artır (yükselen adım).
4. **Eşik:** Aynı dB seviyesinde **en az 3 yükselen sunumdan en az 2'sinde**
   yanıt verilmesi durumunda o seviye eşik olarak kaydedilir.
5. Tavan (120 dB) seviyesinde yanıt alınamazsa eşik `Nothing` döner
   (ölçülemez kayıp).

Algoritma sürekli olarak `HWState` (immutable) üretir; her adımda yeni bir
`Presentation` tuple'a eklenerek yeni bir `HWState` döner. Eski durumlar
hiçbir zaman mutate edilmez. Sonlanma garantisi property-based testte
ispatlanır.

Frekans sırası: **1000 → 2000 → 4000 → 8000 → 500 → 250 Hz** (önce en
güvenilir referans, sonra yüksek/alçak frekanslar).

---

## IEC 60645-1 Doğrulayıcıları

`audiometer/iec60645.py`:

* `validate_stimulus` — frekansın IEC kümesinde, dB değerinin `[-10, 120]`
  aralığında ve 5 dB ızgarasında olduğunu kontrol eder.
* `audiogram_complete` — odyogramın her iki kulak için tüm gerekli
  frekansları içerip içermediğini denetler (Type-1 tanı ve Type-4 tarama
  varyantları desteklenir).
* `step_sizes_correct` — sunum geçmişinde "10 aşağı / 5 yukarı" kuralına
  uyulup uyulmadığını doğrular; tavan/taban clamp'lerini hesaba katar.
* `state_is_iec_conformant` — yukarıdakilerin bileşkesi: tamamlanan bir
  H-W oturumunun IEC kurallarına uygun bittiğini tek bir `Result` ile döner.

---

## Sistem Entegrasyonu

Sistem bütünü iki proses olarak çalıştırılabilir:

```
┌───────────────────┐    Sanal COM Port    ┌─────────────────────────┐
│ Proteus (EEE)     │ ←─────────────────→  │ Java GUI (Bilgisayar)    │
│ Arduino UNO       │                      │ jSerialComm             │
│ MCP4921 DAC       │                      │ LineChart audiogram     │
│ LM358 buffer      │                      └─────────────────────────┘
│ Sanal hasta butonu│                                │
└───────────────────┘                                ▼ "RESPONSE"
                                          ┌─────────────────────────┐
                                          │ audiometer_fp (YMH)     │
                                          │ Pure FP çekirdek         │
                                          │ - Maybe / Result        │
                                          │ - map/filter/reduce     │
                                          │ - H-W state machine     │
                                          │ - IEC 60645-1 validator │
                                          │ - property-based tests  │
                                          └─────────────────────────┘
```

Python modülü iki şekilde devreye girer:

1. **Bağımsız mod (`--simulate` ya da `--serial COM3`)**: Python kendi
   `RESPONSE` oracle'ı ile H-W oturumunu yürütür, raporu yazar.
2. **Java GUI'nin yardımcısı**: Java tarafı eşik değerlerini ve sunum
   geçmişini JSON olarak Python CLI'ya aktarır (`audiometer-fp` komut
   satırı çıktısı), Python tarafı doğrulama ve IEC raporunu üretir.

---

## Standartlar ve Referanslar

Aşağıdaki standart ve kaynaklar bu çekirdeğin tasarımında temel alınmıştır;
proje raporunun **REFERENCES** bölümüne de aynı maddelerin işlenmesi
önerilir.

* **IEC 60645-1:2017** *Electroacoustics — Audiometric equipment — Part 1:
  Equipment for pure-tone audiometry.*
* **ISO 389-1:2017** Referans eşit eşik ses basıncı seviyeleri (RETSPL).
* **ASHA (1978)** *Guidelines for Manual Pure-Tone Threshold Audiometry.*
* **Carhart, R., Jerger, J. (1959)** "Preferred Method for Clinical
  Determination of Pure-Tone Thresholds."
* **WHO (2021)** *World Report on Hearing* — hearing-loss grading
  (Normal, Mild, Moderate, Moderately Severe, Severe, Profound).
* **Hughson W., Westlake H. (1944)** "Manual for Program Outline for
  Rehabilitation of Aural Casualties Both Military and Civilian."

---

## Geliştirme Sırasında Alınan Mimari Kararlar

1. **Cebirsel veri tipleri** (`Maybe`, `Result`) — Python'da klasik
   `Optional[T]` (yani `T | None`) yerine `Just(value)` / `Nothing()`
   sınıfları kullanıldı çünkü desen monad yasalarını property-based
   testle ispatlanabilir kılıyor (`test_properties.py`).
2. **`functools.reduce` zorunluluğu** — `to_events`, `summarise`,
   `run_session` gibi koleksiyon işlemlerinde `for` döngüsü yerine
   `reduce` tercih edildi; bu, "RESPONSE mesajları map/filter/reduce
   zinciriyle işlensin" şartını sözlü olarak değil yapısal olarak yerine
   getirir.
3. **`@dataclass(frozen=True) + Tuple`** — Bütün domain veri yapıları
   hashlenebilir ve değiştirilemez, böylece function-as-value mantığı
   güvenli paylaşılabiliyor; Hypothesis testlerinde `assert state.x is
   snapshot` ile mutasyon olmadığı doğrulanıyor.
4. **Yan etkiler tek bir modülde** — `serial_bridge.py` dışında hiçbir
   modül `import serial`, `import time` (CLI hariç) veya `print` çağırmaz.
   Bu, "yan etkisiz" tanımının kodla denetlenebilir hâle gelmesini
   sağlar.

---

## Sorun Giderme

* **`ModuleNotFoundError: No module named 'audiometer'`** — `pytest`
  doğrudan `audiometer_fp/` klasöründen çalıştırılmalı; `conftest.py`
  paket kökünü `sys.path`'e ekliyor.
* **`pyserial` kurulu değil** — `pip install pyserial` ya da `pip
  install -e .[serial]`. Sanal hasta modu (`--simulate`) için gerekli
  değildir.
* **Windows COM port adı** — `--serial COM5` gibi büyük harfle yazılır.
  Proteus tarafında COMPIM ile aynı sanal porta bağlanılmalı.
