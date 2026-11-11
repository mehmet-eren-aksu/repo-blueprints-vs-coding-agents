# Görev

Bu klasör `sqlfluff` adlı SQL linter'ının repo'sunun bir kopyası. Kullanıcının isteği şu:

> LT05 uzun bir virgüllü listeyi (örneğin `GROUP BY` terimleri ya da bir fonksiyonun argümanları) bölerken şu an her elemanı ayrı satıra koyuyor. Bunun yerine her satıra sığdığı kadar eleman koyan bir seçenek istiyorum.
>
> Config'in `[sqlfluff:indentation]` bölümüne `list_wrapping` diye bir ayar eklensin:
>
> ```ini
> [sqlfluff:indentation]
> list_wrapping = fill
> ```
>
> Değerleri `one_per_line` ve `fill` olsun. Varsayılan `one_per_line` olsun ve bugünkü davranış hiç değişmesin.
>
> Örnek: `max_line_length = 45` iken bugünkü çıktı şu:
>
> ```sql
> SELECT a
> FROM tbl
> GROUP BY
>     long_column_name1,
>     long_column_name2,
>     long_column_name3,
>     long_column_name4
> ```
>
> `list_wrapping = fill` ile şöyle olsun:
>
> ```sql
> SELECT a
> FROM tbl
> GROUP BY
>     long_column_name1, long_column_name2,
>     long_column_name3, long_column_name4
> ```

## Ayrıntılar

1. Her satıra sınırı aşmadan sığan kadar eleman koy. Satır uzunluğunu LT05 bugün nasıl ölçüyorsa öyle ölç: girinti dahil ve şablonlu (Jinja) SQL'de render edilmiş metne göre değil, kaynak metne göre.
2. Fill yalnızca çok uzun bir satırı böler. Satırları birleştirmez, listede zaten var olan satır sonlarını korur. Sınırı aşmayan satıra dokunmaz.
3. Virgüllerin konumu için yapılmış ayar (`trailing`, `leading`, `alone`) satırın bölündüğü yerde yine geçerli. `alone` ayarında virgül yine kendi satırında durur.
4. Yalnızca virgüllü listeler doldurulur. `AND`, `OR`, `+` gibi operatörler doldurulmaz, bugünkü gibi her biri ayrı satır sonu alır.
5. İç içe listelerde LT05'in bugünkü sırası korunur: önce dıştaki liste, gerekirse sonra içteki liste bölünür.
6. LT05 bir şablon etiketinin (`{{ ... }}`, `{% ... %}`) içini bölmez. Bütün listeyi tek bir etiket render ediyorsa satır, iki ayarda da uzun kalır.
7. LT09 birden fazla select hedefini her durumda ayrı satırlara koyar. Bu değişmesin. LT09 `exclude_rules` ile kapatılırsa select hedefleri de doldurulur.
8. `sqlfluff fix` iki kez çalıştırıldığında ikinci çalışma hiçbir şey değiştirmemeli.
9. Geçersiz bir değer (`FILL` gibi büyük harfli yazımlar, boş string, sayı dahil) config doğrulamasında `SQLFluffUserError` versin. Mesaj, `implicit_indents` için var olan doğrulama mesajıyla aynı kalıpta olsun: ``... set an invalid value for `list_wrapping`: <değerin repr'i>. Valid options are: one_per_line, fill. ...``
10. Yeni ayar, varsayılan değeriyle birlikte varsayılan config dosyasında yer alsın.

## Çalışma kuralları

1. Değişiklikleri bu klasörde yap.
2. İnternete çıkma. sqlfluff'un başka bir sürümünü indirme, kurma ya da inceleme.
3. Bu klasörün dışındaki dosyaları okuma.
4. Soru sorma, bu oturumda cevap verecek kimse yok. Belirsiz bir şey olursa en makul yorumu seç ve `NOTES.md`'ye yaz.
5. Python ortamı hazır: testleri `.venv/bin/python -m pytest ...` ile çalıştır. Bütün test paketi çok uzun sürer; ilgili testleri seç.
6. Dokümantasyonu güncellemek isteğe bağlı.

## Bitirince

- Yeni davranış için kendi testlerini ekle.
- Değişikliğin dokunduğu alanlardaki mevcut testler geçmeli.
- Repo köküne `NOTES.md` yaz ve içine şunları koy:
  1. Değiştirdiğin ve eklediğin dosyalar.
  2. Belirsiz bulduğun noktalar ve her biri için seçtiğin yorum.
  3. Emin olmadığın ya da bitiremediğin şeyler.
  4. Hangi testleri çalıştırdığın ve sonuçları.
  5. Kabaca kaç adımda ve ne kadar sürede bitirdiğin.

Kullanım limitine takılırsan, durmadan önce `NOTES.md`'ye nerede kaldığını yaz.
