---
name: extract
description: Bir kod tabanından blueprint, yani kodla doğrulanmış bir uyarlama haritası çıkarır. Kullanıcı /extract dediğinde ya da bir repo için blueprint istediğinde kullan.
---

# Blueprint çıkarma

## Amaç

Bu repoyu kendi ihtiyacına göre uyarlamak isteyecek bir ajan ve bir insan için, **kodla doğrulanmış bir uyarlama haritası** üret. Harita şu soruları cevaplamalı:

- Kodun hangi kısmı **taşınabilir çekirdek** (belirli bir alana bağlı olmayan mantık), hangi kısmı **alana bağlı katman** (belirli bir dosya formatına, dile, protokole, platforma ya da dış araca bağlı kısım)?
- İkisi birbirine nereden ve hangi arayüzle bağlanıyor?
- Yeni bir varyant eklemek için nerelere dokunmak gerekir?
- Kodun hangi yerleri alana dair neyi varsayıyor?
- Neyin **kesinlikle bozulmaması** gerekir? Özellikle dokümantasyonda yazmayan davranışlar.

**Hangi uyarlamanın yapılacağını bilmiyorsun.** Harita her tür uyarlamaya eşit derecede yaramalı: yeni bir girdi türü, yeni bir platform, yeni bir komut, bir bileşeni değiştirmek ya da başka bir dile taşımak. Belirli bir uyarlamayı varsayma, öne çıkarma ve bir uyarlama için hazır çözüm yazma.

## Çıktı

Repo kökünde bir `blueprint/` klasörü. Ayrıntılı şema için aynı klasördeki `FORMAT.md` dosyasına bak.

- `blueprint.yaml`: kimlik bilgisi (repo, commit, tarih, boyut, çıkaran model).
- `map.yaml`: **tek doğruluk kaynağı.** Ajanların okuduğu yapılandırılmış harita.
- `README.md`: insan görünümü. Yalnızca `map.yaml`'dan türetilir, yeni iddia eklemez.

## Adımlar

1. **Envanter.** Okumaya başlamadan önce komutlarla çıkar: `git rev-parse HEAD`, dosya ağacı, diller ve satır sayıları, bağımlılık dosyaları, giriş noktaları, test klasörleri, dokümantasyon dosyaları.
2. **Dokümantasyonu oku** (README, docs/, örnek config dosyaları). Somut iddiaları not al: anahtar adları, varsayılanlar, değer listeleri, davranış açıklamaları. Bunları sonra kodla karşılaştıracaksın.
3. **Kodu giriş noktasından izle.** Bir girdinin geçtiği aşamaları sırayla çıkar.
4. **Modül haritası.** Her modül için rolünü ve katmanını belirle: `core`, `domain` ya da `mixed`. `mixed` modüllerde alana bağlı satır aralıklarını ayrıca göster.
5. **Dikişler.** Çekirdek ile alan katmanı arasındaki arayüzleri bul. Açık bir arayüz yoksa ve alan bilgisi çekirdeğin içine gömülüyse, bunu `embedded` olarak işaretle ve gömülü olduğu yerleri listele.
6. **Genişleme noktaları.** Yeni bir varyant türü (girdi türü, komut, backend, çıktı hedefi gibi; repoda hangisi anlamlıysa) eklemek için kodun bugünkü mekanizmasını anlat. Örneğin uzantıya göre seçim, enum, trait/interface, registry. Dokunulması gereken bütün yerleri kontrol listesi olarak ver. Repoda anlamlı olan her varyant türü için bunu ayrı ayrı yap.
7. **Gömülü varsayımlar.** Alana özgü sabitleri ve kontrolleri ara: dosya uzantıları, sabit araç adları, parser düğüm türleri, sabit yollar, özel dosya adları. Her birini `dosya:satır` ile ve neyi etkilediğiyle yaz.
8. **Değişmezler.** Kullanıcının gözlemleyebildiği ve bozulmaması gereken davranışları çıkar. **Öncelik dokümantasyonda yazmayanlarda.** Şu kategorileri tek tek tara:
   - sıralama ve karşılaştırma semantiği (büyük-küçük harf, sayılar, Unicode, eşitlik durumları),
   - config arama, katmanlama ve öncelik sırası,
   - CLI çıkış kodları, stdout ile stderr ayrımı, dosya yazma koşulları,
   - hata durumları ve hatanın kapsamı (tek dosya mı, bütün çalışma mı),
   - güvenlik kontrolleri, uyarılar, idempotentlik, varsayılan değerler,
   - ayarların birbirini nasıl etkilediği (bir ayar başka bir ayarı devre dışı bırakıyor mu).

   Her değişmez için şunları yaz: ifade, kanıt (`dosya:satır`), varsa onu sınayan repo testi, güven düzeyi ve dokümantasyonda geçip geçmediği. Mümkünse aracı derle ve küçük girdilerle çalıştırarak davranışı gözlemle; gözlemlediğin değişmezin güven düzeyi `verified` olur.
9. **Dokümantasyon tutarsızlıkları.** 2. adımda not aldığın her somut iddiayı koddaki tanımla karşılaştır. Çelişenleri ve kodda karşılığı olmayanları yaz.
10. **Belirsizlikler.** Kodu okuduğun halde emin olamadığın davranışları soru olarak yaz.
11. **Yaz.** Önce `map.yaml`'ı yaz, sonra `README.md`'yi ondan türet.
12. **Kontrol et.**
    - Her `dosya:satır` işaretçisini yeniden aç ve gerçekten iddia edilen şeyi gösterdiğini doğrula.
    - README'deki her iddianın `map.yaml`'da bir karşılığı olsun.
    - Blueprint'in toplam boyutu kodun yaklaşık %10'unu geçmesin.

## Büyük repolar

Kaynak kodu yaklaşık 20.000 satırı geçiyorsa bu bölüm 1-12. adımların nasıl uygulanacağını değiştirir.

- **Boyut sınırı.** %10 kuralı yerine okunabilirlik sınırı uygula: `README.md` en fazla yaklaşık 400 satır, `map.yaml` en fazla yaklaşık 2500 satır.
- **Tekrarlayan aileler.** Aynı kalıpla yazılmış çok sayıda üye varsa (diller, eklentiler, kurallar, adaptörler, sürücüler gibi) her üyeyi ayrı ayrı haritalama. Aileyi tek bir kalıp olarak yaz: ortak arayüz, üyelerin listesi ya da bulunduğu yer, temsili bir üye, yeni üye eklemenin kontrol listesi ve kalıbın dışına çıkan üyeler.
- **Derinlik çekirdeğe.** Kazandığın yeri, birçok ailenin ya da özelliğin paylaştığı çekirdek makineye harca. Uzun ve karmaşık çekirdek modüller için iç harita çıkar: ana fonksiyonlar, aralarındaki çağrı ve veri akışı, hangi kararın hangi fonksiyonda verildiği ve bu modüle davranış ekleyen bir değişikliğin hangi noktalara dokunması gerektiği.
- **Mevcut ajan ve katkı dokümanları.** `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING` gibi dosyaları oku. Söylediklerini tekrar etme, onlara işaret et. Haritayı bu dosyaların söylemediği şeylere ayır ve çelişkileri 9. adımda yaz.
- **Testler.** Bütün test paketini çalıştırma. Bir değişmezi doğrulamak için yalnızca ilgili testleri ya da küçük girdilerle aracın kendisini çalıştır.
- **Önceliklendirme.** Her şeyi aynı derinlikte bitiremeyeceksen kapsamadığın alanları `unknowns` bölümüne "incelenmedi" diye yaz.

## Kurallar

- Repodaki koda dokunma. Yalnızca `blueprint/` klasörüne yaz.
- İnternete çıkma. Yalnızca repodaki bilgiyi kullan.
- Uydurma. Emin olmadığın şeyi `unknowns` bölümüne yaz. Tahminlerini `confidence: guess` olarak işaretle.
- "Neden böyle?" sorusunu yalnızca bir kanıtla cevapla: kod yorumu, commit mesajı ya da test adı. Kanıt yoksa nedenini yazma.
- Kısa ve somut yaz. Her madde tek bir şey söylesin.
