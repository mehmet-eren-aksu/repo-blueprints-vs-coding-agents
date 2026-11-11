# Görev

Bu klasör `pedantix` adlı aracın repo'sunun bir kopyası. Kullanıcının isteği şu:

> pedantix şu an yalnızca Nix dosyalarını düzenliyor. JSON dosyalarındaki nesne anahtarlarını da sıralayabilsin istiyorum. `.json` dosyalarında ve `--stdin-filepath` bir `.json` yolu gösterdiğinde pedantix aynı config'i kullansın: `[attrs]` ayarları JSON nesnelerine, `[lists]` ayarları JSON dizilerine uygulansın, `[[overrides]]` ve `[[files]]` da çalışsın. Sayılar ve stringler birebir korunsun. Nix davranışı hiç değişmesin.

Repo kökündeki `blueprint/` klasörü bu kod tabanının uyarlama haritası. Önce `blueprint/README.md` dosyasını, ayrıntı için `blueprint/map.yaml` dosyasını oku, sonra işe başla.

## Çalışma kuralları

1. Değişiklikleri bu klasörde yap.
2. İnternete çıkma. Tek istisna: `cargo` ile crates.io'dan bağımlılık indirmek serbest.
3. Bu klasörün dışındaki dosyaları okuma.
4. Soru sorma, bu oturumda cevap verecek kimse yok. Belirsiz bir şey olursa en makul yorumu seç ve `NOTES.md`'ye yaz.

## Bitirince

- `cargo build --release` hatasız çalışmalı.
- Repo'nun mevcut testleri (`cargo test`) geçmeli.
- Repo köküne `NOTES.md` yaz ve içine şunları koy:
  1. Değiştirdiğin ve eklediğin dosyalar.
  2. Belirsiz bulduğun noktalar ve her biri için seçtiğin yorum.
  3. Emin olmadığın ya da bitiremediğin şeyler.
  4. Kabaca kaç adımda ve ne kadar sürede bitirdiğin.

Kullanım limitine takılırsan, durmadan önce `NOTES.md`'ye nerede kaldığını yaz.
