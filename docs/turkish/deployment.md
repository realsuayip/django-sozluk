#Sunucuya kurulum yapacaklar için notlar

Aksini yapmak için spesifik bir sebebiniz yok ise sunucuya kurulum yaparken şu adımları takip etmenizi öneriyoruz:

* Veritabanı için `PostgreSQL` kullanın.
* Sunucunuza bir önbellekleme sistemi kurmanız veya önbellekleme için ayrı bir sunucu açmanız gerekiyor. Önbellekleme
sistemi için `memcached` test edildi, fakat Django'da önbellek sistemi ortak bir arayüz kullandığı için herhangi bir
sistemi kullanabilirsiniz.
* Bu adreste belirtilen yönergelerin hepsini titiz bir şekilde kontrol ettiğinizden emin olun:
https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/