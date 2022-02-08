## django-sozluk, Python tabanlı ekşisözlük klonu, (bkz: [klon](https://tr.wikipedia.org/wiki/Klonlama))
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/6c2a34dfbd184f139cd32f8f622d4002)](https://www.codacy.com/manual/realsuayip/django-sozluk?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=realsuayip/django-sozluk&amp;utm_campaign=Badge_Grade)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](LICENSE)

Demo website [sozluk.me](https://sozluk.me/) adresinde ulaşılabilir durumda!\
Yeni versiyonu klonlamadan önce [CHANGELOG](CHANGELOG)'u kontrol etmeyi unutma suser

Bu bir ekşisözlük klonudur. Çoğunlukla anıldığı gibi "bir elde sen at be sözlük",
Bu proje "herkesin kültür zerreciklerini dağıtıp entellik yapabildiği sözlük" gibidir.
Sosyal ağ(sosyal örümcek şeyi) hakkında daha çok şey öğrenmek için [this Wikipedia article](https://en.wikipedia.org/wiki/Ek%C5%9Fi_S%C3%B6zl%C3%BCk) 
adresini ziyaret edin ve görün.

**Bu proje anlık olarak korunuyor.** Eğer katkı sağlamak isterseniz ya da bir hata bulduysanız ki bulamazsınız,
benimle iletişime geçmek isteyebilirsiniz(başka kiminle iletişime geçeceksiniz, korktum).
Telegram (Orada da aynı kullanıcı adını kullanıyorum, ne kadar akıllıca dimi?) veya, daha akıllıca, [bir konu oluşturun](https://github.com/realsuayip/django-sozluk/issues/new).

Yapılacakları görmek için to-do anahtar kelimesini kontrol edin.(to-do ney ya, ne mutlu türküm diyene)

Mevcut siteyi görmek için [screenshots](screenshots) klasörünü ziyaret edin.
   
### Kolay indirme

Sisteminizde Docker ve Python'un son versiyonunun indirilmiş olduğundan emin olun. Dosyaları
Git/Github yoluyla klonlayın ve projenin kök dizininde şu komutu çalıştırın:

    python docker.py up

Bu proje için inşaa ve geliştirme sunucusunu başlatacaktır. Üretim durumunda olduğunu aklınızda tutun
, elektronik postalar konsola düşecektir (konteyner kayıtları).

Geliştirme modunda(namı diğer test modu) çalıştırmak ayrıca ```test@django.org``` adında bir elektronik posta ve ```test```  adında bir şifre oluşturacaktır.
Girişlerinizin görünmesi için kendinizi gerçek bir yazar yapmanız gerekir, yani,
yönetici kullanıcı düzenleme sayfasını kullanarak kendinizi acemi yani beceriksiz bir iş beceremeyen tembel çocuk durumundan kaldırın.

Web sitesi önbellek mekanizmik zımbırtısını sıklıkla kullanır, bu nedenle devre dışı bırakma eğiliminde olabilirsiniz.(hayda)
Sahte bir önbellek arka ucu kullanarak önbelleğe almayın veya sol çerçevede önbelleği devre dışı bırakmayın.(ee?)
Önbelleğe almak ile ilgili ayarları ve diğer şeyleri öğrenmek için ```apps.py``` üzerindeki ayarları kontrol edin(tamam geç bunları geç)

Python aracı ayrıca üretim kurulumu için önünüze taş koymaz (:D), Daha fazlasını öğrenmek için `python docker.py --help`
komutunu çalıştırın(disklerin çalışma sesini gür bir şekilde duymaya hazır ol suser!)

### Standart docker kullanımı(kolaycı mod)
Daha ayrıntılı kontrol elde etmek için yardımcı komut dosyasını kullanmamayı tercih ediyorsanız, doğru 
dosyayı belirttiğinizden emin olun. Başlatmak ve çalıştırmak için bu komutu kullanın:

    docker-compose up -d

Başlangıçta, aynı zamanda, aşağıdakileri ayarlayan bir komut dosyası (web konteynerinde) çalıştırmanız gerekir.
Veritabanı, statik dosyaları toplar ve sözlük uygulaması için gerekli kullanıcıları oluşturur:

    docker-compose exec web sh scripts/setup.sh

Bu işlemlerden sonra bir yönetici hesabı oluşturmanız olasıdır(şuayip başkana atfedildi):

    docker-compose exec web python manage.py createsuperuser

Bu yapılandırmayı kullanmayı düşünüyorsanız, bütün ```.env```, Django ayarlar dosyası (```settings_prod.py```) ve sözlük ayarları dosyası (```dictionary/apps.py```)'i düzgün
bilgiler ile düzenlediğinizden emin olun. Ayrıca setup.sh aracılığıyla oluşturulan kullanıcıların
parolalarını değiştirdiğinizden emin olun.
