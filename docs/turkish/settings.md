# Ayarlar

### GENERIC_SUPERUSER_USERNAME
`generic_superuser` özel bir kullanıcıdır. Normal kullanıcılardan farklı olarak
tüm kullanıcılara mesaj gönderme yetkisine sahiptir. Bu kullanıcı, hesabı askıya 
alınan kullanıcılara bilgi mesajı atma, taşınan başlıklara `bkz` verme,
ukte veren kullanıcılara müjde verme gibi birtakım ayak işlerini *otomatik olarak*
yapar.

Bu ayarın değeri `str` tipi olmalıdır. Sözlükteki `generic_superuser` aksiyonlarını
gerçekleştirecek kullanıcıyı belirler. Kullanıcın `username` adlı alanını birebir 
girmelisiniz.

Kullanıcıyı oluşturmak için:

1. `DEBUG` modunda olduğunuzdan emin olun. Sitenizi canlıya almadan önce bu
ayarı yapmanız gerekiyor.
2. [Ayar dosyası](/dictionary/utils/settings.py)nda kullanıcı adını belirleyin. Halihazırda
`djangosozluk` olarak durur. Bu isimle bir kullanıcının var olması gerekmiyor, bu adımdan
sonra oluşturulacak.
3. [Proje ana dizini](/../../)nde komut satırını açıp şu komutu çalıştırın ve adımları takip edin:

        python manage.py create_generic_user superuser KULLANICININ_PAROLASI EPOSTA_ADRESİ

Birkaç not:
* Adının aksine, bu kullanıcın herhangi bir yetkiye sahip olması gerekmiyor, eğer
ihtiyacınız yok ise bu kullanıcıya herhangi bir yetki vermemelisiniz.
* Bu kullanıcıyı `create_generic_user` komutunu kullanmadan da oluşturabilirsiniz.
Ayar dosyasında, var olan herhangi bir kullanıcının kullanıcı adınını kullanmak o kullanıcının
`generic_superuser` olmasını sağlayacaktır. Tabii ki bunu sadece ne yaptığınızı
biliyorsanız yapmalısınız.

### GENERIC_PRIVATEUSER_USERNAME
`generic_privateuser` özel bir kullanıcıdır. Hesaplarını silen kullanıcılar eğer entry'lerinin
korunmasını isterlerse, entry'leri bu kullanıcı tutar. Normal kullanıcıların bu kullanıcıya
erişmesi mümkün değildir. Gelişigüzel bir isim verebilirsiniz, bu isim halka açık olmayacaktır.
Hesabı silinmiş kullanıcıların entry'lerinin yazarı bu ayardan bağımsız olarak *anonim* şeklinde gözükecektir.

Halihazırda bu ayar `anonymous` olarak durur. [GENERIC_SUPERUSER_USERNAME](#generic_superuser_username) ayarındaki adımları kullanarak bu kullanıcıyı
oluşturabilirsiniz. Tek fark, komutu çalıştırırken, kullanıcı tipinin `private` olması gerekiyor:

    python manage.py create_generic_user private KULLANICININ_PAROLASI EPOSTA_ADRESİ