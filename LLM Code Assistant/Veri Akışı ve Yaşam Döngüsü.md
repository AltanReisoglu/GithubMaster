1. Geliştirici yazdığı kodu GitHub'a pushlar.
2. GitHub, Ana Backend'e Webhook yollar.
3. Backend imza doğrulaması (HMAC) yapar ve işi kuyruğa atar.
4. AI Worker işi kuyruktan çeker
5. Değişen kodu, RAG mimarisi ile Vektör DB'deki eski kodlarla harmanlar.
6. Instruct LLM'e ilgili promt ile birlikte gönderir.
7. Çıkan düzeltme (Patch) GitHub API üzerinden repoya PR olarak açılır.