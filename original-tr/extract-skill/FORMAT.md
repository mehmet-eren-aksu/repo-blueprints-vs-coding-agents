# Blueprint formatı (v0.2)

Anahtarlar İngilizce, açıklamalar Türkçe yazılır. Bütün yollar repo köküne göredir. Konum işaretçileri `dosya:satır` ya da `dosya:başlangıç-bitiş` biçimindedir.

## blueprint.yaml

```yaml
format: blueprint/0.2
repo: <sahip/ad ya da klasör adı>
commit: <git rev-parse HEAD>
extracted_at: <YYYY-MM-DD>
extracted_by: <model adı>
code_lines: <test hariç kaynak satır sayısı>
languages: {<dil>: <satır>}
```

## map.yaml

```yaml
summary: <aracın ne yaptığını anlatan tek cümle>

entrypoints:
  - where: <dosya:satır>
    what: <ne başlatır>

pipeline:                 # bir girdinin geçtiği aşamalar, sırayla
  - id: P1
    stage: <kısa ad>
    what: <ne yapar>
    where: [<dosya:satır>]

modules:
  - path: <dosya ya da klasör>
    role: <tek cümle>
    layer: core | domain | mixed
    domain_lines: [<dosya:başlangıç-bitiş>]   # yalnızca mixed ise
    depends_on: [<yol>]

seams:                    # çekirdek ile alan katmanı arasındaki bağlantılar
  - id: S1
    name: <kısa ad>
    kind: explicit | embedded
    interface: <fonksiyon, trait ya da veri yapısı imzası>   # explicit ise
    where: [<dosya:satır>]
    note: <embedded ise alan bilgisinin çekirdeğe nasıl sızdığı>

extension_points:         # yeni bir varyant eklemenin bugünkü yolu
  - id: E1
    variant: <ör. yeni girdi türü, yeni komut, yeni backend>
    mechanism: <kod bugün varyantları nasıl seçiyor>
    touch:                # dokunulması gereken bütün yerler
      - where: <dosya:satır>
        what: <ne değişmeli>
    related_invariants: [<INV id>]
    tests: [<ilgili test dosyası ya da test adı>]

assumptions:              # kodun alana dair varsayımları
  - id: A1
    assumes: <ne varsayılıyor>
    where: [<dosya:satır>]
    affects: <neyi etkiliyor>

invariants:               # bozulmaması gereken davranışlar
  - id: INV-01
    category: sorting | config | cli | errors | safety | warnings | defaults | interaction | other
    statement: <tek cümle, gözlemlenebilir davranış>
    evidence: [<dosya:satır>]
    test: <test dosyası::test adı> | null
    confidence: verified | read | guess
    documented: yes | no | contradicts

config:
  sources: [<config'in okunduğu yerler, öncelik sırasıyla>]
  discovery: <config dosyası nasıl bulunuyor>
  precedence: <katmanların birbirini nasıl ezdiği>
  keys:
    - key: <anahtar>
      type: <tip>
      default: <varsayılan>
      applies_to: <neye uygulanıyor>
      where: <dosya:satır>

cli:
  flags:
    - flag: <--bayrak>
      what: <ne yapar>
      where: <dosya:satır>
  exit_codes: {<kod>: <anlamı>}
  io: <stdin, stdout, stderr ve dosya yazma davranışı>

doc_discrepancies:
  - doc: <dosya:satır>
    says: <dokümantasyon ne diyor>
    code: <dosya:satır>
    actually: <kod ne yapıyor>

unknowns:
  - question: <emin olunamayan davranış>
    where: [<dosya:satır>]
```

## README.md (insan görünümü)

`map.yaml`'dan türetilir ve yeni iddia eklemez. Her maddenin yanında map'teki kimliği parantez içinde yazar (`INV-03`, `E1` gibi).

1. **Tek cümle:** `summary`.
2. **Bir sayfada:** ne yaptığı, aşamaları gösteren bir Mermaid şeması, çekirdek/alan tablosu ve en önemli 5 değişmez.
3. **Uyarlama rehberi:** her genişleme noktası için kısa bir kontrol listesi ve ilgili değişmezler.
4. **Modül ayrıntıları:** modül başına birkaç satır.
5. **Dokümantasyon tutarsızlıkları** ve **belirsizlikler.**
